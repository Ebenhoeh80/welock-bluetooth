"""Unit tests for WeLock diagnostic tools and helper functions."""

from __future__ import annotations

import unittest
from tools.ble_scan import is_likely_welock
from tools.dependency_check import check_bluetooth_system, check_python_version
from tools.welock_protocol import (
    BATTERY_REQUEST,
    NOTIFY_UUID,
    SERVICE_UUID,
    WRITE_UUID,
    BatteryResponse,
    parse_battery_response,
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
        self.assertTrue(
            is_likely_welock("Unknown Device", [SERVICE_UUID.lower()])
        )
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


if __name__ == "__main__":
    unittest.main()
