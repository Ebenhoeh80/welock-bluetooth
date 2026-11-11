"""The WeLock Smart Lock integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, WeLockApiClient, WeLockApiError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LOCK,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


class WeLockDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching WeLock data from the cloud API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WeLockApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from WeLock Cloud."""
        try:
            locks = await self.api.async_get_locks()
            gateways = await self.api.async_get_gateways()

            lock_dict: dict[str, dict[str, Any]] = {}
            for lock in locks:
                lock_sn = lock.get("lockSn") or lock.get("lock_sn") or lock.get("sn")
                if lock_sn:
                    # Enrich with detail if available
                    detail = await self.api.async_get_lock_detail(lock_sn)
                    merged = {**lock, **detail}
                    lock_dict[str(lock_sn)] = merged

            return {
                "locks": lock_dict,
                "gateways": gateways,
            }
        except (InvalidAuth, CannotConnect, WeLockApiError) as err:
            raise UpdateFailed(f"Error communicating with WeLock Cloud: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WeLock Smart Lock from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data.get(CONF_USERNAME) or entry.data.get(CONF_CLIENT_ID) or ""
    password = entry.data.get(CONF_PASSWORD) or entry.data.get(CONF_CLIENT_SECRET) or ""
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    session = async_get_clientsession(hass)
    api = WeLockApiClient(username=username, password=password, session=session)

    # Initial authentication test
    try:
        await api.async_authenticate()
    except Exception as err:
        _LOGGER.error("Failed to authenticate with WeLock during setup: %s", err)
        raise

    coordinator = WeLockDataUpdateCoordinator(
        hass=hass,
        api=api,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data so that entities have state immediately
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
