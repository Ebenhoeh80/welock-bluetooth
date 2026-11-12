"""Sensor platform for WeLock: battery and Bluetooth signal strength."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_SPACE, DOMAIN
from .coordinator import WeLockCoordinator
from .entity import WeLockEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WeLock sensors."""
    coordinator: WeLockCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WeLockBatterySensor(coordinator, entry),
            WeLockSignalSensor(coordinator, entry),
            WeLockLearnedCommandsSensor(coordinator, entry),
            WeLockLastAccessSensor(coordinator, entry),
        ]
    )


class WeLockBatterySensor(WeLockEntity, SensorEntity):
    """Battery level read over BLE (periodically and on every unlock)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "battery"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, entry, "battery")

    @property
    def native_value(self) -> int | None:
        """Return the last known battery percentage."""
        return (self.coordinator.data or {}).get("battery")


class WeLockSignalSensor(WeLockEntity, SensorEntity):
    """RSSI of the last advertisement seen by Home Assistant."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "signal_strength"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the signal sensor."""
        super().__init__(coordinator, entry, "rssi")

    @property
    def native_value(self) -> int | None:
        """Return the RSSI in dBm."""
        return (self.coordinator.data or {}).get("rssi")


class WeLockLearnedCommandsSensor(WeLockEntity, SensorEntity):
    """How many of the 256 offline unlock commands have been learned so far."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "commands"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "learned_commands"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the learned-commands sensor."""
        super().__init__(coordinator, entry, "learned_commands")

    @property
    def native_value(self) -> int:
        """Return the number of learned offline commands (0..256)."""
        return self.coordinator.cache.count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose coverage and whether the offline table is complete."""
        cache = self.coordinator.cache
        return {
            "coverage_percent": cache.coverage,
            "total": COMMAND_SPACE,
            "complete": cache.complete,
        }


class WeLockLastAccessSensor(WeLockEntity, SensorEntity):
    """Most recent access-log entry, filled on demand by the fetch service.

    The state is the time of the latest entry; attributes carry who opened the
    lock and how, plus the most recent entries. Disabled by default because it
    stays empty until the ``welock.fetch_access_log`` service is used.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:history"
    _attr_translation_key = "last_access"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last-access sensor."""
        super().__init__(coordinator, entry, "last_access")

    @property
    def native_value(self) -> str | None:
        """Return the time of the latest access-log entry, if any."""
        records = self.coordinator.access_records
        return records[0].time if records else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the latest entry and the most recent entries."""
        records = self.coordinator.access_records
        if not records:
            return {"records": []}
        latest = records[0]
        return {
            "user": latest.user,
            "method": latest.method,
            "success": latest.success,
            "records": [
                {
                    "time": record.time,
                    "user": record.user,
                    "method": record.method,
                    "success": record.success,
                }
                for record in records[:20]
            ],
        }
