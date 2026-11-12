"""Unit tests for the WeLock cloud client and BLE protocol helpers (no network, no HA)."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock

# The integration package imports Home Assistant in __init__; stub it for pure-logic tests.
for mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.bluetooth",
    "homeassistant.components.diagnostics",
    "homeassistant.exceptions",
    "bleak",
    "bleak.exc",
    "bleak_retry_connector",
]:
    sys.modules.setdefault(mod, MagicMock())

from custom_components.welock.api import (  # noqa: E402
    CannotConnect,
    InvalidAuth,
    LockUnavailable,
    WeLockApiClient,
    WeLockApiError,
    parse_device_list,
    parse_envelope,
    parse_unlock_command,
)
from custom_components.welock.protocol import (  # noqa: E402
    BATTERY_REQUEST,
    format_mac,
    parse_battery_response,
    validate_unlock_command,
)

# Shape of a real /Device/GetDevices answer; values are made up.
SAMPLE_DEVICES = [
    {
        "type": 1,
        "model": "SECBREBL01",
        "deviceName": "12345678",
        "deviceNumber": "12345678",
        "devicePassword": "x",
        "ble": [
            {
                "position": 1,
                "deviceName": "WeLockABCDE",
                "deviceMac": "AABBCCDDEEFF",
                "devicePassword": None,
                "power": 100,
                "version": None,
            },
            {"position": 2, "deviceName": "WeLockXYZ", "deviceMac": "", "power": 0},
        ],
        "gatewayModel": None,
    },
    {"deviceNumber": "", "ble": []},
    "garbage",
]


class TestApi(unittest.TestCase):
    def test_exceptions_inherit(self) -> None:
        for exc in (InvalidAuth, CannotConnect, LockUnavailable):
            self.assertTrue(issubclass(exc, WeLockApiError))

    def test_repr_hides_password_and_password_not_stripped(self) -> None:
        client = WeLockApiClient("user@example.com", " secret ", session=None)
        self.assertNotIn("secret", repr(client))
        self.assertEqual(client._password, " secret ")
        self.assertEqual(client.username, "user@example.com")

    def test_parse_device_list(self) -> None:
        devices = parse_device_list(SAMPLE_DEVICES)
        self.assertEqual(len(devices), 1)
        dev = devices[0]
        self.assertEqual(dev.device_number, "12345678")
        self.assertEqual(dev.model, "SECBREBL01")
        self.assertEqual([m.name for m in dev.ble], ["WeLockABCDE", "WeLockXYZ"])
        self.assertEqual(dev.ble[0].address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(dev.ble[0].battery, 100)
        self.assertIsNone(dev.ble[1].address)

    def test_parse_device_list_rejects_non_list(self) -> None:
        with self.assertRaises(WeLockApiError):
            parse_device_list({"list": []})

    def test_parse_envelope(self) -> None:
        self.assertEqual(parse_envelope({"code": 0, "data": [1]}), [1])
        for bad in ({"code": 5, "data": None, "msg": "pw=abc"}, {"code": "0"}, [], {"code": 0}):
            with self.assertRaises(WeLockApiError) as ctx:
                parse_envelope(bad)
            self.assertNotIn("pw=abc", str(ctx.exception))

    def test_parse_unlock_command(self) -> None:
        cmd = b"U1ABCDEFGHIJKLM"
        self.assertEqual(parse_unlock_command({"command": cmd.hex()}), cmd)
        for bad in (None, {}, {"command": "abc"}, {"command": "zz"}):
            with self.assertRaises(LockUnavailable):
                parse_unlock_command(bad)


class TestProtocol(unittest.TestCase):
    def test_battery_request(self) -> None:
        self.assertEqual(len(BATTERY_REQUEST), 15)
        self.assertEqual(BATTERY_REQUEST[:2], b"\x55\x30")

    def test_parse_battery_response(self) -> None:
        state = parse_battery_response(bytes((0x55, 0x30, 0x2A, 0x5F)))
        self.assertEqual((state.random_factor, state.battery), (42, 95))
        with self.assertRaises(ValueError):
            parse_battery_response(b"\x55\x31\x00\x00")

    def test_validate_unlock_command(self) -> None:
        self.assertEqual(validate_unlock_command(b"U1ABCDEFGHIJKLM"), b"U1ABCDEFGHIJKLM")
        for bad in (b"U1SHORT", b"X1ABCDEFGHIJKLM", b"U1ABCDEFGHIJK-M"):
            with self.assertRaises(ValueError):
                validate_unlock_command(bad)

    def test_format_mac(self) -> None:
        self.assertEqual(format_mac("aabbccddeeff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(format_mac("AA-BB-CC-DD-EE-FF"), "AA:BB:CC:DD:EE:FF")
        self.assertIsNone(format_mac(""))
        self.assertIsNone(format_mac("AABB"))


if __name__ == "__main__":
    unittest.main()
