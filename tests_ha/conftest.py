"""Fixtures for tests that run the integration inside a real Home Assistant core.

These tests use ``pytest-homeassistant-custom-component`` and run in their own CI job (Python 3.14,
the Home Assistant version that package pins). They are kept apart from ``tests/``: those tests stub
Home Assistant with ``sys.modules`` and must never be collected in the same session.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Coroutine, Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# The integration only calls a few functions of Home Assistant's Bluetooth component (is the lock
# in range, how strong is the signal). The component itself needs a dozen native Bluetooth
# packages and D-Bus, so it is replaced by a stand-in; the tests patch the calls they care about.
sys.modules.setdefault("homeassistant.components.bluetooth", MagicMock())

from homeassistant.core import HomeAssistant  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.welock.const import (  # noqa: E402
    CONF_ADDRESS,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.welock.protocol import BatteryResponse  # noqa: E402

ADDRESS = "C4:43:4A:03:42:A9"
DEVICE_NUMBER = "22231059"
CLOUD_COMMAND = b"U1CLOUDCMDXXXXX"
STORED_COMMAND = b"U1STOREDCMDXXXX"

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load integrations from ``custom_components/``."""


@pytest.fixture(autouse=True)
def _bluetooth_is_loaded(hass: HomeAssistant) -> None:
    """Mark the Bluetooth dependencies as set up; the tests patch the calls the integration makes."""
    hass.config.components.add("bluetooth")
    hass.config.components.add("bluetooth_adapters")


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for one lock (setup is done by the tests)."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=ADDRESS,
        title="WeLockTest",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret-password",
            CONF_ADDRESS: ADDRESS,
            CONF_BLE_NAME: "WeLockTEST",
            CONF_DEVICE_NUMBER: DEVICE_NUMBER,
            CONF_MODEL: "Smart Lock",
        },
        options={},
    )


class FakeLock:
    """Replaces the Bluetooth exchange: plays the lock's side without any radio."""

    def __init__(self) -> None:
        self.random_factor = 7
        self.battery = 80
        self.fail_to_connect = False
        self.commands_written: list[bytes] = []

    async def exchange(
        self,
        hass: HomeAssistant,
        address: str,
        command_provider: Callable[[BatteryResponse], Coroutine[Any, Any, bytes]] | None = None,
        timeout: float = 15.0,
        report: Any = None,
        confirm_timeout: float = 3.0,
        teardown_runner: Callable[[Any], None] | None = None,
    ) -> BatteryResponse:
        """Same contract as ``custom_components.welock.ble.async_exchange``."""
        from custom_components.welock.ble import WeLockBleError

        if self.fail_to_connect:
            if report is not None:
                report.connect_ms = 20000
            raise WeLockBleError("Could not connect")
        state = BatteryResponse(random_factor=self.random_factor, battery=self.battery)
        if report is not None:
            report.connect_ms = 1500
            report.status_ms = 50
        if command_provider is not None:
            command = await command_provider(state)
            self.commands_written.append(command)
            if report is not None:
                report.command_written = True
                report.confirmed = True
                report.command_ms = 0
                report.confirm_ms = 500

            if teardown_runner is not None:

                async def _teardown() -> None:
                    if report is not None:
                        report.teardown_ms = 30

                teardown_runner(_teardown())
        return state


@pytest.fixture
def fake_lock() -> Iterator[FakeLock]:
    """Patch the Bluetooth presence calls and the exchange with a fake lock."""
    lock = FakeLock()
    info = MagicMock()
    info.rssi = -70
    with (
        patch("custom_components.welock.coordinator.async_exchange", lock.exchange),
        patch(
            "custom_components.welock.coordinator.bluetooth.async_last_service_info",
            return_value=info,
        ),
        patch(
            "custom_components.welock.coordinator.bluetooth.async_address_present",
            return_value=True,
        ),
    ):
        yield lock


@pytest.fixture
def cloud_command() -> Iterator[MagicMock]:
    """Patch the cloud request for an unlock command."""
    with patch(
        "custom_components.welock.api.WeLockApiClient.async_request_unlock_command",
        return_value=CLOUD_COMMAND,
    ) as mock:
        yield mock
