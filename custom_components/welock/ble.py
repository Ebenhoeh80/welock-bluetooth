"""BLE transport for WeLock locks via the Home Assistant Bluetooth stack.

Uses whatever adapter or ESPHome Bluetooth proxy Home Assistant has in range.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import BLE_TIMEOUT, CONFIRM_TIMEOUT
from .protocol import (
    BATTERY_REQUEST,
    NOTIFY_UUID,
    WRITE_UUID,
    BatteryResponse,
    is_battery_response,
    parse_battery_response,
    validate_unlock_command,
)

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)


class WeLockBleError(Exception):
    """BLE communication with the lock failed."""


class LockNotInRange(WeLockBleError):
    """Home Assistant currently has no connectable path to the lock."""


CommandProvider = Callable[[BatteryResponse], Awaitable[bytes]]
# Receives the coroutine that closes the connection and runs it in the background.
TeardownRunner = Callable[[Awaitable[None]], None]


@dataclass
class ExchangeReport:
    """What happened during an unlock exchange, filled in by ``async_exchange``.

    ``command_written`` is set once the unlock command has been written to the
    lock; ``confirmed`` once the lock answered it with a notification. The lock
    does not always answer, so "written but not confirmed" is not an error.
    """

    command_written: bool = False
    confirmed: bool = False
    # Milliseconds spent in each phase; ``None`` if the phase was not reached.
    # connect = establishing the BLE connection (includes waiting for a busy
    # adapter and retries), status = challenge request and answer, command =
    # obtaining the unlock command (cloud round-trip or cache lookup),
    # confirm = writing the command and waiting for the lock's answer,
    # teardown = stopping notifications and disconnecting.
    connect_ms: int | None = None
    status_ms: int | None = None
    command_ms: int | None = None
    confirm_ms: int | None = None
    teardown_ms: int | None = None
    # What Home Assistant knew about the lock when the connection was started:
    # age of the last advertisement (a large value means the lock was not heard
    # for a while, a small one that it was advertising but the connection still
    # took long), its signal strength then, and how many connection attempts the
    # retry helper needed. These tell "lock not advertising" apart from "adapter
    # could not connect".
    adv_age_ms: int | None = None
    rssi: int | None = None
    connect_attempts: int | None = None


def _elapsed_ms(since: float) -> int:
    return round((time.monotonic() - since) * 1000)


def lock_in_range(hass: HomeAssistant, address: str) -> bool:
    """Return True if a connectable adapter or proxy currently sees the lock."""
    return bluetooth.async_ble_device_from_address(hass, address, connectable=True) is not None


class _Notifications:
    """What the lock sends back during one exchange: the status answer and the follow-up."""

    def __init__(self) -> None:
        loop = asyncio.get_running_loop()
        self.status: asyncio.Future[BatteryResponse] = loop.create_future()
        self.followup: asyncio.Future[None] = loop.create_future()
        self.waiting_for_followup = False

    def on_notify(self, _sender: object, data: bytearray) -> None:
        """Receive a notification from the lock."""
        if self.waiting_for_followup and not self.followup.done():
            self.followup.set_result(None)
            return
        if self.status.done() or not is_battery_response(bytes(data)):
            return
        try:
            self.status.set_result(parse_battery_response(bytes(data)))
        except ValueError as err:
            self.status.set_exception(err)


def _note_advertisement(hass: HomeAssistant, address: str, report: ExchangeReport | None) -> None:
    """Record how recently and how strongly Home Assistant heard the lock."""
    info = bluetooth.async_last_service_info(hass, address, connectable=True)
    if report is not None and info is not None:
        report.adv_age_ms = max(0, round((time.monotonic() - info.time) * 1000))
        report.rssi = info.rssi


async def _async_connect(
    hass: HomeAssistant,
    address: str,
    ble_device: BLEDevice,
    report: ExchangeReport | None,
) -> BleakClientWithServiceCache:
    """Open the BLE connection; the retry helper may try several adapters or proxies."""
    attempts = 0

    def _fresh_device() -> BLEDevice:
        # Called by the retry helper before every *retry*: use the newest device
        # object (it may now come from a different adapter or proxy) and count.
        nonlocal attempts
        attempts += 1
        return (
            bluetooth.async_ble_device_from_address(hass, address, connectable=True) or ble_device
        )

    phase = time.monotonic()
    try:
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            ble_device.name or address,
            max_attempts=3,
            ble_device_callback=_fresh_device,
        )
    except (BleakError, asyncio.TimeoutError, OSError) as err:
        raise WeLockBleError(f"Could not connect to {address}: {err}") from err
    finally:
        if report is not None:
            report.connect_ms = _elapsed_ms(phase)
            report.connect_attempts = attempts + 1
    return client


async def _async_read_status(
    client: BleakClientWithServiceCache,
    notifications: _Notifications,
    timeout: float,
    report: ExchangeReport | None,
) -> BatteryResponse:
    """Ask the lock for its challenge and battery and wait for the answer."""
    phase = time.monotonic()
    await client.start_notify(NOTIFY_UUID, notifications.on_notify)
    await client.write_gatt_char(WRITE_UUID, BATTERY_REQUEST, response=False)
    state = await asyncio.wait_for(notifications.status, timeout)
    if report is not None:
        report.status_ms = _elapsed_ms(phase)
    return state


async def _async_send_command(
    client: BleakClientWithServiceCache,
    notifications: _Notifications,
    state: BatteryResponse,
    command_provider: CommandProvider,
    *,
    confirm_timeout: float,
    report: ExchangeReport | None,
    address: str,
) -> None:
    """Get the unlock command for this challenge, write it once and wait for the lock's answer."""
    phase = time.monotonic()
    command = validate_unlock_command(await command_provider(state))
    if report is not None:
        report.command_ms = _elapsed_ms(phase)
    notifications.waiting_for_followup = True
    phase = time.monotonic()
    await client.write_gatt_char(WRITE_UUID, command, response=False)
    if report is not None:
        report.command_written = True
    try:
        await asyncio.wait_for(notifications.followup, confirm_timeout)
        if report is not None:
            report.confirmed = True
    except asyncio.TimeoutError:
        _LOGGER.debug("No confirmation notification from %s after unlock", address)
    if report is not None:
        report.confirm_ms = _elapsed_ms(phase)


