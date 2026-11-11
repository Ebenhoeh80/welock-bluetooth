"""BLE transport for WeLock locks via the Home Assistant Bluetooth stack.

Uses whatever adapter or ESPHome Bluetooth proxy Home Assistant has in range.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import BLE_TIMEOUT
from .protocol import (
    BATTERY_REQUEST,
    NOTIFY_UUID,
    WRITE_UUID,
    BatteryResponse,
    is_battery_response,
    parse_battery_response,
    validate_unlock_command,
)

_LOGGER = logging.getLogger(__name__)


class WeLockBleError(Exception):
    """BLE communication with the lock failed."""


class LockNotInRange(WeLockBleError):
    """Home Assistant currently has no connectable path to the lock."""


CommandProvider = Callable[[BatteryResponse], Awaitable[bytes]]


def lock_in_range(hass: HomeAssistant, address: str) -> bool:
    """Return True if a connectable adapter or proxy currently sees the lock."""
    return bluetooth.async_ble_device_from_address(hass, address, connectable=True) is not None


async def async_exchange(
    hass: HomeAssistant,
    address: str,
    command_provider: CommandProvider | None = None,
    timeout: float = BLE_TIMEOUT,
) -> BatteryResponse:
    """Run the WeLock challenge exchange.

    1. Write the status request ``55 30 00..`` and wait for ``55 30 <rf> <battery>``.
    2. If ``command_provider`` is given, obtain the cloud unlock command for that
       challenge and write it once to the lock.

    Without a ``command_provider`` this is a read-only status/battery check.
    """
    ble_device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is None:
        raise LockNotInRange(f"No connectable Bluetooth adapter or proxy sees {address}")

    loop = asyncio.get_running_loop()
    status: asyncio.Future[BatteryResponse] = loop.create_future()
    followup: asyncio.Future[None] = loop.create_future()
    waiting_for_followup = False

    def _on_notify(_sender: object, data: bytearray) -> None:
        if waiting_for_followup and not followup.done():
            followup.set_result(None)
            return
        if status.done() or not is_battery_response(bytes(data)):
            return
        try:
            status.set_result(parse_battery_response(bytes(data)))
        except ValueError as err:
            status.set_exception(err)

    try:
        client = await establish_connection(
            BleakClientWithServiceCache, ble_device, ble_device.name or address, max_attempts=3
        )
    except (BleakError, asyncio.TimeoutError, OSError) as err:
        raise WeLockBleError(f"Could not connect to {address}: {err}") from err

    try:
        await client.start_notify(NOTIFY_UUID, _on_notify)
        await client.write_gatt_char(WRITE_UUID, BATTERY_REQUEST, response=False)
        state = await asyncio.wait_for(status, timeout)

        if command_provider is not None:
            command = validate_unlock_command(await command_provider(state))
            waiting_for_followup = True
            await client.write_gatt_char(WRITE_UUID, command, response=False)
            try:
                await asyncio.wait_for(followup, timeout)
            except asyncio.TimeoutError:
                _LOGGER.debug("No confirmation notification from %s after unlock", address)
        return state
    except (BleakError, asyncio.TimeoutError, ValueError) as err:
        raise WeLockBleError(f"BLE exchange with {address} failed: {err}") from err
    finally:
        try:
            await client.stop_notify(NOTIFY_UUID)
        except (BleakError, asyncio.TimeoutError, OSError):
            pass
        await client.disconnect()
