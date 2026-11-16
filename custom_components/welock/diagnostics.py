"""Diagnostics support for WeLock Smart Lock integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADDRESS,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from .coordinator import WeLockConfigEntry

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ADDRESS,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    "access_token",
    "refresh_token",
    "token",
    "deviceMac",
    "address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WeLockConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (account, MAC and serial redacted)."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "version": entry.version,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "state": coordinator.data,
    }
