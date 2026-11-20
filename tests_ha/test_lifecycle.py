"""Setup, reload, unload, Home Assistant stop and the migration of older entries (CI only)."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import ADDRESS, DEVICE_NUMBER, FakeLock
from .test_integration import _setup, _unlock


def _entities(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, str]:
    """Return ``{unique_id: entity_id}`` of all entities of the entry."""
    registry = er.async_get(hass)
    return {
        item.unique_id: item.entity_id
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


async def test_setup_reload_unload_and_stop_leave_nothing_behind(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    # The Home Assistant test fixtures also fail the test if a task or timer is left over.
    coordinator = await _setup(hass, config_entry)
    await _unlock(hass)

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data is not coordinator

    old = config_entry.runtime_data
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not old._teardown_tasks
    assert not old._unlock_listeners  # every event entity removed its listener
    assert not config_entry.update_listeners  # the options listener is gone

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    running = config_entry.runtime_data
    assert not running._teardown_tasks


async def test_stopping_home_assistant_right_after_an_unlock_leaves_no_task(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await _unlock(hass, settle=False)  # the connection is still being closed in the background
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert not coordinator._teardown_tasks


async def test_an_entry_from_before_2_5_gets_the_lock_number_in_its_title(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    """Version-2 entries made before 2.5 are titled with the module name and have no number."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(config_entry, title="WeLockTEST")  # the module name
    assert config_entry.version == 2
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.title == f"WeLock ({DEVICE_NUMBER})"
    assert config_entry.unique_id == ADDRESS
    first = _entities(hass, config_entry)
    assert first and all(unique_id.startswith(ADDRESS) for unique_id in first)

    # Going back to the old title and setting up again changes neither identity nor entity IDs.
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    hass.config_entries.async_update_entry(config_entry, title="WeLockTEST")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.title == f"WeLock ({DEVICE_NUMBER})"
    assert config_entry.unique_id == ADDRESS
    assert _entities(hass, config_entry) == first
