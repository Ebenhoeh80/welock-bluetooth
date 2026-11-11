"""Base entity for WeLock."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ADDRESS, CONF_BLE_NAME, CONF_DEVICE_NUMBER, CONF_MODEL, DOMAIN
from .coordinator import WeLockCoordinator


class WeLockEntity(CoordinatorEntity[WeLockCoordinator]):
    """Common device info for all WeLock entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        address = entry.data[CONF_ADDRESS]
        self._attr_unique_id = f"{address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name=entry.data[CONF_BLE_NAME],
            manufacturer="WeLock",
            model=entry.data.get(CONF_MODEL) or "Smart Lock",
            serial_number=entry.data[CONF_DEVICE_NUMBER],
        )
