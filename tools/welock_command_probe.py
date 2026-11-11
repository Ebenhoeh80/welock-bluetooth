"""Fordert einen experimentellen Cloud-Befehl anhand einer frischen BLE-Challenge an.

Standardmäßig wird KEIN Entriegelungsbefehl an das Schloss übertragen.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import math
import sys
import warnings

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None  # type: ignore[assignment,misc]
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakError = Exception  # type: ignore[assignment,misc]

try:
    from dependency_check import check_bleak_installed
except ImportError:
    from tools.dependency_check import check_bleak_installed

try:
    from welock_cloud_login import CloudError, CloudSession
    from welock_protocol import (
        BATTERY_REQUEST,
        NOTIFY_UUID,
        SERVICE_UUID,
        WRITE_UUID,
        BatteryResponse,
        parse_battery_response,
    )
except ImportError:
    from tools.welock_cloud_login import CloudError, CloudSession
    from tools.welock_protocol import (
        BATTERY_REQUEST,
        NOTIFY_UUID,
        SERVICE_UUID,
        WRITE_UUID,
        BatteryResponse,
        parse_battery_response,
    )

TIMEOUT = 15.0


async def probe(
    session: CloudSession,
    address: str,
    device_number: str,
    device_name: str,
    *,
    timeout: float = TIMEOUT,
    send_unlock: bool = False,
    as_json: bool = False,
) -> bytes:
    """Liest BLE-Status, fragt Cloud-Befehl an und sendet ihn optional zum Entriegeln."""
    if BleakScanner is None or BleakClient is None:
        _, msg = check_bleak_installed()
        raise RuntimeError(f"BLE-Modul fehlt: {msg}")

    if not as_json:
        print(f"Suche nach BLE-Schloss [{address}]...")
    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device is None:
        raise RuntimeError(
            f"Das BLE-Gerät [{address}] nicht gefunden (Reichweite/Adapter prüfen)."
        )

    async with BleakClient(device, timeout=timeout) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            raise RuntimeError(f"Der erwartete WeLock BLE-Service ({SERVICE_UUID}) fehlt.")

        chars = {char.uuid.lower(): char for char in service.characteristics}
        if WRITE_UUID not in chars or NOTIFY_UUID not in chars:
            raise RuntimeError("Erforderliche BLE-Characteristics (TX/RX) fehlen auf dem Schloss.")

        response: asyncio.Future[BatteryResponse] = asyncio.get_running_loop().create_future()
        followup: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        waiting_for_followup = False

        def notification(_sender: object, data: bytearray) -> None:
            if waiting_for_followup and not followup.done():
                followup.set_result(None)
            if response.done():
                return
            if len(data) >= 2 and data[:2] == b"\x55\x30":
                try:
                    response.set_result(parse_battery_response(bytes(data)))
                except ValueError as exc:
                    response.set_exception(exc)

        await client.start_notify(chars[NOTIFY_UUID], notification)
        if not as_json:
            print("Sende Batterie- und Challenge-Anfrage per BLE...")
        await client.write_gatt_char(chars[WRITE_UUID], BATTERY_REQUEST, response=False)

        state = await asyncio.wait_for(response, timeout)
        if not as_json:
            print(f"BLE-Antwort: Akkustand {state.battery}%, Challenge {state.random_factor}")
            print("Fordere autorisierten Befehl von der WeLock Cloud API an...")

        command = await asyncio.to_thread(
            session.request_unlock_command,
            device_number,
            device_name,
            state.random_factor,
            state.battery,
        )

        if send_unlock:
            if len(command) != 15 or not command.startswith(b"U1") or not command.isalnum():
                raise RuntimeError("Cloud-Command hat nicht erwartetes Format (U1...); kein Write.")
            waiting_for_followup = True
            if not as_json:
                print("\n[Achtung] Frischer Befehl wird einmalig an das Schloss geschrieben...")
                print("Hinweis: Zwischen Entriegelungen mindestens 30 Sekunden Abstand halten.")
            await client.write_gatt_char(chars[WRITE_UUID], command, response=False)
            if not as_json:
                print("BLE-Befehl erfolgreich übertragen.")
            try:
                await asyncio.wait_for(followup, timeout)
                if not as_json:
                    print("Bestätigungs-Notification vom Schloss empfangen.")
            except asyncio.TimeoutError:
                if not as_json:
                    print("Keine anschließende Notification empfangen.")

        await client.stop_notify(chars[NOTIFY_UUID])
        return command


async def discover_devices(timeout: float = TIMEOUT) -> list[tuple[str, str]]:
    """Hilfsfunktion: Sucht BLE-Geräte in Reichweite."""
    if BleakScanner is None:
        return []
    devices = await BleakScanner.discover(timeout=timeout)
    return sorted(
        ((device.address, device.name or "(unbekannt)") for device in devices),
        key=lambda item: item[1],
    )


def run_interactive(
    *,
    send_unlock: bool = False,
    address: str | None = None,
    account: str | None = None,
    number: str | None = None,
    name: str | None = None,
    timeout: float = TIMEOUT,
    auto_yes: bool = False,
    show_command: bool = False,
    as_json: bool = False,
) -> int:
    """Ausführung für Command-Probe oder autorisierten Unlock."""
    if BleakScanner is None:
        _, msg = check_bleak_installed()
        if as_json:
            print(json.dumps({"error": "missing_dependency", "message": msg}))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        return 1

    if not as_json:
        if send_unlock:
            print("=" * 70)
            print("  AUTORISIERTER ENTRIEGELUNGSTEST (Vor-Ort BLE-Unlock)")
            print("=" * 70)
            print("Dieser Test sendet einen echten 15-Byte-Befehl an das WeLock-Schloss.")
            print("Bleiben Sie vor Ort am Schloss und halten Sie mindestens 30 Sekunden Abstand.")
        else:
            print("=" * 70)
            print("  WeLock Hybrid Command-Probe (Test ohne Entriegelung)")
            print("=" * 70)
            print("Fragt einen Cloud-Befehl anhand der BLE-Challenge an, sendet ihn aber NICHT.")

    if not auto_yes and not as_json:
        if input("Fortfahren? JA eingeben: ").strip() != "JA":
            print("Abgebrochen; keine Aktion durchgeführt.")
            return 1

        confirm_prompt = "Einmaligen Unlock-Befehl senden? ENTRIEGELN eingeben: "
        if send_unlock and input(confirm_prompt).strip() != "ENTRIEGELN":
            print("Abgebrochen; Schloss wird nicht entriegelt.")
            return 1

    if not account:
        account = input("WeLock-Konto (E-Mail): ").strip()

    if not address:
        address = input("BLE-Adresse des Schlosses (Enter = jetzt suchen): ").strip()
        if not address:
            try:
                print("Suche nach BLE-Geräten...")
                devices = asyncio.run(discover_devices(timeout=timeout))
            except (BleakError, OSError, TimeoutError) as exc:
                print(f"BLE-Suche fehlgeschlagen: {exc}", file=sys.stderr)
                return 1

            if not devices:
                print(
                    "Keine BLE-Geräte gefunden. Funkreichweite oder Timeout prüfen.",
                    file=sys.stderr,
                )
                return 1

            print("\nGefundene BLE-Geräte:")
            for index, (candidate_address, dname) in enumerate(devices, 1):
                print(f"  [{index}] {dname} ({candidate_address})")
            selection = input("\nNummer Ihres Schlosses: ").strip()
            if not selection.isdecimal() or not 1 <= int(selection) <= len(devices):
                print("Ungültige Auswahl; abgebrochen.", file=sys.stderr)
                return 1
            address = devices[int(selection) - 1][0]

    if not number:
        number = input("Schlossnummer (deviceNumber, z.B. C41...): ").strip()

    if not account or not address or not number:
        msg = "E-Mail, BLE-Adresse und Schlossnummer sind erforderlich."
        if as_json:
            print(json.dumps({"error": "missing_parameters", "message": msg}))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        return 1

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("WeLock-Passwort (verdeckte Eingabe): ")

        session = CloudSession()
        session.authenticate(account, password)
        del password
        if not as_json:
            print("Cloud-Anmeldung erfolgreich.")

        if not name:
            if not as_json:
                print("Lade WeLock-Geräteliste aus der Cloud...")
            dev_list = session.list_devices()
            if not dev_list:
                raise CloudError("Keine BLE-fähigen Schlösser im WeLock-Konto gefunden.")
            if len(dev_list) == 1 and auto_yes:
                number, _, name = dev_list[0]
            else:
                print("\nRegistrierte Schlösser im Konto:")
                for index, (candidate_number, candidate_name, ble_name) in enumerate(dev_list, 1):
                    msg_item = (
                        f"  [{index}] Schloss: {candidate_number} | "
                        f"Name: {candidate_name} | BLE: {ble_name}"
                    )
                    print(msg_item)
                selection = input("\nNummer des zugehörigen Schlosses: ").strip()
                if not selection.isdecimal() or not 1 <= int(selection) <= len(dev_list):
                    raise CloudError("Kein Schloss ausgewählt.")
                number, _, name = dev_list[int(selection) - 1]

        command = asyncio.run(
            probe(
                session,
                address,
                number,
                name,
                timeout=timeout,
                send_unlock=send_unlock,
                as_json=as_json,
            )
        )

    except getpass.GetPassWarning:
        msg = "Verdeckte Passworteingabe wird im aktuellen Terminal nicht unterstützt."
        if as_json:
            print(json.dumps({"error": "getpass_unsupported", "message": msg}))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        return 1
    except (CloudError, BleakError, OSError, TimeoutError, RuntimeError, ValueError) as exc:
        if as_json:
            print(json.dumps({"error": "execution_failed", "message": str(exc)}))
        else:
            print(f"Fehler beim Testlauf: {exc}", file=sys.stderr)
        return 1

    if as_json:
        result_payload = {
            "success": True,
            "address": address,
            "device_number": number,
            "device_name": name,
            "unlocked": send_unlock,
            "command_length": len(command),
        }
        if show_command:
            result_payload["command_hex"] = command.hex()
        print(json.dumps(result_payload, indent=2))
        return 0

    if send_unlock:
        print("\n" + "=" * 50)
        print("  Befehl gesendet. Bitte mechanisch prüfen, ob der Außenknauf einkuppelt.")
        print("=" * 50)
        return 0

    print(f"\nErfolg: Cloud lieferte einen gültigen Befehl mit {len(command)} Bytes.")
    print("Der Befehl wurde absichtlich NICHT an das Schloss gesendet.")
    prompt_show = "Hex-Befehl lokal im Terminal anzeigen? [j/N]: "
    if show_command or input(prompt_show).strip().lower() in ("j", "ja", "y"):
        print(f"Befehl: {command.hex()}")
    return 0


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    """Erstellt den gemeinsamen ArgumentParser für Probe und Unlock."""
    parser = argparse.ArgumentParser(description=description)
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
        help="BLE-MAC-Adresse des Schlosses.",
    )
    parser.add_argument(
        "--account",
        "-u",
        type=str,
        default=None,
        help="WeLock-Konto / E-Mail-Adresse.",
    )
    parser.add_argument(
        "--number",
        "-n",
        type=str,
        default=None,
        help="Schlossnummer (deviceNumber, z. B. C41...).",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Cloud-BLE-Gerätename des Schlosses.",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=15.0,
        help="Verbindungs-Timeout in Sekunden (Standard: 15.0).",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Sicherheitsbestätigung automatisch akzeptieren.",
    )
    parser.add_argument(
        "--show-command",
        action="store_true",
        help="Empfangenen 15-Byte-Befehl als Hex-String anzeigen.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ausgabe als JSON-Datenstruktur.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser(
        "WeLock Hybrid Command-Probe: Liest BLE-Challenge & holt Cloud-Befehl (ohne Unlock)."
    )
    args = parser.parse_args()

    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout muss eine positive Zahl sein.")

    target_address = args.address or args.positional_address

    try:
        return run_interactive(
            send_unlock=False,
            address=target_address,
            account=args.account,
            number=args.number,
            name=args.name,
            timeout=args.timeout,
            auto_yes=args.yes,
            show_command=args.show_command,
            as_json=args.json,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
