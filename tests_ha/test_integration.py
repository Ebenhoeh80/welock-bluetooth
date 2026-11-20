"""The integration running inside a real Home Assistant core (CI only)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.welock.const import DOMAIN
from custom_components.welock.coordinator import WeLockCoordinator
from custom_components.welock.diagnostics import async_get_config_entry_diagnostics

from .conftest import ADDRESS, CLOUD_COMMAND, DEVICE_NUMBER, STORED_COMMAND, FakeLock


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> WeLockCoordinator:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry.runtime_data


def _entity_id(hass: HomeAssistant, domain: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{ADDRESS}_{key}")
    assert entity_id is not None, f"no {domain} entity for {key}"
    return entity_id


async def _unlock(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "lock", "unlock", {"entity_id": _entity_id(hass, "lock", "lock")}, blocking=True
    )
    await hass.async_block_till_done()


async def test_setup_creates_all_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    for domain, key in (
        ("lock", "lock"),
        ("switch", "offline_unlock"),
        ("event", "unlock"),
        ("binary_sensor", "reachable"),
        ("sensor", "battery"),
        ("sensor", "rssi"),
        ("sensor", "learned_commands"),
        ("sensor", "last_access"),
        ("sensor", "unlocks_cloud"),
        ("sensor", "unlocks_offline"),
        ("sensor", "last_unlock"),
        ("sensor", "connection_quality"),
    ):
        assert _entity_id(hass, domain, key)
    assert hass.states.get(_entity_id(hass, "lock", "lock")).state == "locked"
    assert hass.states.get(_entity_id(hass, "binary_sensor", "reachable")).state == "on"


async def test_unlock_through_the_cloud_is_recorded_and_learned(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await _unlock(hass)

    assert hass.states.get(_entity_id(hass, "lock", "lock")).state == "unlocked"
    assert fake_lock.commands_written == [CLOUD_COMMAND]
    cloud = coordinator.stats.paths["cloud"]
    assert (cloud.attempts, cloud.confirmed, cloud.failed) == (1, 1, 0)
    assert coordinator.cache.get(7) == CLOUD_COMMAND  # learned from the cloud's answer
    # The teardown time is added after the connection has been closed in the background.
    assert coordinator.stats.latest.teardown_ms == 30


async def test_offline_switch_uses_the_stored_command_without_the_cloud(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await coordinator.cache.async_put(7, STORED_COMMAND)

    with patch.object(hass.config_entries, "async_reload") as reload:
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": _entity_id(hass, "switch", "offline_unlock")},
            blocking=True,
        )
        await hass.async_block_till_done()
    reload.assert_not_called()  # the switch applies live, without reloading the entry
    assert config_entry.options["local_unlock"] is True

    await _unlock(hass)
    assert fake_lock.commands_written == [STORED_COMMAND]
    cloud_command.assert_not_called()
    offline = coordinator.stats.paths["offline"]
    assert (offline.attempts, offline.confirmed) == (1, 1)


async def test_switch_off_ignores_the_stored_command(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await coordinator.cache.async_put(7, STORED_COMMAND)
    await _unlock(hass)
    assert fake_lock.commands_written == [CLOUD_COMMAND]
    cloud_command.assert_called_once()


async def test_a_second_unlock_is_held_back_for_a_moment(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    await _setup(hass, config_entry)
    await _unlock(hass)
    with pytest.raises(HomeAssistantError):
        await _unlock(hass)
    assert len(fake_lock.commands_written) == 1


async def test_a_failed_connection_is_reported_and_counted(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    coordinator = await _setup(hass, config_entry)
    fake_lock.fail_to_connect = True
    with pytest.raises(HomeAssistantError):
        await _unlock(hass)
    assert hass.states.get(_entity_id(hass, "lock", "lock")).state == "locked"
    none = coordinator.stats.paths["none"]
    assert (none.attempts, none.failed) == (1, 1)


async def test_low_battery_raises_a_repairs_issue(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    await _setup(hass, config_entry)
    fake_lock.battery = 10
    await _unlock(hass)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"battery_low_{config_entry.entry_id}")
    assert issue is not None
    assert issue.translation_key == "battery_low"
    assert issue.is_fixable is False


async def test_clear_commands_forgets_the_table(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await _unlock(hass)
    assert coordinator.cache.count == 1
    await hass.services.async_call(DOMAIN, "clear_commands", {}, blocking=True)
    assert coordinator.cache.count == 0


async def test_import_commands_adds_a_table_for_the_matching_lock(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    coordinator = await _setup(hass, config_entry)
    name = "welock-test-table.json"
    table = {
        "device_number": DEVICE_NUMBER,
        "table": {"1": "U1IMPORTEDCMD01", "2": "U1IMPORTEDCMD02"},
    }
    path = Path(hass.config.path(name))
    await hass.async_add_executor_job(path.write_text, json.dumps(table), "utf-8")
    try:
        result = await hass.services.async_call(
            DOMAIN, "import_commands", {"path": name}, blocking=True, return_response=True
        )
    finally:
        await hass.async_add_executor_job(path.unlink)
    assert result["added"] == 2
    assert coordinator.cache.count == 2


async def test_import_commands_refuses_a_table_of_another_lock(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    coordinator = await _setup(hass, config_entry)
    name = "welock-other-table.json"
    table = {"device_number": "99999999", "table": {"1": "U1IMPORTEDCMD01"}}
    path = Path(hass.config.path(name))
    await hass.async_add_executor_job(path.write_text, json.dumps(table), "utf-8")
    try:
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN, "import_commands", {"path": name}, blocking=True, return_response=True
            )
    finally:
        await hass.async_add_executor_job(path.unlink)
    assert coordinator.cache.count == 0


async def test_diagnostics_contain_no_secrets_or_commands(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    await _setup(hass, config_entry)
    await _unlock(hass)
    text = json.dumps(await async_get_config_entry_diagnostics(hass, config_entry), default=str)
    assert "secret-password" not in text
    assert "user@example.com" not in text
    assert ADDRESS not in text
    assert CLOUD_COMMAND.decode() not in text
    assert CLOUD_COMMAND.hex() not in text


async def test_entry_unloads_cleanly_after_an_unlock(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    await _setup(hass, config_entry)
    await _unlock(hass)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
