"""Local coordinator: Bluetooth presence, RSSI and battery. Never polls the cloud."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    CannotConnect,
    InvalidAuth,
    LockUnavailable,
    WeLockAccessRecord,
    WeLockApiClient,
    WeLockApiError,
)
from .ble import LockNotInRange, WeLockBleError, async_exchange
from .cache import CommandCache
from .const import (
    CONF_ADDRESS,
    CONF_BATTERY_INTERVAL,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_LOCAL_UNLOCK,
    CONF_SCAN_INTERVAL,
    DEFAULT_BATTERY_INTERVAL,
    DEFAULT_LOCAL_UNLOCK,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_UNLOCK_INTERVAL,
)
from .protocol import BatteryResponse

_LOGGER = logging.getLogger(__name__)


class WeLockCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Tracks one WeLock BLE module and serialises all BLE access to it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: WeLockApiClient,
        cache: CommandCache,
    ) -> None:
        """Initialize the coordinator."""
        scan = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_ADDRESS]}",
            update_interval=timedelta(seconds=scan),
        )
        self.api = api
        self.cache = cache
        self._entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.device_number: str = entry.data[CONF_DEVICE_NUMBER]
        self.ble_name: str = entry.data[CONF_BLE_NAME]
        self._local_unlock: bool = entry.options.get(CONF_LOCAL_UNLOCK, DEFAULT_LOCAL_UNLOCK)
        hours = entry.options.get(CONF_BATTERY_INTERVAL, DEFAULT_BATTERY_INTERVAL)
        self._battery_interval = hours * 3600
        self._ble_lock = asyncio.Lock()
        self._last_unlock = 0.0
        # First battery read a minute after start, so setup is not blocked by BLE.
        self._next_battery_read = time.monotonic() + 60
        self.battery: int | None = None
        # Access log, filled on demand by the fetch_access_log service (never polled).
        self.access_records: list[WeLockAccessRecord] = []

    async def _async_update_data(self) -> dict[str, Any]:
        info = bluetooth.async_last_service_info(self.hass, self.address, connectable=False)
        present = bluetooth.async_address_present(self.hass, self.address, connectable=True)
        if (
            present
            and self._battery_interval > 0
            and time.monotonic() >= self._next_battery_read
            and not self._ble_lock.locked()
        ):
            self._next_battery_read = time.monotonic() + self._battery_interval
            try:
                async with self._ble_lock:
                    state = await async_exchange(self.hass, self.address)
                self.battery = state.battery
            except WeLockBleError as err:
                _LOGGER.debug("Battery read from %s failed: %s", self.address, err)
        return {
            "present": present,
            "rssi": info.rssi if info else None,
            "battery": self.battery,
        }

    async def async_unlock(self) -> None:
        """Challenge -> cloud command -> BLE write. Raises HomeAssistantError."""
        wait = MIN_UNLOCK_INTERVAL - (time.monotonic() - self._last_unlock)
        if wait > 0:
            raise HomeAssistantError(
                f"Bitte {int(wait) + 1} s warten: zwischen zwei Entriegelungen "
                f"liegen mindestens {MIN_UNLOCK_INTERVAL} s."
            )
        if self._ble_lock.locked():
            raise HomeAssistantError(
                "Das Schloss ist gerade mit einem anderen Vorgang beschäftigt."
            )

        async def _command(state: BatteryResponse) -> bytes:
            # Use a locally learned command when the feature is enabled and the
            # challenge value is already known - no cloud round-trip, no app logout.
            if self._local_unlock:
                cached = self.cache.get(state.random_factor)
                if cached is not None:
                    _LOGGER.debug(
                        "Local unlock command for randomFactor=%d (cache hit)",
                        state.random_factor,
                    )
                    return cached
            # Otherwise ask the cloud and always learn the result (shadow filling),
            # so the table keeps growing even while the feature is off.
            command = await self.api.async_request_unlock_command(
                self.device_number, self.ble_name, state.random_factor, state.battery
            )
            await self.cache.async_put(state.random_factor, command)
            return command

        try:
            async with self._ble_lock:
                state = await async_exchange(self.hass, self.address, _command)
        except LockNotInRange as err:
            raise HomeAssistantError(
                "Kein Bluetooth-Adapter oder -Proxy erreicht das Schloss gerade."
            ) from err
        except InvalidAuth as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "WeLock-Anmeldung fehlgeschlagen; bitte neu anmelden."
            ) from err
        except (CannotConnect, LockUnavailable) as err:
            raise HomeAssistantError(f"WeLock Cloud: {err}") from err
        except WeLockBleError as err:
            raise HomeAssistantError(f"Bluetooth: {err}") from err

        self._last_unlock = time.monotonic()
        self.battery = state.battery
        self.async_set_updated_data({**(self.data or {}), "battery": state.battery})

    async def async_fetch_access_log(self, page_size: int) -> int:
        """Fetch the lock's access log from the cloud (on demand only).

        Returns the number of records fetched. Logs in and therefore ends other
        sessions of the account, so this runs only when the user triggers it.
        """
        try:
            records = await self.api.async_get_access_log(self.device_number, page_size=page_size)
        except InvalidAuth as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "WeLock-Anmeldung fehlgeschlagen; bitte neu anmelden."
            ) from err
        except (CannotConnect, WeLockApiError) as err:
            raise HomeAssistantError(f"WeLock Cloud: {err}") from err

        self.access_records = records
        self.async_update_listeners()
        return len(records)
