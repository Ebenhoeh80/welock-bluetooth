"""WeLock BLE protocol helpers (Nordic UART Service). Pure functions, no I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

BATTERY_REQUEST = bytes((0x55, 0x30)) + bytes(13)
BATTERY_RESPONSE_HEADER = bytes((0x55, 0x30))
UNLOCK_COMMAND_LENGTH = 15
UNLOCK_COMMAND_PREFIX = b"U1"


@dataclass(frozen=True)
class BatteryResponse:
    """Status answer of the lock: challenge factor and battery percentage."""

    random_factor: int
    battery: int


def parse_battery_response(value: bytes) -> BatteryResponse:
    """Parse the four-byte status response ``55 30 <random_factor> <battery>``."""
    if len(value) != 4:
        raise ValueError(f"Expected a four-byte battery response, got {len(value)} bytes")
    if value[:2] != BATTERY_RESPONSE_HEADER:
        raise ValueError("Unexpected battery response header")
    return BatteryResponse(random_factor=value[2], battery=value[3])


def is_battery_response(value: bytes) -> bool:
    """Return True if a notification looks like a status response."""
    return len(value) >= 2 and value[:2] == BATTERY_RESPONSE_HEADER


def validate_unlock_command(command: bytes) -> bytes:
    """Ensure the cloud command has the expected 15-byte ``U1...`` form."""
    if (
        len(command) != UNLOCK_COMMAND_LENGTH
        or not command.startswith(UNLOCK_COMMAND_PREFIX)
        or not command.isalnum()
    ):
        raise ValueError("Cloud command does not have the expected 15-byte U1... form")
    return command


def format_mac(value: str) -> str | None:
    """Normalise ``AABBCCDDEEFF`` / ``aa-bb-...`` to ``AA:BB:CC:DD:EE:FF``."""
    hex_only = re.sub(r"[^0-9A-Fa-f]", "", value or "")
    if len(hex_only) != 12:
        return None
    hex_only = hex_only.upper()
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
