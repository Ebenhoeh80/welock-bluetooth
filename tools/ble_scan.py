"""Suche nach Bluetooth Low Energy (BLE) Geräten und WeLock Smart Locks in Reichweite."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys

try:
    from bleak import BleakScanner
    from bleak.exc import BleakError
except ImportError:
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakError = Exception  # type: ignore[assignment,misc]

try:
    from dependency_check import check_bleak_installed
except ImportError:
    from tools.dependency_check import check_bleak_installed

WELOCK_NAME_PREFIXES = ("SECBN", "TOUCH", "PCB", "WELOCK", "LOCK", "SMARTLOCK")
WELOCK_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


def is_likely_welock(name: str | None, service_uuids: list[str] | None = None) -> bool:
    """Prüft, ob ein Gerät anhand von Name oder Service-UUID ein WeLock-Schloss sein könnte."""
    if name:
        upper = name.upper()
        if any(upper.startswith(prefix) or prefix in upper for prefix in WELOCK_NAME_PREFIXES):
            return True
    if service_uuids:
        lower_uuids = [u.lower() for u in service_uuids]
        if WELOCK_SERVICE_UUID.lower() in lower_uuids:
            return True
    return False


async def scan_ble_devices(
    timeout: float,
    filter_term: str | None = None,
    welock_only: bool = False,
    as_json: bool = False,
) -> int:
    """Führt einen BLE-Scan durch und gibt die Ergebnisse formatiert aus."""
    if BleakScanner is None:
        _, msg = check_bleak_installed()
        print(f"Fehler: {msg}", file=sys.stderr)
        return 1

    if not as_json:
        print(f"Starte BLE-Suchlauf für {timeout:.1f} Sekunden...")
        print("Hinweis: Stellen Sie sicher, dass das Schloss aufgeweckt ist (Touchpad kurz berühren).\n")

    try:
        discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
    except BleakError as exc:
        print(f"Bluetooth-Scan fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    results = []
    for _device, (ble_device, adv_data) in discovered.items():
        name = ble_device.name or adv_data.local_name or "(unbekannt)"
        addr = ble_device.address
        rssi = adv_data.rssi if adv_data and hasattr(adv_data, "rssi") else -999
        service_uuids = adv_data.service_uuids if adv_data else []
        is_welock = is_likely_welock(name, service_uuids)

        if filter_term:
            term = filter_term.lower()
            if term not in name.lower() and term not in addr.lower():
                continue

        if welock_only and not is_welock:
            continue

        results.append(
            {
                "name": name,
                "address": addr,
                "rssi": rssi,
                "is_welock": is_welock,
                "service_uuids": service_uuids,
            }
        )

    # Nach Signalstärke sortieren (stärkstes Signal zuerst)
    results.sort(key=lambda item: item["rssi"], reverse=True)

    if as_json:
        print(json.dumps(results, indent=2))
        return 0

    if not results:
        print("Keine BLE-Geräte gefunden.")
        print("Mögliche Ursachen:")
        print("  1. Das Schloss schläft (Deep Sleep) -> Berühren Sie kurz die Tastatur oder den Sensor.")
        print("  2. Entfernung zu groß (> 3-5 Meter).")
        print("  3. Bluetooth am Host deaktiviert oder nicht freigegeben.")
        return 0

    print("=" * 78)
    print(f"{'Typ':<10} | {'Name':<25} | {'Adresse / UUID':<24} | {'Signal (RSSI)':<12}")
    print("=" * 78)

    for item in results:
        type_badge = "🔐 WeLock" if item["is_welock"] else "   BLE"
        rssi_str = f"{item['rssi']} dBm" if item["rssi"] > -999 else "n/a"
        print(f"{type_badge:<10} | {item['name'][:25]:<25} | {item['address'][:24]:<24} | {rssi_str:<12}")

    print("-" * 78)
    print(f"Gesamt gefunden: {len(results)} Gerät(e).")
    welock_count = sum(1 for r in results if r["is_welock"])
    if welock_count > 0:
        print(f"Davon {welock_count} WeLock Smart Lock(s) identifiziert.")
    else:
        print("Tipp: Wenn Ihr Schloss nicht erscheint, wecken Sie es durch Berühren des Tastfelds auf.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BLE-Suchlauf zur Erkennung von WeLock Smart Locks und BLE-Geräten."
    )
    parser.add_argument(
        "positional_filter",
        nargs="?",
        default=None,
        help="Optionaler Suchbegriff für Gerätenamen oder MAC-Adresse (z. B. Touch oder C41).",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=10.0,
        help="Scan-Dauer in Sekunden (Standard: 10.0).",
    )
    parser.add_argument(
        "--filter",
        "-f",
        type=str,
        default=None,
        help="Filterbegriff für Gerätenamen oder MAC-Adresse.",
    )
    parser.add_argument(
        "--welock-only",
        "-w",
        action="store_true",
        help="Nur erkannte WeLock-Schlösser anzeigen.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ausgabe als JSON-Datenstruktur.",
    )

    args = parser.parse_args()

    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout muss eine positive Zahl sein.")

    active_filter = args.filter or args.positional_filter

    try:
        return asyncio.run(
            scan_ble_devices(
                timeout=args.timeout,
                filter_term=active_filter,
                welock_only=args.welock_only,
                as_json=args.json,
            )
        )
    except (KeyboardInterrupt, EOFError):
        print("\nScan durch Benutzer abgebrochen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
