"""Sensor platform for WeLock smart locks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: list[SensorEntity] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(WeLockBatterySensor(coordinator, lock_sn))
        entities.append(WeLockSignalSensor(coordinator, lock_sn))
        entities.append(WeLockLastUnlockTypeSensor(coordinator, lock_sn))

    async_add_entities(entities)


class WeLockSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for WeLock sensor entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._lock_sn = lock_sn

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking sensor to the lock."""
        model = self.lock_data.get("model") or "Smart Lock"
        name = self.lock_data.get("lockName") or f"WeLock {self._lock_sn[-4:]}"
        fw = self.lock_data.get("firmwareVersion") or "1.0"
        wifi_box = self.lock_data.get("wifiBoxId")

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._lock_sn)},
            "name": name,
            "manufacturer": "WeLock",
            "model": f"WeLock {model}",
            "sw_version": str(fw),
        }
        if wifi_box:
            info["via_device"] = (DOMAIN, str(wifi_box))
        return info


class WeLockBatterySensor(WeLockSensorBase):
    """Battery level sensor for WeLock."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "battery"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_battery"

    @property
    def native_value(self) -> int | None:
        """Return the current battery percentage."""
        val = self.lock_data.get("battery") or self.lock_data.get("electric")
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                return None
        return None


class WeLockSignalSensor(WeLockSensorBase):
    """Bluetooth / WiFi Gateway signal strength sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_translation_key = "signal_strength"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the signal strength sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_signal"

    @property
    def native_value(self) -> int | None:
        """Return the RSSI signal strength."""
        val = self.lock_data.get("rssi") or self.lock_data.get("signal")
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                return None
        return None


class WeLockLastUnlockTypeSensor(WeLockSensorBase):
    """Sensor reporting the last unlock mechanism."""

    _attr_translation_key = "last_unlock_type"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the last unlock sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_last_unlock_type"

    @property
    def native_value(self) -> str | None:
        """Return the last unlock method."""
        val = (
            self.lock_data.get("lastUnlockType")
            or self.lock_data.get("unlockType")
            or self.lock_data.get("lastAction")
        )
        if not val:
            return "None"
        # Standardize known WeLock unlock methods
        mapping = {
            "1": "Fingerprint",
            "2": "RFID Card",
            "3": "Passcode",
            "4": "App / Bluetooth",
            "5": "Gateway / Cloud",
            "fingerprint": "Fingerprint",
            "card": "RFID Card",
            "password": "Passcode",
            "app": "App / Gateway",
        }
        return mapping.get(str(val).lower(), str(val))
