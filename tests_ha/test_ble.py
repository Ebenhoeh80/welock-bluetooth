"""The Bluetooth exchange with a fake lock (no radio); runs inside a real Home Assistant core (CI only)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant

from custom_components.welock import ble
from custom_components.welock.protocol import BATTERY_REQUEST, WRITE_UUID

from .conftest import ADDRESS

COMMAND = b"U1ABCDEFGHIJKLM"
STATUS = bytes((0x55, 0x30, 7, 80))


class FakeClient:
    """Plays the lock: answers the status request and, after an unlock command, notifies once."""

    def __init__(
        self,
        *,
        answer_status: bool = True,
        confirm: bool = True,
        junk_first: bool = False,
        fail_stop: bool = False,
        fail_disconnect: bool = False,
        hang_disconnect: bool = False,
    ) -> None:
        self.answer_status = answer_status
        self.confirm = confirm
        self.junk_first = junk_first
        self.fail_stop = fail_stop
        self.fail_disconnect = fail_disconnect
        self.hang_disconnect = hang_disconnect
        self.callback = None
        self.written: list[bytes] = []
        self.stopped = False
        self.disconnected = False

    async def start_notify(self, uuid: str, callback) -> None:
        self.callback = callback

    async def write_gatt_char(self, uuid: str, data: bytes, response: bool = False) -> None:
        self.written.append(bytes(data))
        if data == BATTERY_REQUEST:
            if self.junk_first:
                self.callback(None, bytearray(b"\x01\x02"))
            if self.answer_status:
                self.callback(None, bytearray(STATUS))
        elif self.confirm:
            self.callback(None, bytearray(b"\x99\x99"))

    async def stop_notify(self, uuid: str) -> None:
        if self.fail_stop:
            raise BleakError("stop failed")
        self.stopped = True

    async def disconnect(self) -> None:
        if self.hang_disconnect:
            await asyncio.Event().wait()  # a proxy that never answers the disconnect
        if self.fail_disconnect:
            raise BleakError("disconnect failed")
        self.disconnected = True


def _patches(client: FakeClient | Exception, device: object | None = MagicMock()):
    info = SimpleNamespace(time=0.0, rssi=-65, source="proxy-source-1")
    connect = (
        MagicMock(side_effect=client)
        if isinstance(client, Exception)
        else MagicMock(return_value=client)
    )

    async def establish(*args, ble_device_callback=None, **kwargs):
        if ble_device_callback is not None:
            ble_device_callback()
        return connect()

    return (
        patch.object(ble.bluetooth, "async_ble_device_from_address", return_value=device),
        patch.object(ble.bluetooth, "async_last_service_info", return_value=info),
        patch.object(ble, "establish_connection", establish),
    )


async def _run(hass: HomeAssistant, client, **kwargs):
    a, b, c = _patches(client)
    with a, b, c:
        return await ble.async_exchange(hass, ADDRESS, confirm_timeout=0.05, timeout=0.2, **kwargs)


async def test_a_status_check_reads_battery_and_challenge_and_disconnects(
    hass: HomeAssistant,
) -> None:
    client = FakeClient(junk_first=True)
    report = ble.ExchangeReport()
    state = await _run(hass, client, report=report)
    assert (state.random_factor, state.battery) == (7, 80)
    assert client.written == [BATTERY_REQUEST]
    assert client.stopped and client.disconnected
    assert report.connect_ms is not None and report.status_ms is not None
    assert report.rssi == -65 and report.adv_age_ms is not None and report.connect_attempts == 2
    assert not report.command_written and report.teardown_ms is not None
    # the scanner is noted as a neutral label, never as the address it came from
    assert report.scanner == ble.scanner_label("proxy-source-1")
    assert report.scanner is not None and "proxy-source-1" not in report.scanner


async def test_an_unlock_writes_the_command_and_notes_the_confirmation(hass: HomeAssistant) -> None:
    client = FakeClient()
    report = ble.ExchangeReport()

    async def provider(state):
        assert state.random_factor == 7
        return COMMAND

    await _run(hass, client, command_provider=provider, report=report)
    assert client.written == [BATTERY_REQUEST, COMMAND]
    assert report.command_written and report.confirmed and report.confirm_ms is not None


async def test_an_unconfirmed_unlock_is_not_an_error(hass: HomeAssistant) -> None:
    client = FakeClient(confirm=False)
    report = ble.ExchangeReport()

    async def provider(state):
        return COMMAND

    await _run(hass, client, command_provider=provider, report=report)
    assert report.command_written and not report.confirmed


async def test_the_teardown_can_be_handed_to_the_caller(hass: HomeAssistant) -> None:
    client = FakeClient()
    handed: list = []

    async def provider(state):
        return COMMAND

    await _run(hass, client, command_provider=provider, teardown_runner=handed.append)
    assert len(handed) == 1 and not client.disconnected
    await handed[0]
    assert client.disconnected


async def test_a_hanging_disconnect_cannot_hold_the_lock_slot(hass: HomeAssistant) -> None:
    """A disconnect that never returns must be bounded, or every later unlock is 'lock_busy'."""
    client = FakeClient(hang_disconnect=True)
    report = ble.ExchangeReport()
    with patch.object(ble, "TEARDOWN_TIMEOUT", 0.05):
        await asyncio.wait_for(_run(hass, client, report=report), 1)
    assert client.stopped
    assert not client.disconnected  # the hanging call was cancelled
    assert report.teardown_ms is not None


async def test_errors_while_closing_are_swallowed(hass: HomeAssistant) -> None:
    client = FakeClient(fail_stop=True, fail_disconnect=True)
    report = ble.ExchangeReport()
    await _run(hass, client, report=report)
    assert report.teardown_ms is not None


async def test_a_lock_that_does_not_answer_raises_and_still_disconnects(
    hass: HomeAssistant,
) -> None:
    client = FakeClient(answer_status=False)
    with pytest.raises(ble.WeLockBleError):
        await _run(hass, client)
    assert client.disconnected


async def test_a_bad_command_from_the_cloud_raises(hass: HomeAssistant) -> None:
    async def provider(state):
        return b"not a command"

    with pytest.raises(ble.WeLockBleError):
        await _run(hass, FakeClient(), command_provider=provider)


async def test_a_malformed_status_answer_raises(hass: HomeAssistant) -> None:
    class Short(FakeClient):
        async def write_gatt_char(self, uuid, data, response=False):
            self.written.append(bytes(data))
            if data == BATTERY_REQUEST:
                self.callback(None, bytearray(b"\x55\x30\x01"))

    with pytest.raises(ble.WeLockBleError):
        await _run(hass, Short())


async def test_no_path_to_the_lock_raises_not_in_range(hass: HomeAssistant) -> None:
    with (
        patch.object(ble.bluetooth, "async_ble_device_from_address", return_value=None),
        pytest.raises(ble.LockNotInRange),
    ):
        await ble.async_exchange(hass, ADDRESS)


@pytest.mark.parametrize("error", [BleakError("no"), asyncio.TimeoutError(), OSError("no")])
async def test_a_failed_connection_is_reported(hass: HomeAssistant, error: Exception) -> None:
    report = ble.ExchangeReport()
    with pytest.raises(ble.WeLockBleError):
        await _run(hass, error, report=report)
    assert report.connect_ms is not None and report.connect_attempts == 2


def test_lock_in_range_follows_the_bluetooth_cache() -> None:
    with patch.object(ble.bluetooth, "async_ble_device_from_address", return_value=object()):
        assert ble.lock_in_range(MagicMock(), ADDRESS) is True
    with patch.object(ble.bluetooth, "async_ble_device_from_address", return_value=None):
        assert ble.lock_in_range(MagicMock(), ADDRESS) is False


def test_the_write_characteristic_is_known() -> None:
    assert WRITE_UUID