async def async_exchange(
    hass: HomeAssistant,
    address: str,
    command_provider: CommandProvider | None = None,
    *,
    timeout: float = BLE_TIMEOUT,
    report: ExchangeReport | None = None,
    confirm_timeout: float = CONFIRM_TIMEOUT,
    teardown_runner: TeardownRunner | None = None,
) -> BatteryResponse:
    """Run the WeLock challenge exchange.

    1. Write the status request ``55 30 00..`` and wait for ``55 30 <rf> <battery>``.
    2. If ``command_provider`` is given, obtain the cloud unlock command for that
       challenge and write it once to the lock.

    Without a ``command_provider`` this is a read-only status/battery check.

    With a ``teardown_runner`` the connection is not closed before returning:
    after a completed unlock exchange the closing coroutine is handed to the
    runner, so the caller can report success right away. The runner must run it
    to completion; on any error the connection is closed here as before.
    """
    ble_device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is None:
        raise LockNotInRange(f"No connectable Bluetooth adapter or proxy sees {address}")

    notifications = _Notifications()
    _note_advertisement(hass, address, report)
    client = await _async_connect(hass, address, ble_device, report)

    handed_off = False
    try:
        state = await _async_read_status(client, notifications, timeout, report)
        if command_provider is not None:
            await _async_send_command(
                client,
                notifications,
                state,
                command_provider,
                confirm_timeout=confirm_timeout,
                report=report,
                address=address,
            )
            if teardown_runner is not None:
                teardown_runner(_async_teardown(client, report))
                handed_off = True
        return state
    except (BleakError, asyncio.TimeoutError, ValueError) as err:
        raise WeLockBleError(f"BLE exchange with {address} failed: {err}") from err
    finally:
        if not handed_off:
            await _async_teardown(client, report)


async def _async_teardown(
    client: BleakClientWithServiceCache, report: ExchangeReport | None
) -> None:
    """Stop notifications and disconnect; never raises."""
    started = time.monotonic()
    # A failure to close must never mask the real exchange exception.
    with contextlib.suppress(BleakError, asyncio.TimeoutError, OSError):
        await client.stop_notify(NOTIFY_UUID)
    with contextlib.suppress(BleakError, asyncio.TimeoutError, OSError):
        await client.disconnect()
    if report is not None:
        report.teardown_ms = _elapsed_ms(started)
