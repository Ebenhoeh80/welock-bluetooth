"""Support for WeLock smart locks."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AUTO_RELOCK_DELAY,
    DEFAULT_AUTO_RELOCK_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock locks from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    relock_delay = entry.options.get(
        CONF_AUTO_RELOCK_DELAY,
        entry.data.get(CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY),
    )

    entities: list[WeLockLock] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(
            WeLockLock(
                coordinator=coordinator,
                api=api,
                lock_sn=lock_sn,
                relock_delay=relock_delay,
            )
        )

    async_add_entities(entities)


class WeLockLock(CoordinatorEntity, LockEntity):
    """Representation of a WeLock Smart Lock entity."""

    _attr_has_entity_name = True
    _attr_name = None  # Uses device name

    def __init__(
        self,
        coordinator: Any,
        api: Any,
        lock_sn: str,
        relock_delay: int,
    ) -> None:
        """Initialize the lock entity."""
        super().__init__(coordinator)
        self.api = api
        self._lock_sn = lock_sn
        self._relock_delay = relock_delay
        self._is_locked = True
        self._is_unlocking = False
        self._attr_unique_id = f"welock_{lock_sn}_lock"

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Home Assistant device registry."""
        model = self.lock_data.get("model") or self.lock_data.get("deviceType") or "Smart Lock"
        name_field = self.lock_data.get("lockName") or self.lock_data.get("name")
        custom_name = name_field or f"WeLock {self._lock_sn[-4:]}"
        fw = self.lock_data.get("firmwareVersion") or self.lock_data.get("firmware") or "1.0"
        wifi_box = self.lock_data.get("wifiBoxId") or self.lock_data.get("gatewayId")

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._lock_sn)},
            "name": custom_name,
            "manufacturer": "WeLock",
            "model": f"WeLock {model}",
            "sw_version": str(fw),
        }
        if wifi_box:
            info["via_device"] = (DOMAIN, str(wifi_box))

        return info

    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        return self._is_locked

    @property
    def is_unlocking(self) -> bool:
        """Return true if lock is unlocking."""
        return self._is_unlocking

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device-specific attributes."""
        data = self.lock_data
        return {
            "serial_number": self._lock_sn,
            "mac_address": data.get("mac") or data.get("macAddress"),
            "model": data.get("model") or data.get("deviceType"),
            "battery_percent": data.get("battery") or data.get("electric"),
            "gateway_sn": data.get("wifiBoxId") or data.get("gatewayId"),
            "last_active": data.get("lastActive") or data.get("updateTime"),
        }

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the WeLock device via WiFiBox gateway."""
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            await self.api.async_unlock(self._lock_sn)
            self._is_locked = False
            self._is_unlocking = False
            self.async_write_ha_state()

            # WeLock smart cylinders mechanically reset / auto-relock after engagement
            self.hass.async_create_task(self._async_auto_relock())

        except Exception as err:
            _LOGGER.error("Failed to unlock WeLock %s: %s", self._lock_sn, err)
            self._is_unlocking = False
            self._is_locked = True
            self.async_write_ha_state()
            raise

    async def _async_auto_relock(self) -> None:
        """Simulate mechanical auto-relock of the WeLock cylinder knob."""
        await asyncio.sleep(self._relock_delay)
        self._is_locked = True
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device (WeLock auto-locks mechanically)."""
        self._is_locked = True
        self._is_unlocking = False
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
