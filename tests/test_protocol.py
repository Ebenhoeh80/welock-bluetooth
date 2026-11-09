"""Unit tests for WeLock BLE protocol module (supports pytest and standard unittest)."""
import unittest
from tools.welock_protocol import (
    BATTERY_REQUEST,
    BatteryResponse,
    parse_battery_response,
)


class TestWeLockProtocol(unittest.TestCase):
    """Test battery exchange protocol."""

    def test_battery_request_structure(self) -> None:
        """Verify BATTERY_REQUEST has length 15 and starts with 0x55 0x30."""
        self.assertEqual(len(BATTERY_REQUEST), 15)
        self.assertEqual(BATTERY_REQUEST[:2], bytes((0x55, 0x30)))
        self.assertEqual(BATTERY_REQUEST[2:], bytes(13))

    def test_parse_battery_response_valid(self) -> None:
        """Verify parsing a valid 4-byte battery notification."""
        raw = bytes((0x55, 0x30, 0x7A, 0x58))  # random_factor=122, battery=88%
        parsed = parse_battery_response(raw)
        self.assertIsInstance(parsed, BatteryResponse)
        self.assertEqual(parsed.random_factor, 122)
        self.assertEqual(parsed.battery, 88)

    def test_parse_battery_response_invalid_length(self) -> None:
        """Verify ValueError is raised if length is not 4."""
        with self.assertRaises(ValueError):
            parse_battery_response(bytes((0x55, 0x30, 0x7A)))

        with self.assertRaises(ValueError):
            parse_battery_response(bytes((0x55, 0x30, 0x7A, 0x58, 0x00)))

    def test_parse_battery_response_invalid_header(self) -> None:
        """Verify ValueError is raised if header is not 0x55 0x30."""
        with self.assertRaises(ValueError):
            parse_battery_response(bytes((0x55, 0x31, 0x7A, 0x58)))


if __name__ == "__main__":
    unittest.main()
