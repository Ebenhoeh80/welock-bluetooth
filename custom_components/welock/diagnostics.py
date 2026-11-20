"""Diagnostics support for WeLock Smart Lock integration.

Everything that identifies the account, the lock or its Bluetooth module is redacted, and the
runtime state is an allowlist: a new field of the coordinator data is not exported by accident.
The learned unlock commands and the challenge values are never part of the output.
"""

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
    "title",
    "unique_id",
    "access_token",
    "refresh_token",
    "token",
    "deviceMac",
    "address",
}

# The only runtime values exported: presence, signal strength and battery level.
STATE_ALLOWLIST = ("present", "rssi", "battery")
# Fields of an unlock attempt that are left out of the exported history (the challenge value).
HISTORY_OMIT = ("random_factor",)


def _state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the allowlisted part of the coordinator data."""
    return {key: value for key, value in (data or {}).items() if key in STATE_ALLOWLIST}


def _statistics(stats: dict[str, Any]) -> dict[str, Any]:
    """Return the unlock statistics without the challenge value of each attempt."""
    return {
        **stats,
        "history": [
            {key: value for key, value in attempt.items() if key not in HISTORY_OMIT}
            for attempt in stats["history"]
        ],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WeLockConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (account, lock number, MAC and title redacted)."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(
            {
                "version": entry.version,
                "title": entry.title,
                "unique_id": entry.unique_id,
                "data": async_redact_data(dict(entry.data), TO_REDACT),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "state": _state(coordinator.data),
        "offline_unlock": {
            "enabled": coordinator.local_unlock,
            "learned_commands": coordinator.cache.count,
            "key_figures": coordinator.stats.key_figures(),
            "statistics": _statistics(coordinator.stats.as_dict()),
        },
    }
