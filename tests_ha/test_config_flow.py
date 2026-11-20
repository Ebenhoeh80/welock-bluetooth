"""The setup, re-authentication and options dialogs, run inside a real Home Assistant core (CI only)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import TextSelector, TextSelectorType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.welock.api import (
    CannotConnect,
    InvalidAuth,
    WeLockApiError,
    WeLockBleModule,
    WeLockDevice,
)
from custom_components.welock.ble import LockNotInRange, WeLockBleError
from custom_components.welock.const import (
    CONF_ADDRESS,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.welock.protocol import BatteryResponse

from .conftest import ADDRESS, DEVICE_NUMBER

LOGIN = "custom_components.welock.config_flow._async_login_and_list"
EXCHANGE = "custom_components.welock.config_flow.async_exchange"
IN_RANGE = "custom_components.welock.config_flow.lock_in_range"
OTHER_ADDRESS = "AA:BB:CC:DD:EE:01"


def _account(*addresses: str | None) -> list[WeLockDevice]:
    """A cloud account with one lock that has one Bluetooth module per given address."""
    modules = tuple(
        WeLockBleModule(name=f"WeLockTEST{i}", address=address, battery=70, position=None)
        for i, address in enumerate(addresses)
    )
    return [WeLockDevice(device_number=DEVICE_NUMBER, name="Door", model="Smart Lock", ble=modules)]


async def _start(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    return result["flow_id"]


async def _login(hass: HomeAssistant, flow_id: str, devices=None, error: Exception | None = None):
    with patch(LOGIN, side_effect=error, return_value=devices):
        return await hass.config_entries.flow.async_configure(
            flow_id, {CONF_USERNAME: " user@example.com ", CONF_PASSWORD: "pw"}
        )


def _password_field(result: dict) -> object:
    return next(v for k, v in result["data_schema"].schema.items() if k == CONF_PASSWORD)


async def test_the_login_asks_for_the_password_in_a_password_field(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    field = _password_field(result)
    assert isinstance(field, TextSelector)
    assert field.config["type"] == TextSelectorType.PASSWORD


async def test_the_reauthentication_asks_for_the_password_in_a_password_field(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    field = _password_field(result)
    assert isinstance(field, TextSelector)
    assert field.config["type"] == TextSelectorType.PASSWORD


async def test_the_full_setup_creates_an_entry(hass: HomeAssistant) -> None:
    flow_id = await _start(hass)
    with patch(IN_RANGE, return_value=True):
        result = await _login(hass, flow_id, _account(ADDRESS))
    assert result["step_id"] == "select"

    result = await hass.config_entries.flow.async_configure(flow_id, {CONF_ADDRESS: ADDRESS})
    assert result["step_id"] == "verify"

    with (
        patch(EXCHANGE, return_value=BatteryResponse(random_factor=1, battery=80)),
        patch("custom_components.welock.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(flow_id, {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USERNAME] == "user@example.com"
    assert result["data"][CONF_ADDRESS] == ADDRESS
    assert result["data"][CONF_DEVICE_NUMBER] == DEVICE_NUMBER


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (InvalidAuth("no"), "invalid_auth"),
        (CannotConnect("no"), "cannot_connect"),
        (WeLockApiError("no"), "cloud_error"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_a_failing_login_shows_the_matching_error(
    hass: HomeAssistant, error: Exception, key: str
) -> None:
    flow_id = await _start(hass)
    result = await _login(hass, flow_id, error=error)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}


async def test_an_account_without_a_bluetooth_lock_is_reported(hass: HomeAssistant) -> None:
    flow_id = await _start(hass)
    result = await _login(hass, flow_id, _account(None))
    assert result["errors"] == {"base": "no_locks"}


async def test_the_lock_in_range_is_preselected_and_a_bluetooth_error_can_be_retried(
    hass: HomeAssistant,
) -> None:
    flow_id = await _start(hass)
    with patch(IN_RANGE, side_effect=lambda hass, address: address == OTHER_ADDRESS):
        result = await _login(hass, flow_id, _account(ADDRESS, OTHER_ADDRESS))
    assert result["step_id"] == "select"
    assert result["data_schema"]({})[CONF_ADDRESS] == OTHER_ADDRESS

    await hass.config_entries.flow.async_configure(flow_id, {CONF_ADDRESS: ADDRESS})
    for error, key in (
        (LockNotInRange("far"), "not_in_range"),
        (WeLockBleError("x"), "ble_failed"),
    ):
        with patch(EXCHANGE, side_effect=error):
            result = await hass.config_entries.flow.async_configure(flow_id, {})
        assert result["step_id"] == "verify" and result["errors"] == {"base": key}


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", ["lock", "battery per cloud 70 %", "out of range"]),
        ("de", ["Schloss", "Akku laut Cloud 70 %", "außer Reichweite"]),
        ("fr", ["serrure", "batterie selon le cloud 70 %", "hors de portée"]),
    ],
)
async def test_the_lock_list_is_translated(
    hass: HomeAssistant, language: str, expected: list[str]
) -> None:
    hass.config.language = language
    flow_id = await _start(hass)
    with patch(IN_RANGE, return_value=False):
        result = await _login(hass, flow_id, _account(ADDRESS))
    label = result["data_schema"].schema[CONF_ADDRESS].container[ADDRESS]
    for word in expected:
        assert word in label, (language, label)


async def test_a_lock_that_is_already_set_up_cannot_be_added_again(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    flow_id = await _start(hass)
    with patch(IN_RANGE, return_value=True):
        await _login(hass, flow_id, _account(ADDRESS))
    result = await hass.config_entries.flow.async_configure(flow_id, {CONF_ADDRESS: ADDRESS})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_bluetooth_discovery_asks_for_the_login_and_checks_the_account(
    hass: HomeAssistant,
) -> None:
    info = SimpleNamespace(address=ADDRESS, name="WeLockTEST0")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info
    )
    assert result["step_id"] == "user"
    with patch(IN_RANGE, return_value=True):
        result = await _login(hass, result["flow_id"], _account(ADDRESS, OTHER_ADDRESS))
    assert result["step_id"] == "select"
    assert list(result["data_schema"].schema[CONF_ADDRESS].container) == [ADDRESS]


async def test_a_discovered_lock_that_is_not_in_the_account_aborts(hass: HomeAssistant) -> None:
    info = SimpleNamespace(address=ADDRESS, name="WeLockTEST0")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info
    )
    result = await _login(hass, result["flow_id"], _account(OTHER_ADDRESS))
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "not_in_account"


async def test_a_discovered_lock_that_is_already_set_up_aborts(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    info = SimpleNamespace(address=ADDRESS, name="WeLockTEST0")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_reauthentication_stores_the_new_password(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with (
        patch(LOGIN, return_value=_account(ADDRESS)),
        patch("custom_components.welock.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-password"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-password"


@pytest.mark.parametrize(
    ("kwargs", "key"),
    [
        ({"error": InvalidAuth("no")}, "invalid_auth"),
        ({"error": CannotConnect("no")}, "cannot_connect"),
        ({"error": WeLockApiError("no")}, "cloud_error"),
        ({"devices": _account(OTHER_ADDRESS)}, "lock_not_found"),
    ],
)
async def test_reauthentication_reports_what_went_wrong(
    hass: HomeAssistant, config_entry: MockConfigEntry, kwargs: dict, key: str
) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    with patch(LOGIN, side_effect=kwargs.get("error"), return_value=kwargs.get("devices")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "pw"}
        )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": key}


async def test_the_options_can_be_changed(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["step_id"] == "init"
    with patch("custom_components.welock.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "auto_relock_delay": 12,
                "battery_interval": 6,
                "scan_interval": 90,
                "local_unlock": True,
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options["auto_relock_delay"] == 12
    assert config_entry.options["local_unlock"] is True
    assert CONF_BLE_NAME in config_entry.data
