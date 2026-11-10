"""WeLock BLE protocol definitions and parsers."""

from dataclasses import dataclass

BATTERY_REQUEST = b"\x55\x30" + b"\x00" * 13


@dataclass(frozen=True)
class BatteryResponse:
    random_factor: int
    battery: int


def parse_battery_response(data: bytes) -> BatteryResponse:
    if len(data) < 4 or data[:2] != b"\x55\x30":
        raise ValueError("Ungueltige Batterie-Antwort vom Schloss.")
    return BatteryResponse(random_factor=data[2], battery=data[3])
    