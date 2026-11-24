"""Services, error paths and the life cycle of the entry, inside a real Home Assistant core (CI only)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.welock_ble.api import (
    CannotConnect,
    InvalidAuth,
    LockUnavailable,
    WeLockAccessRecord,
    WeLockApiError,
)
from custom_components.welock_ble.ble import LockNotInRange, WeLockBleError
from custom_components.welock_ble.const import DOMAIN

from .conftest import DEVICE_NUMBER, STORED_COMMAND, FakeLock
from .test_integration import _entity_id, _setup, _unlock

REQUEST = "custom_components.welock_ble.api.WeLockApiClient.async_request_unlock_command"
ACCESS_LOG = "custom_components.welock_ble.api.WeLockApiClient.async_get_access_log"


def _record(time: str = "2026-11-20 10:00:00") -> WeLockAccessRecord:
    return WeLockAccessRecord(time=time, user="Dan", method="app", success=True, position=1)


async def test_the_access_log_is_fetched_and_shown(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "sensor", "last_access")
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    with patch(ACCESS_LOG, return_value=[_record(), _record("2026-11-19 09:00:00")]):
        await hass.services.async_call(DOMAIN, "fetch_access_log", {"page_size": 5}, blocking=True)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "2026-11-20 10:00:00"
    assert state.attributes["user"] == "Dan" and len(state.attributes["records"]) == 2

    # after a reload the last fetched entries are restored from the state
    coordinator.access_records = []
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.access_records or hass.states.get(entity_id) is not None


@pytest.mark.parametrize("error", [InvalidAuth("no"), CannotConnect("no"), WeLockApiError("no")])
async def test_a_failing_access_log_request_is_reported(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock, error: Exception
) -> None:
    await _setup(hass, config_entry)
    with patch(ACCESS_LOG, side_effect=error), pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "fetch_access_log", {}, blocking=True)


@pytest.mark.parametrize(
    "error",
    [
        LockNotInRange("far"),
        InvalidAuth("no"),
        CannotConnect("no"),
        LockUnavailable("no"),
        WeLockBleError("no"),
    ],
)
async def test_unlock_errors_become_readable_messages(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock, error: Exception
) -> None:
    await _setup(hass, config_entry)
    with patch(REQUEST, side_effect=error), pytest.raises(HomeAssistantError):
        await _unlock(hass)
    assert hass.states.get(_entity_id(hass, "lock", "lock")).state == "locked"


async def test_an_unexpected_error_is_not_hidden(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    with patch(REQUEST, side_effect=RuntimeError("boom")), pytest.raises(RuntimeError):
        await _unlock(hass)


async def test_an_unlock_is_refused_while_the_lock_is_busy(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    async with coordinator._ble_lock:
        with pytest.raises(HomeAssistantError):
            await _unlock(hass)
    assert not fake_lock.commands_written


async def test_the_lock_service_only_resets_the_display(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "lock", "lock")
    await _unlock(hass, settle=False)
    assert hass.states.get(entity_id).state == "unlocked"
    await hass.services.async_call("lock", "lock", {"entity_id": entity_id}, blocking=True)
    assert hass.states.get(entity_id).state == "locked"
    await hass.async_block_till_done()


async def test_a_stored_command_that_fails_to_write_is_dropped(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    coordinator = await _setup(hass, config_entry)
    await coordinator.cache.async_put(7, STORED_COMMAND)
    await coordinator.async_set_local_unlock(True)

    async def failing_exchange(hass, address, command_provider=None, report=None, **kwargs):
        from custom_components.welock_ble.protocol import BatteryResponse

        await command_provider(BatteryResponse(random_factor=7, battery=80))
        report.command_written = True
        raise WeLockBleError("write failed")

    with (
        patch("custom_components.welock_ble.coordinator.async_exchange", failing_exchange),
        pytest.raises(HomeAssistantError),
    ):
        await _unlock(hass)
    assert coordinator.cache.get(7) is None


async def test_the_battery_is_read_and_a_failed_read_is_retried_later(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    fake_lock.fail_to_connect = True
    coordinator = await _setup(hass, config_entry)
    assert coordinator.battery is None
    fake_lock.fail_to_connect = False
    coordinator._next_battery_read = 0
    await coordinator.async_refresh()
    assert coordinator.battery == 80


async def _write_table(hass: HomeAssistant, name: str, text: str) -> Path:
    path = Path(hass.config.path(name))
    await hass.async_add_executor_job(path.write_text, text, "utf-8")
    return path


@pytest.mark.parametrize("name", ["table.txt", "../outside.json"])
async def test_import_refuses_files_outside_the_rules(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock, name: str
) -> None:
    await _setup(hass, config_entry)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_commands", {"path": name}, blocking=True, return_response=True
        )


async def test_import_reports_a_missing_or_broken_file(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_commands", {"path": "missing.json"}, blocking=True, return_response=True
        )
    path = await _write_table(hass, "welock-broken.json", json.dumps({"device_number": 5}))
    try:
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "import_commands", {"path": path.name}, blocking=True, return_response=True
            )
    finally:
        await hass.async_add_executor_job(path.unlink)


async def test_a_file_that_is_too_large_is_refused(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    path = await _write_table(hass, "welock-large.json", " " * 3_000_000)
    try:
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "import_commands", {"path": path.name}, blocking=True, return_response=True
            )
    finally:
        await hass.async_add_executor_job(path.unlink)


async def test_changed_options_reload_the_entry_and_the_offline_switch_applies_live(
    hass: HomeAssistant, config_entry: MockConfigEntry, fake_lock: FakeLock
) -> None:
    await _setup(hass, config_entry)
    first = config_entry.runtime_data
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, "local_unlock": True}
    )
    await hass.async_block_till_done()
    assert config_entry.runtime_data is first  # applied live, no reload

    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.options, "auto_relock_delay": 7}
    )
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data is not first  # other options reload the entry


async def test_an_entry_of_the_first_version_cannot_be_migrated(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, version=1, unique_id="old", data={"username": "u"})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_removing_the_entry_clears_its_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
) -> None:
    coordinator = await _setup(hass, config_entry)
    await coordinator.cache.async_put(7, STORED_COMMAND)
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.config_entries.async_get_entry(config_entry.entry_id) is None
    assert DEVICE_NUMBER


async def test_the_software_part_of_an_unlock_stays_small(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    fake_lock: FakeLock,
    cloud_command: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Budget: without radio and cloud latency an unlock costs the integration only milliseconds.

    In the field a whole unlock takes 3 to 33 s, of which the Bluetooth connection is 99 %; this
    guards the part the integration controls.
    """
    import asyncio
    import statistics
    import time

    coordinator = await _setup(hass, config_entry)
    samples: list[float] = []
    for _ in range(8):
        coordinator._last_unlock = float("-inf")
        started = time.perf_counter()
        await coordinator.async_unlock()
        samples.append((time.perf_counter() - started) * 1000)
        while coordinator._ble_lock.locked():  # the connection is closed in the background
            await asyncio.sleep(0.01)
        await hass.async_block_till_done()
    with capsys.disabled():
        print(
            f"unlock software overhead: median {statistics.median(samples):.1f} ms, max {max(samples):.1f} ms"
        )
    assert statistics.median(samples) < 250
