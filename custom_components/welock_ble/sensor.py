"""Sensor platform for WeLock: battery and Bluetooth signal strength."""

from __future__ import annotations

from datetime import datetime
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
from homeassistant.helpers.restore_state import RestoreEntity

from .api import access_records_from_attributes
from .const import COMMAND_SPACE, PATH_CLOUD, PATH_OFFLINE
from .coordinator import WeLockConfigEntry, WeLockCoordinator
from .entity import WeLockEntity
from .health import QUALITIES

# read-only
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: WeLockConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WeLock sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            WeLockBatterySensor(coordinator, entry),
            WeLockSignalSensor(coordinator, entry),
            WeLockLearnedCommandsSensor(coordinator, entry),
            WeLockLastAccessSensor(coordinator, entry),
            WeLockUnlockCountSensor(coordinator, entry, PATH_CLOUD),
            WeLockUnlockCountSensor(coordinator, entry, PATH_OFFLINE),
            WeLockLastUnlockSensor(coordinator, entry),
            WeLockConnectionQualitySensor(coordinator, entry),
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
    """How many of the 256 offline unlock commands have been learned so far.

    Commands are learned only while the offline-unlock switch is on (or when a
    table is imported explicitly); with the switch off the count stays unchanged.
    """

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


class WeLockLastAccessSensor(WeLockEntity, RestoreEntity, SensorEntity):
    """Most recent access-log entry, filled on demand by the fetch service.

    The state is the time of the latest entry; attributes carry who opened the
    lock and how, plus the most recent entries. The log is never polled (the
    cloud login ends other sessions of the account), so the sensor stays empty
    until the ``welock_ble.fetch_access_log`` service is used. The last fetched
    entries are restored after a restart or reload, so the value is not lost.
    Disabled by default.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "last_access"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last-access sensor."""
        super().__init__(coordinator, entry, "last_access")

    async def async_added_to_hass(self) -> None:
        """Restore the last fetched entries after a restart or reload."""
        await super().async_added_to_hass()
        if self.coordinator.access_records:
            return
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        self.coordinator.access_records = access_records_from_attributes(last_state.attributes)

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


class WeLockUnlockCountSensor(WeLockEntity, SensorEntity):
    """How many unlocks through Home Assistant were delivered by one path.

    ``cloud`` = the command came from the WeLock cloud, ``offline`` = it came
    from the local command cache (no cloud contact). The state counts unlocks in
    which the command was written to the lock; the attributes split them into
    ``confirmed`` (the lock answered), ``unconfirmed`` and ``failed`` attempts and
    give the average duration. The counters survive restarts.
    """

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "unlocks"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry, path: str) -> None:
        """Initialize the counter for one path."""
        super().__init__(coordinator, entry, f"unlocks_{path}")
        self._path = path
        self._attr_translation_key = f"unlocks_{path}"

    @property
    def native_value(self) -> int:
        """Return the number of unlocks delivered by this path."""
        return self.coordinator.stats.paths[self._path].delivered

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the split into confirmed / unconfirmed / failed and the timing."""
        return self.coordinator.stats.paths[self._path].as_attributes()


class WeLockLastUnlockSensor(WeLockEntity, SensorEntity):
    """Time of the last unlock attempt and how it went, plus recent history."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_unlock"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last-unlock sensor."""
        super().__init__(coordinator, entry, "last_unlock")

    @property
    def native_value(self) -> datetime | None:
        """Return when the latest unlock attempt happened."""
        latest = self.coordinator.stats.latest
        if latest is None:
            return None
        try:
            return datetime.fromisoformat(latest.time)
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the latest attempt and the ten most recent ones (newest first)."""
        stats = self.coordinator.stats
        latest = stats.latest
        attributes: dict[str, Any] = {
            "evictions": stats.evictions,
            "recent": stats.recent(10),
        }
        if latest is not None:
            attributes.update(
                path=latest.path,
                result=latest.result,
                duration_ms=latest.duration_ms,
                random_factor=latest.random_factor,
                error=latest.error,
                connect_ms=latest.connect_ms,
                status_ms=latest.status_ms,
                command_ms=latest.command_ms,
                confirm_ms=latest.confirm_ms,
                teardown_ms=latest.teardown_ms,
                adv_age_ms=latest.adv_age_ms,
                connect_attempts=latest.connect_attempts,
                rssi=latest.rssi,
            )
        return attributes


class WeLockConnectionQualitySensor(WeLockEntity, SensorEntity):
    """How well Home Assistant reaches the lock, judged from the latest unlock attempts."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(QUALITIES)
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connection_quality"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the connection-quality sensor."""
        super().__init__(coordinator, entry, "connection_quality")

    @property
    def native_value(self) -> str:
        """Return good, fair, poor, or unknown while there are too few attempts."""
        return self.coordinator.quality_report.level

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Explain the rating: sample size, failures, median connect time, a suggestion."""
        report = self.coordinator.quality_report
        return {
            "attempts_considered": report.sample,
            "failures": report.failures,
            "median_connect_seconds": (
                None if report.median_connect_s is None else round(report.median_connect_s, 1)
            ),
            "suggestion": report.suggestion,
        }
