"""Inspiziert ein bekanntes BLE-Gerät (GATT-Dienste und Characteristics) ohne Applikationsbefehle."""

from __future__ import annotations

import argparse
import asyncio
import math
import sys

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None  # type: ignore[assignment,misc]
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakError = Exception  # type: ignore[assignment,misc]

try:
    from dependency_check import check_bleak_installed
    from welock_protocol import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID
except ImportError:
    from tools.dependency_check import check_bleak_installed
    from tools.welock_protocol import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID


async def inspect_device(address: str, timeout: float, connect: bool) -> int:
    """Sucht nach dem BLE-Gerät und inspiziert optional die GATT-Dienste."""
    if BleakScanner is None or BleakClient is None:
        _, msg = check_bleak_installed()
        print(f"Fehler: {msg}", file=sys.stderr)
        return 1

    print(f"Suche nach BLE-Gerät [{address}]...")
    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device is None:
        print(
            f"Gerät [{address}] wurde nicht gefunden. Stellen Sie sicher, dass es aufgeweckt und in Reichweite ist.",
            file=sys.stderr,
        )
        return 1

    name = device.name or "(unbekannt)"
    print(f"Gerät gefunden: '{name}' [{device.address}].")

    if not connect:
        print("Hinweis: Verbindungstest übersprungen (geben Sie --connect an, um GATT-Services zu prüfen).")
        return 0

    print("Verbinde mit Gerät zur GATT-Inspektion...")
    async with BleakClient(device, timeout=timeout) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            print(f"Warnung: Der WeLock Nordic UART Service ({SERVICE_UUID}) wurde nicht gefunden.", file=sys.stderr)
            print("Verfügbare Services auf diesem Gerät:", file=sys.stderr)
            for s in client.services:
                print(f"  - {s.uuid} ({s.description})", file=sys.stderr)
            return 1

        characteristics = {
            char.uuid.lower(): char for char in service.characteristics
        }
        missing = {WRITE_UUID.lower(), NOTIFY_UUID.lower()} - characteristics.keys()
        if missing:
            print(f"Fehlende WeLock-Characteristics: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

        print("\n" + "=" * 65)
        print("  GATT-Service Inspektion (Nordic UART Service)")
        print("=" * 65)
        print(f"  Service-UUID:    {SERVICE_UUID}")
        for uuid in (WRITE_UUID, NOTIFY_UUID):
            char_obj = characteristics[uuid.lower()]
            props = ", ".join(char_obj.properties)
            role = "Schreiben (TX)" if uuid == WRITE_UUID else "Benachrichtigung (RX)"
            print(f"  Char ({role}): {uuid}")
            print(f"    Eigenschaften: {props}")
        print("=" * 65)
        print("Inspektion erfolgreich abgeschlossen. Es wurden keine Befehle gesendet.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspiziert ein bekanntes WeLock BLE-Gerät ohne Befehle zu übertragen."
    )
    parser.add_argument(
        "positional_address",
        nargs="?",
        default=None,
        help="BLE-Adresse des Schlosses (optional als erstes Positionsargument).",
    )
    parser.add_argument(
        "--address",
        "-a",
        type=str,
        default=None,
        help="BLE-Adresse des zu untersuchenden Schlosses.",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=15.0,
        help="Timeout für Scan und Verbindung in Sekunden (Standard: 15.0).",
    )
    parser.add_argument(
        "--connect",
        "-c",
        action="store_true",
        help="Verbinden und GATT-Services/Characteristics prüfen.",
    )

    args = parser.parse_args()
    target_address = args.address or args.positional_address

    if not target_address:
        parser.print_help(sys.stderr)
        print("\nFehler: Bitte geben Sie eine BLE-Adresse an (--address oder als Argument).", file=sys.stderr)
        return 1

    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout muss eine positive Zahl sein.")

    try:
        return asyncio.run(inspect_device(target_address.strip(), args.timeout, args.connect))
    except (BleakError, OSError, TimeoutError) as exc:
        print(f"Bluetooth-Inspektion fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
