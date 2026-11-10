"""Binary sensor platform for WeLock smart locks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: list[BinarySensorEntity] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(WeLockLockOnlineBinarySensor(coordinator, lock_sn))

    gateways = coordinator.data.get("gateways", [])
    if isinstance(gateways, list):
        for gw in gateways:
            gw_id = gw.get("gatewayId") or gw.get("wifiBoxId") or gw.get("id")
            if gw_id:
                entities.append(WeLockGatewayBinarySensor(coordinator, str(gw_id), gw))

    async_add_entities(entities)


class WeLockLockOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor reporting whether the lock is communicating with the gateway."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the online binary sensor."""
        super().__init__(coordinator)
        self._lock_sn = lock_sn
        self._attr_unique_id = f"welock_{lock_sn}_online"

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking binary sensor to the lock."""
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

    @property
    def is_on(self) -> bool:
        """Return true if lock is online and reachable."""
        # Check online flags from API response
        status = self.lock_data.get("status")
        online = self.lock_data.get("online")
        if online is not None:
            return bool(online)
        if status is not None:
            return str(status) in ("1", "online", "normal")
        # If lock appears in active dictionary, default to True
        return True


class WeLockGatewayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for the WeLock WiFiBox gateway."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "gateway_connectivity"

    def __init__(self, coordinator: Any, gateway_id: str, initial_data: dict[str, Any]) -> None:
        """Initialize the gateway binary sensor."""
        super().__init__(coordinator)
        self._gateway_id = gateway_id
        self._initial_data = initial_data
        self._attr_unique_id = f"welock_gateway_{gateway_id}_online"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the gateway."""
        return {
            "identifiers": {(DOMAIN, self._gateway_id)},
            "name": f"WeLock WiFiBox ({self._gateway_id[-4:]})",
            "manufacturer": "WeLock",
            "model": "WiFiBox Gateway",
        }

    @property
    def is_on(self) -> bool:
        """Return true if gateway is online."""
        gateways = self.coordinator.data.get("gateways", [])
        for gw in gateways:
            gid = str(gw.get("gatewayId") or gw.get("wifiBoxId") or gw.get("id"))
            if gid == self._gateway_id:
                return bool(gw.get("online", True))
        return True
