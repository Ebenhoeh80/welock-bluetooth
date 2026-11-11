"""Lock platform for WeLock smart cylinders."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY, DOMAIN
from .coordinator import WeLockCoordinator
from .entity import WeLockEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the WeLock lock entity."""
    coordinator: WeLockCoordinator = hass.data[DOMAIN][entry.entry_id]
    delay = entry.options.get(CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY)
    async_add_entities([WeLockLock(coordinator, entry, delay)])


class WeLockLock(WeLockEntity, LockEntity):
    """WeLock cylinder. The knob engages for a few seconds, then it is locked again.

    The real lock state is not reported, so the state is assumed.
    """

    _attr_name = None
    _attr_assumed_state = True

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry, delay: int) -> None:
        """Initialize the lock entity."""
        super().__init__(coordinator, entry, "lock")
        self._relock_delay = delay
        self._attr_is_locked = True
        self._attr_is_unlocking = False
        self._relock_task: asyncio.Task | None = None

    @property
    def available(self) -> bool:
        """Available while a connectable Bluetooth path to the lock exists."""
        return bool(self.coordinator.data and self.coordinator.data.get("present"))

    async def async_unlock(self, **kwargs: Any) -> None:
        """Run challenge -> cloud command -> BLE write."""
        self._attr_is_unlocking = True
        self.async_write_ha_state()
        try:
            await self.coordinator.async_unlock()
        except Exception:
            self._attr_is_unlocking = False
            self.async_write_ha_state()
            raise
        self._attr_is_unlocking = False
        self._attr_is_locked = False
        self.async_write_ha_state()
        if self._relock_task:
            self._relock_task.cancel()
        self._relock_task = self.hass.async_create_task(self._async_relock())

    async def _async_relock(self) -> None:
        await asyncio.sleep(self._relock_delay)
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """The cylinder locks mechanically by itself; only reset the state."""
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel a pending relock timer."""
        if self._relock_task:
            self._relock_task.cancel()
