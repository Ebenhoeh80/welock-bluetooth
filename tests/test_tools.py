"""Unit tests for WeLock diagnostic tools, helper functions, and CLI argument parsing."""

from __future__ import annotations

import unittest

from tools.ble_scan import is_likely_welock
from tools.dependency_check import check_bluetooth_system, check_python_version
from tools.welock_command_probe import build_arg_parser
from tools.welock_protocol import (
    NOTIFY_UUID,
    SERVICE_UUID,
    WRITE_UUID,
)


class TestWeLockTools(unittest.TestCase):
    """Test tools utility functions and heuristics."""

    def test_welock_name_detection(self) -> None:
        """Verify device names are correctly recognized as WeLock."""
        self.assertTrue(is_likely_welock("Touch41_A1B2"))
        self.assertTrue(is_likely_welock("SECBN51_98F1"))
        self.assertTrue(is_likely_welock("PCB41_C123"))
        self.assertTrue(is_likely_welock("WeLock Door"))
        self.assertTrue(is_likely_welock("SmartLock_Front"))

        # Non-lock devices
        self.assertFalse(is_likely_welock("iPhone von Max"))
        self.assertFalse(is_likely_welock("Samsung TV"))
        self.assertFalse(is_likely_welock("JBL Flip 5"))
        self.assertFalse(is_likely_welock(None))

    def test_welock_service_uuid_detection(self) -> None:
        """Verify Nordic UART Service UUID is detected."""
        self.assertTrue(is_likely_welock("Unknown Device", [SERVICE_UUID.lower()]))
        self.assertFalse(
            is_likely_welock("Unknown Device", ["0000180f-0000-1000-8000-00805f9b34fb"])
        )

    def test_protocol_uuids(self) -> None:
        """Verify standard Nordic UART Service UUIDs."""
        self.assertEqual(SERVICE_UUID, "6e400001-b5a3-f393-e0a9-e50e24dcca9e")
        self.assertEqual(WRITE_UUID, "6e400002-b5a3-f393-e0a9-e50e24dcca9e")
        self.assertEqual(NOTIFY_UUID, "6e400003-b5a3-f393-e0a9-e50e24dcca9e")

    def test_python_version_check(self) -> None:
        """Verify python version check passes on Python 3.10+."""
        ok, msg = check_python_version()
        self.assertTrue(ok)
        self.assertIn("OK", msg)

    def test_bluetooth_system_check(self) -> None:
        """Verify platform system detection."""
        ok, msg = check_bluetooth_system()
        self.assertTrue(ok)
        self.assertIsInstance(msg, str)

    def test_command_probe_arg_parser_options(self) -> None:
        """Verify argument parser handles positional and option flags properly."""
        parser = build_arg_parser("Test Probe Parser")

        # Test long options with values
        args1 = parser.parse_args(
            [
                "--address",
                "AA:BB:CC:DD:EE:FF",
                "--account",
                "test@example.com",
                "--number",
                "C411234",
                "--name",
                "Touch41_1234",
                "--timeout",
                "25.5",
                "--yes",
                "--show-command",
                "--json",
            ]
        )
        self.assertEqual(args1.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(args1.account, "test@example.com")
        self.assertEqual(args1.number, "C411234")
        self.assertEqual(args1.name, "Touch41_1234")
        self.assertEqual(args1.timeout, 25.5)
        self.assertTrue(args1.yes)
        self.assertTrue(args1.show_command)
        self.assertTrue(args1.json)

        # Test short options and positional address
        args2 = parser.parse_args(
            [
                "11:22:33:44:55:66",
                "-u",
                "user@domain.de",
                "-n",
                "SEC5199",
                "-t",
                "10",
                "-y",
            ]
        )
        self.assertEqual(args2.positional_address, "11:22:33:44:55:66")
        self.assertEqual(args2.account, "user@domain.de")
        self.assertEqual(args2.number, "SEC5199")
        self.assertEqual(args2.timeout, 10.0)
        self.assertTrue(args2.yes)
        self.assertFalse(args2.json)


if __name__ == "__main__":
    unittest.main()
