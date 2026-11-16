"""The WeLock Smart Lock integration.

One config entry = one BLE module of a lock. Unlocking follows the WeLock workflow:
BLE status/challenge -> cloud unlock command -> BLE write. The cloud is not polled.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeLockApiClient
from .cache import CommandCache
from .const import (
    CONF_ADDRESS,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_ACCESS_LOG_PAGE_SIZE,
    DOMAIN,
    SERVICE_FETCH_ACCESS_LOG,
)
from .coordinator import WeLockConfigEntry, WeLockCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LOCK, Platform.SENSOR, Platform.BINARY_SENSOR]

_FETCH_ACCESS_LOG_SCHEMA = vol.Schema(
    {
        vol.Optional("page_size", default=DEFAULT_ACCESS_LOG_PAGE_SIZE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        )
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration-wide access-log service once."""

    async def _handle_fetch_access_log(call: ServiceCall) -> None:
        page_size = call.data["page_size"]
        # Each lock is a separate cloud login; most accounts have a single lock.
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            coordinator = entry.runtime_data
            count = await coordinator.async_fetch_access_log(page_size)
            _LOGGER.debug("Fetched %d access-log entries for %s", count, coordinator.device_number)

    hass.services.async_register(
        DOMAIN,
        SERVICE_FETCH_ACCESS_LOG,
        _handle_fetch_access_log,
        schema=_FETCH_ACCESS_LOG_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeLockConfigEntry) -> bool:
    """Set up a WeLock lock from a config entry (no cloud login at startup)."""
    api = WeLockApiClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    cache = CommandCache(hass, entry.entry_id)
    await cache.async_load()
    coordinator = WeLockCoordinator(hass, entry, api, cache)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeLockConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Version 1 entries had no lock selection; they must be set up again."""
    if entry.version == 1 or CONF_ADDRESS not in entry.data:
        _LOGGER.error(
            "WeLock entry '%s' was created by an older version without lock selection. "
            "Please delete it and add the integration again",
            entry.title,
        )
        return False
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the learned command cache when the entry is deleted."""
    await CommandCache(hass, entry.entry_id).async_clear()


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
