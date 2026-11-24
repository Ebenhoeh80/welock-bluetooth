"""The WeLock Smart Lock integration.

One config entry = one BLE module of a lock. Unlocking follows the WeLock workflow:
BLE status/challenge -> cloud unlock command -> BLE write. The cloud is not polled.
"""

from __future__ import annotations

import json
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeLockApiClient
from .cache import CommandCache, parse_command_table
from .const import (
    CONF_ADDRESS,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_ACCESS_LOG_PAGE_SIZE,
    DEFAULT_IMPORT_FILE,
    DOMAIN,
    MAX_IMPORT_FILE_BYTES,
    SERVICE_CLEAR_COMMANDS,
    SERVICE_FETCH_ACCESS_LOG,
    SERVICE_IMPORT_COMMANDS,
)
from .coordinator import WeLockConfigEntry, WeLockCoordinator
from .identity import is_generated_title, lock_title
from .issues import clear_issues
from .stats import UnlockStats

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LOCK,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.EVENT,
]

_FETCH_ACCESS_LOG_SCHEMA = vol.Schema(
    {
        vol.Optional("page_size", default=DEFAULT_ACCESS_LOG_PAGE_SIZE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        )
    }
)


_IMPORT_COMMANDS_SCHEMA = vol.Schema(
    {vol.Optional("path", default=DEFAULT_IMPORT_FILE): vol.All(str, vol.Length(min=1, max=255))}
)


class _PathNotAllowed(Exception):
    """The requested file is not a .json file inside the configuration folder."""


def _read_table_file(config_dir: str, name: str) -> Any:
    """Read and parse a JSON file inside the config folder (runs in the executor)."""
    base = Path(config_dir).resolve()
    file = (base / name).resolve()  # follows symlinks; an absolute name replaces base
    if not file.is_relative_to(base) or file.suffix.lower() != ".json":
        raise _PathNotAllowed
    if file.stat().st_size > MAX_IMPORT_FILE_BYTES:
        raise ValueError("file too large")
    return json.loads(file.read_text(encoding="utf-8"))


async def _async_fetch_access_log(hass: HomeAssistant, call: ServiceCall) -> None:
    page_size = call.data["page_size"]
    # Each lock is a separate cloud login; most accounts have a single lock.
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = entry.runtime_data
        count = await coordinator.async_fetch_access_log(page_size)
        _LOGGER.debug("Fetched %d access-log entries for %s", count, coordinator.device_number)


async def _async_import_commands(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Import a command table into the cache of the lock it belongs to."""
    try:
        data = await hass.async_add_executor_job(
            _read_table_file, hass.config.config_dir, call.data["path"]
        )
    except _PathNotAllowed as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="import_path_not_allowed"
        ) from err
    except (OSError, ValueError) as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="import_file_unreadable",
            translation_placeholders={"error": type(err).__name__},
        ) from err
    try:
        device_number, table = parse_command_table(data)
    except ValueError as err:
        # The message is fixed text plus counts and challenge numbers, never a command
        # (see parse_command_table and its test), so it may be shown to the user.
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="import_invalid_table",
            translation_placeholders={"error": str(err)},
        ) from err
    # The table belongs to one lock; never import it into another one.
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = entry.runtime_data
        if coordinator.device_number != device_number:
            continue
        result = await coordinator.cache.async_import(table)
        coordinator.async_update_listeners()
        return {
            "added": result.added,
            "unchanged": result.unchanged,
            "conflicts": result.conflicts,
            "known": coordinator.cache.count,
        }
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="import_wrong_lock")


async def _async_clear_commands(hass: HomeAssistant, call: ServiceCall) -> None:
    """Forget the stored unlock commands of every configured lock."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = entry.runtime_data
        await coordinator.cache.async_clear()
        coordinator.async_update_listeners()
        _LOGGER.info("Cleared the stored unlock commands of %s", entry.title)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration-wide services once."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_FETCH_ACCESS_LOG,
        partial(_async_fetch_access_log, hass),
        schema=_FETCH_ACCESS_LOG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_COMMANDS,
        partial(_async_import_commands, hass),
        schema=_IMPORT_COMMANDS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_COMMANDS,
        partial(_async_clear_commands, hass),
        schema=vol.Schema({}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeLockConfigEntry) -> bool:
    """Set up a WeLock lock from a config entry (no cloud login at startup)."""
    _async_heal_title(hass, entry)
    api = WeLockApiClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    cache = CommandCache(hass, entry.entry_id)
    await cache.async_load()
    stats = UnlockStats(hass, entry.entry_id)
    await stats.async_load()
    coordinator = WeLockCoordinator(hass, entry, api, cache, stats)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


def _async_heal_title(hass: HomeAssistant, entry: WeLockConfigEntry) -> None:
    """Show the lock number instead of the Bluetooth module name (a title the user chose stays)."""
    title = lock_title(entry.data[CONF_DEVICE_NUMBER])
    if entry.title != title and is_generated_title(entry.title, entry.data[CONF_BLE_NAME]):
        hass.config_entries.async_update_entry(entry, title=title)


async def async_unload_entry(hass: HomeAssistant, entry: WeLockConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # Issues from older versions were created without a config entry link.
        clear_issues(hass, entry.entry_id)
    return unloaded


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
    """Remove the learned command cache and the statistics when the entry is deleted."""
    await CommandCache(hass, entry.entry_id).async_clear()
    await UnlockStats(hass, entry.entry_id).async_clear()
    clear_issues(hass, entry.entry_id)


async def _async_reload_entry(hass: HomeAssistant, entry: WeLockConfigEntry) -> None:
    """Apply changed options: the offline switch live, anything else by reloading."""
    if entry.runtime_data.apply_options(entry.options):
        return
    await hass.config_entries.async_reload(entry.entry_id)
