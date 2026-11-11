"""Liest den Akkustand und Challenge-Faktor eines WeLock-Schlosses direkt über BLE aus."""

from __future__ import annotations

import argparse
import asyncio
import json
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
    from welock_protocol import (
        BATTERY_REQUEST,
        NOTIFY_UUID,
        SERVICE_UUID,
        WRITE_UUID,
        BatteryResponse,
        parse_battery_response,
    )
except ImportError:
    from tools.dependency_check import check_bleak_installed
    from tools.welock_protocol import (
        BATTERY_REQUEST,
        NOTIFY_UUID,
        SERVICE_UUID,
        WRITE_UUID,
        BatteryResponse,
        parse_battery_response,
    )


async def read_lock_battery(address: str, timeout: float = 15.0, as_json: bool = False) -> int:
    """Verbindet sich mit dem WeLock-Schloss und liest den Akkustand aus."""
    if BleakScanner is None or BleakClient is None:
        _, msg = check_bleak_installed()
        print(f"Fehler: {msg}", file=sys.stderr)
        return 1

    if not as_json:
        print(f"Suche nach WeLock-Schloss [{address}]...")

    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device is None:
        if as_json:
            print(json.dumps({"error": "device_not_found", "address": address}))
        else:
            print(
                f"Fehler: Gerät mit Adresse [{address}] konnte nicht gefunden werden.",
                file=sys.stderr,
            )
            print("Mögliche Ursachen:", file=sys.stderr)
            print(
                "  - Entfernung zu groß (> 3-5m) oder Dämpfung durch massive Türen",
                file=sys.stderr,
            )
            print(
                "  - Schloss ist bereits mit WeLock-App oder WiFiBox verbunden (1 Client max)",
                file=sys.stderr,
            )
            print(
                "  - BLE-Advertising-Intervall verpasst (Timeout erhöhen, z. B. -t 25)",
                file=sys.stderr,
            )
            print(
                "  - Falsche MAC-Adresse (nutzen Sie ./run_ble_scan.sh)",
                file=sys.stderr,
            )
        return 1

    if not as_json:
        name = device.name or "(unbekannt)"
        print(f"Gerät gefunden: '{name}' [{device.address}]. Verbinde...")

    async with BleakClient(device, timeout=timeout) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            msg = f"Der WeLock Nordic UART Service ({SERVICE_UUID}) fehlt auf diesem Gerät."
            if as_json:
                print(json.dumps({"error": "missing_service", "message": msg}))
            else:
                print(f"Fehler: {msg}", file=sys.stderr)
            return 1

        chars = {c.uuid.lower(): c for c in service.characteristics}
        if WRITE_UUID not in chars or NOTIFY_UUID not in chars:
            msg = "Erforderliche Schreib- (TX) oder Benachrichtigungs- (RX) Characteristic fehlt."
            if as_json:
                print(json.dumps({"error": "missing_characteristics", "message": msg}))
            else:
                print(f"Fehler: {msg}", file=sys.stderr)
            return 1

        future_response: asyncio.Future[BatteryResponse] = (
            asyncio.get_running_loop().create_future()
        )

        def notification_handler(_sender: object, data: bytearray) -> None:
            if future_response.done():
                return
            try:
                parsed = parse_battery_response(bytes(data))
                future_response.set_result(parsed)
            except ValueError:
                pass  # Nicht passender Header oder Teildaten ignorieren

        await client.start_notify(chars[NOTIFY_UUID], notification_handler)

        if not as_json:
            print("Sende Batterie- und Challenge-Anfrage (15 Bytes)...")
        await client.write_gatt_char(chars[WRITE_UUID], BATTERY_REQUEST, response=False)

        try:
            result = await asyncio.wait_for(future_response, timeout=6.0)
        except asyncio.TimeoutError:
            if as_json:
                print(json.dumps({"error": "timeout", "address": address}))
            else:
                print(
                    "Fehler: Zeitüberschreitung beim Warten auf die Schloss-Rückmeldung.",
                    file=sys.stderr,
                )
            await client.stop_notify(chars[NOTIFY_UUID])
            return 1

        await client.stop_notify(chars[NOTIFY_UUID])

        if as_json:
            print(
                json.dumps(
                    {
                        "address": address,
                        "battery": result.battery,
                        "random_factor": result.random_factor,
                    },
                    indent=2,
                )
            )
            return 0

        # Formatiertes Terminal-Ergebnis
        battery_bar = "█" * (result.battery // 10) + "░" * (10 - (result.battery // 10))
        status_emoji = "🟢" if result.battery > 50 else ("🟡" if result.battery >= 20 else "🔴")

        print("\n" + "=" * 50)
        print(f"  {status_emoji} WeLock Schloss-Status [{address}]")
        print("=" * 50)
        print(f"  Akkustand:        {result.battery}%  [{battery_bar}]")
        print(f"  Challenge-Faktor: {result.random_factor} (0x{result.random_factor:02X})")
        print("=" * 50)

        if result.battery < 20:
            print("\n⚠️  WARNUNG: Der Batteriestand ist sehr niedrig (< 20%)!")
            print("    Bitte zeitnah 3x AAA Batterien austauschen, um Ausfälle zu vermeiden.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Liest den Akkustand und Challenge-Faktor eines WeLock-Schlosses per BLE aus."
    )
    parser.add_argument(
        "positional_address",
        nargs="?",
        default=None,
        help="BLE-MAC-Adresse des Schlosses (z. B. AA:BB:CC:DD:EE:FF).",
    )
    parser.add_argument(
        "--address",
        "-a",
        type=str,
        default=None,
        help="BLE-Adresse des Schlosses (Alternative zur Positionsangabe).",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=15.0,
        help="Verbindungs-Timeout in Sekunden (Standard: 15.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ausgabe als JSON-Objekt.",
    )

    args = parser.parse_args()
    target_address = args.address or args.positional_address

    if not target_address:
        parser.print_help(sys.stderr)
        print(
            "\nFehler: Bitte geben Sie die BLE-Adresse des Schlosses an.",
            file=sys.stderr,
        )
        print("Beispiel: python ble_battery.py AA:BB:CC:DD:EE:FF", file=sys.stderr)
        print("Oder suchen Sie zuerst mit: python ble_scan.py", file=sys.stderr)
        return 1

    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout muss eine positive Zahl sein.")

    try:
        return asyncio.run(
            read_lock_battery(
                address=target_address.strip(),
                timeout=args.timeout,
                as_json=args.json,
            )
        )
    except (BleakError, OSError, TimeoutError) as exc:
        print(f"Bluetooth-Kommunikation fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
