"""Binary sensor for WeLock: is the lock reachable over Bluetooth?"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WeLockConfigEntry, WeLockCoordinator
from .entity import WeLockEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: WeLockConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the WeLock connectivity sensor."""
    coordinator = entry.runtime_data
    async_add_entities([WeLockReachableSensor(coordinator, entry)])


class WeLockReachableSensor(WeLockEntity, BinarySensorEntity):
    """On while a connectable Bluetooth adapter or proxy sees the lock."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, "reachable")

    @property
    def is_on(self) -> bool:
        """Return True if the lock is reachable."""
        return bool((self.coordinator.data or {}).get("present"))
