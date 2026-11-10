"""Fordert einen experimentellen Cloud-Befehl anhand einer frischen BLE-Challenge an.

Standardmäßig wird KEIN Entriegelungsbefehl an das Schloss übertragen.
"""

from __future__ import annotations

import asyncio
import getpass
import json
import sys
import warnings

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None  # type: ignore[assignment,misc]
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakError = Exception  # type: ignore[assignment,misc]

from dependency_check import check_bleak_installed

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
    send_unlock: bool = False,
) -> bytes:
    """Liest BLE-Status, fragt Cloud-Befehl an und sendet ihn optional zum Entriegeln."""
    if BleakScanner is None or BleakClient is None:
        _, msg = check_bleak_installed()
        raise RuntimeError(f"BLE-Modul fehlt: {msg}")

    print(f"Suche nach BLE-Schloss [{address}]...")
    device = await BleakScanner.find_device_by_address(address, timeout=TIMEOUT)
    if device is None:
        raise RuntimeError(f"Das BLE-Gerät [{address}] wurde nicht gefunden (in Reichweite? aufgeweckt?).")

    async with BleakClient(device, timeout=TIMEOUT) as client:
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
        print("Sende Batterie- und Challenge-Anfrage per BLE...")
        await client.write_gatt_char(chars[WRITE_UUID], BATTERY_REQUEST, response=False)

        state = await asyncio.wait_for(response, TIMEOUT)
        print(f"BLE-Antwort empfangen: Akkustand {state.battery}%, Challenge {state.random_factor}")

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
                raise RuntimeError("Cloud-Command hat nicht die erwartete 15-Byte-Form (U1...); kein Write.")
            waiting_for_followup = True
            print("\n[Achtung] Frischer Cloud-Befehl wird einmalig an das Schloss geschrieben...")
            print("Hinweis: Zwischen Entriegelungen mindestens 30 Sekunden Abstand halten.")
            await client.write_gatt_char(chars[WRITE_UUID], command, response=False)
            print("BLE-Befehl erfolgreich übertragen.")
            try:
                await asyncio.wait_for(followup, TIMEOUT)
                print("Bestätigungs-Notification vom Schloss empfangen.")
            except asyncio.TimeoutError:
                print("Keine anschließende Notification empfangen.")

        await client.stop_notify(chars[NOTIFY_UUID])
        return command


async def discover_devices() -> list[tuple[str, str]]:
    """Hilfsfunktion: Sucht BLE-Geräte in Reichweite."""
    if BleakScanner is None:
        return []
    devices = await BleakScanner.discover(timeout=TIMEOUT)
    return sorted(
        ((device.address, device.name or "(unbekannt)") for device in devices),
        key=lambda item: item[1],
    )


def run_interactive(*, send_unlock: bool = False) -> int:
    """Interaktive Ausführung für Command-Probe oder autorisierten Unlock."""
    if BleakScanner is None:
        _, msg = check_bleak_installed()
        print(f"Fehler: {msg}", file=sys.stderr)
        return 1

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

    if input("Fortfahren? JA eingeben: ").strip() != "JA":
        print("Abgebrochen; keine Aktion durchgeführt.")
        return 1

    if send_unlock and input("Einmaligen Unlock-Befehl senden? ENTRIEGELN eingeben: ").strip() != "ENTRIEGELN":
        print("Abgebrochen; Schloss wird nicht entriegelt.")
        return 1

    account = input("WeLock-Konto (E-Mail): ").strip()
    address = input("BLE-Adresse des Schlosses (Enter = jetzt suchen): ").strip()

    if not address:
        try:
            print("Suche nach BLE-Geräten...")
            devices = asyncio.run(discover_devices())
        except (BleakError, OSError, TimeoutError) as exc:
            print(f"BLE-Suche fehlgeschlagen: {exc}", file=sys.stderr)
            return 1

        if not devices:
            print("Keine BLE-Geräte gefunden. Schloss aufwecken und wiederholen.", file=sys.stderr)
            return 1

        print("\nGefundene BLE-Geräte:")
        for index, (candidate_address, name) in enumerate(devices, 1):
            print(f"  [{index}] {name} ({candidate_address})")
        selection = input("\nNummer Ihres Schlosses: ").strip()
        if not selection.isdecimal() or not 1 <= int(selection) <= len(devices):
            print("Ungültige Auswahl; abgebrochen.", file=sys.stderr)
            return 1
        address = devices[int(selection) - 1][0]

    number = input("Schlossnummer (deviceNumber, z.B. C41...): ").strip()
    name = input("Cloud-BLE-Gerätename (Enter = aus Cloud-Geräteliste auswählen): ").strip()

    if not account or not address or not number:
        print("Fehler: E-Mail, BLE-Adresse und Schlossnummer sind erforderlich.", file=sys.stderr)
        return 1

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("WeLock-Passwort (verdeckte Eingabe): ")

        session = CloudSession()
        session.authenticate(account, password)
        del password
        print("Cloud-Anmeldung erfolgreich.")

        if not name:
            print("Lade WeLock-Geräteliste aus der Cloud...")
            dev_list = session.list_devices()
            if not dev_list:
                raise CloudError("Keine BLE-fähigen Schlösser im WeLock-Konto gefunden.")
            print("\nRegistrierte Schlösser im Konto:")
            for index, (candidate_number, candidate_name, ble_name) in enumerate(dev_list, 1):
                print(f"  [{index}] Nummer: {candidate_number} | Name: {candidate_name} | BLE: {ble_name}")
            selection = input("\nNummer des zugehörigen Schlosses: ").strip()
            if not selection.isdecimal() or not 1 <= int(selection) <= len(dev_list):
                raise CloudError("Kein Schloss ausgewählt.")
            number, _, name = dev_list[int(selection) - 1]

        if send_unlock:
            command = asyncio.run(probe(session, address, number, name, send_unlock=True))
        else:
            command = asyncio.run(probe(session, address, number, name, send_unlock=False))

    except getpass.GetPassWarning:
        print("Fehler: Verdeckte Passworteingabe wird im aktuellen Terminal nicht unterstützt.", file=sys.stderr)
        return 1
    except (CloudError, BleakError, OSError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Fehler beim Testlauf: {exc}", file=sys.stderr)
        return 1

    if send_unlock:
        print("\n" + "=" * 50)
        print("  Befehl gesendet. Bitte mechanisch prüfen, ob der Außenknauf einkuppelt.")
        print("=" * 50)
        return 0

    print(f"\nErfolg: Cloud lieferte einen gültigen Befehl mit {len(command)} Bytes.")
    print("Der Befehl wurde absichtlich NICHT an das Schloss gesendet.")
    if input("Hex-Befehl lokal im Terminal anzeigen? [j/N]: ").strip().lower() in ("j", "ja", "y"):
        print(f"Befehl: {command.hex()}")
    return 0


def main() -> int:
    try:
        return run_interactive(send_unlock=False)
    except (EOFError, KeyboardInterrupt):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
