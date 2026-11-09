"""Inspect a known BLE device without sending application commands."""

import argparse
import asyncio
import math
import sys

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


async def inspect_device(address: str, timeout: float, connect: bool) -> int:
    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device is None:
        print("Device not found during scan; it may be out of range or using a different address.", file=sys.stderr)
        return 1

    print("Device found during scan.")
    if not connect:
        return 0

    async with BleakClient(device, timeout=timeout) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            print("The expected service was not found.", file=sys.stderr)
            return 1

        characteristics = {characteristic.uuid.lower(): characteristic for characteristic in service.characteristics}
        missing = {WRITE_UUID, NOTIFY_UUID} - characteristics.keys()
        if missing:
            print(f"Expected characteristics not found: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

        print(f"Service: {SERVICE_UUID}")
        for uuid in (WRITE_UUID, NOTIFY_UUID):
            print(f"Characteristic: {uuid}; properties: {', '.join(characteristics[uuid].properties)}")
        print("Inspection complete; no application commands were sent.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True, help="BLE address to inspect; use only your own device.")
    parser.add_argument("--timeout", type=float, default=15, help="Scan and connection timeout in seconds.")
    parser.add_argument("--connect", action="store_true", help="Connect and inspect GATT services without writing.")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a positive finite number")
    try:
        return asyncio.run(inspect_device(args.address, args.timeout, args.connect))
    except (BleakError, OSError, TimeoutError) as exc:
        print(f"Bluetooth inspection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
