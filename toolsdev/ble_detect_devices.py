"""Einfacher BLE-Gerätescanner zur Erkennung von Bluetooth Low Energy Geräten in der Nähe."""

import asyncio
import subprocess
import sys


def ensure_dependencies() -> None:
    """Prüft, ob pip und bleak vorhanden sind, und installiert bleak falls nötig."""
    try:
        import pip
    except ImportError:
        print("pip ist nicht installiert. Versuche pip zu installieren...", file=sys.stderr)
        try:
            import ensurepip
            ensurepip.bootstrap()
        except Exception as e:
            print(f"Fehler beim Installieren von pip: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        import bleak  # noqa: F401
    except ImportError:
        print("Die Bibliothek 'bleak' ist nicht installiert. Wird automatisch installiert...", file=sys.stderr)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "bleak"])
            print("'bleak' wurde erfolgreich installiert.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei der Installation von 'bleak': {e}", file=sys.stderr)
            sys.exit(1)


# Abhängigkeiten vor dem Start prüfen
ensure_dependencies()

from bleak import BleakScanner
from bleak.exc import BleakError

TIMEOUT = 10.0


async def scan_devices() -> None:
    print(f"Suche nach BLE-Geräten für {TIMEOUT} Sekunden...")
    try:
        devices = await BleakScanner.discover(timeout=TIMEOUT, return_adv=True)
    except BleakError as exc:
        print(f"Fehler beim Bluetooth-Scan: {exc}", file=sys.stderr)
        return

    if not devices:
        print("Keine BLE-Geräte gefunden.")
        return

    print(f"\nGefundene BLE-Geräte ({len(devices)}):")
    print("-" * 75)
    print(f"{'Nr.':<4} | {'Name':<25} | {'Adresse / UUID':<20} | RSSI")
    print("-" * 75)

    # devices ist bei return_adv=True ein Dictionary: {device: (BLEDevice, AdvertisementData)}
    # Wir sortieren nach RSSI (falls vorhanden, sonst Standard 0)
    device_list = list(devices.values())
    sorted_devices = sorted(
        device_list,
        key=lambda item: item[1].rssi if item[1] and hasattr(item[1], 'rssi') else -999,
        reverse=True
    )

    for index, (device, adv_data) in enumerate(sorted_devices, 1):
        name = device.name or "(unbekannt)"
        rssi = f"{adv_data.rssi} dBm" if adv_data and hasattr(adv_data, 'rssi') else "n/a"
        print(f"{index:<4} | {name:<25} | {device.address:<20} | {rssi}")
    print("-" * 75)


def main() -> int:
    try:
        asyncio.run(scan_devices())
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nScan abgebrochen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())