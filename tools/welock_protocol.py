"""Verified WELOCK battery exchange; this module does not unlock the lock."""

from dataclasses import dataclass


BATTERY_REQUEST = bytes((0x55, 0x30)) + bytes(13)
BATTERY_RESPONSE_HEADER = bytes((0x55, 0x30))


@dataclass(frozen=True)
class BatteryResponse:
    random_factor: int
    battery: int


def parse_battery_response(value: bytes) -> BatteryResponse:
    """Parse the observed four-byte response, not other firmware variants."""
    if len(value) != 4:
        raise ValueError(f"Expected a four-byte battery response, got {len(value)} bytes")
    if value[:2] != BATTERY_RESPONSE_HEADER:
        raise ValueError("Unexpected battery response header")
    return BatteryResponse(random_factor=value[2], battery=value[3])
