"""Request one experimental cloud command using a fresh BLE battery response.

No unlock command is transmitted to the lock.
"""

import asyncio
import getpass
import json
import sys
import warnings

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from tools.ble_probe import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID
from tools.welock_cloud_login import CloudError, CloudSession
from tools.welock_protocol import BATTERY_REQUEST, BatteryResponse, parse_battery_response


TIMEOUT = 15.0


async def probe(
    session: CloudSession, address: str, device_number: str, device_name: str, *, send_unlock: bool = False
) -> bytes:
    device = await BleakScanner.find_device_by_address(address, timeout=TIMEOUT)
    if device is None:
        raise RuntimeError("Das BLE-Geraet wurde nicht gefunden.")
    async with BleakClient(device, timeout=TIMEOUT) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            raise RuntimeError("Der erwartete BLE-Service fehlt.")
        chars = {characteristic.uuid.lower(): characteristic for characteristic in service.characteristics}
        if WRITE_UUID not in chars or NOTIFY_UUID not in chars:
            raise RuntimeError("Die erwarteten BLE-Characteristics fehlen.")
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
        await client.write_gatt_char(chars[WRITE_UUID], BATTERY_REQUEST, response=False)
        state = await asyncio.wait_for(response, TIMEOUT)
        command = await asyncio.to_thread(
            session.request_unlock_command, device_number, device_name, state.random_factor, state.battery
        )
        if send_unlock:
            if len(command) != 15 or not command.startswith(b"U1") or not command.isalnum():
                raise RuntimeError("Cloud-Command hat nicht die fuer diesen Test belegte 15-Byte-Form; kein Unlock-Write.")
            waiting_for_followup = True
            print("Ein frischer Cloud-Command wird einmalig ohne Suffix geschrieben.")
            print("Ab jetzt bei Fehlern nicht sofort wiederholen: mindestens 30 Sekunden Abstand halten.")
            await client.write_gatt_char(chars[WRITE_UUID], command, response=False)
            print("BLE-Write abgeschlossen; das beweist keine mechanische Entriegelung.")
            try:
                await asyncio.wait_for(followup, TIMEOUT)
                print("Eine anschliessende Notification wurde empfangen; ihr Inhalt wurde nicht ausgewertet.")
            except asyncio.TimeoutError:
                print("Keine Notification innerhalb des Zeitlimits; Entriegelung unklar.")
        return command


async def discover_devices() -> list[tuple[str, str]]:
    devices = await BleakScanner.discover(timeout=TIMEOUT)
    return sorted(((device.address, device.name or "(unbekannt)") for device in devices), key=lambda item: item[1])


def run_interactive(*, send_unlock: bool = False) -> int:
    if send_unlock:
        print("Experiment: EIN frischer Cloud-Command wird an das Schloss gesendet und kann es entriegeln.")
        print("Schloss sichern, vor Ort bleiben und keine anderen Unlock-Versuche parallel ausloesen.")
        print("Zwischen Unlock-Versuchen mehr als 30 Sekunden Abstand halten; kein automatisches Warten.")
    else:
        print("Experiment: Cloud-Geraeteliste und/oder Command anfordern; KEIN Unlock-Befehl wird gesendet.")
    print("Die Cloud-Anmeldung kann die WELOCK-App auf anderen Geraeten abmelden.")
    if input("Fortfahren? JA eingeben: ").strip() != "JA":
        print("Abgebrochen; keine Anmeldung oder BLE-Aktion.")
        return 1
    if send_unlock and input("Einmaligen Unlock-Write erlauben? ENTRIEGELN eingeben: ").strip() != "ENTRIEGELN":
        print("Abgebrochen; keine Anmeldung oder BLE-Aktion.")
        return 1
    account = input("WELOCK-E-Mail: ").strip()
    address = input("BLE-Adresse des eigenen Schlosses (Enter = suchen): ").strip()
    if not address:
        try:
            devices = asyncio.run(discover_devices())
        except (BleakError, OSError, TimeoutError) as exc:
            print(f"BLE-Suche fehlgeschlagen: {exc}", file=sys.stderr)
            return 1
        if not devices:
            print("Keine BLE-Geraete gefunden; keine Anmeldung.", file=sys.stderr)
            return 1
        print("Gefundene BLE-Geraete (Kennungen nicht im Chat teilen):")
        for index, (candidate_address, name) in enumerate(devices, 1):
            print(f"{index}: {name} [{candidate_address}]")
        selection = input("Nummer des eigenen Schlosses: ").strip()
        if not selection.isdecimal() or not 1 <= int(selection) <= len(devices):
            print("Ungueltige Auswahl; keine Anmeldung.", file=sys.stderr)
            return 1
        address = devices[int(selection) - 1][0]
    number = input("Schlossnummer: ").strip()
    name = input("Cloud-BLE-Geraetename (Enter = aus erster Seite der Cloud-Geraeteliste auswaehlen): ").strip()
    if not account or not address or not number:
        print("E-Mail, BLE-Adresse und Schlossnummer sind erforderlich; keine Anmeldung oder BLE-Aktion.", file=sys.stderr)
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("WELOCK-Passwort (verdeckte Eingabe): ")
        session = CloudSession()
        session.authenticate(account, password)
        del password
        print("Cloud-Login akzeptiert.")
        if not name:
            print("Cloud-Geraeteliste wird geladen (nur erste Seite; Kennungen nicht im Chat teilen).")
            devices = session.list_devices()
            if not devices:
                raise CloudError("Die erste Seite enthaelt keine auswaehlbaren BLE-Eintraege.")
            for index, (candidate_number, candidate_name, ble_name) in enumerate(devices, 1):
                print(f"{index}: Nummer {json.dumps(candidate_number, ensure_ascii=True)}, "
                      f"Anzeigename {json.dumps(candidate_name, ensure_ascii=True)}, "
                      f"BLE-Name {json.dumps(ble_name, ensure_ascii=True)}")
            selection = input("Nummer des zugehoerigen Cloud-BLE-Eintrags (Enter = abbrechen): ").strip()
            if not selection.isdecimal() or not 1 <= int(selection) <= len(devices):
                raise CloudError("Kein Cloud-Geraet ausgewaehlt; kein Command angefordert.")
            number, _, name = devices[int(selection) - 1]
        print("BLE-Antwort und Command werden angefordert.")
        if send_unlock:
            command = asyncio.run(probe(session, address, number, name, send_unlock=True))
        else:
            command = asyncio.run(probe(session, address, number, name))
    except getpass.GetPassWarning:
        print("Verdeckte Passworteingabe nicht verfuegbar; abgebrochen.", file=sys.stderr)
        return 1
    except (CloudError, BleakError, OSError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Experiment fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    if send_unlock:
        print("Bitte mechanisch pruefen, ob der Knauf entriegelt ist; das Skript kann dies nicht feststellen.")
        return 0
    print(f"Cloud lieferte einen Hex-Command mit {len(command)} Bytes. Kein Unlock-Write wurde gesendet.")
    print("Der Command ist sensibel; Terminalausgaben koennen protokolliert werden.")
    if input("Command nur lokal anzeigen? ANZEIGEN eingeben, sonst Enter: ").strip() == "ANZEIGEN":
        print(command.hex())
    print("Command und Token wurden nicht gespeichert. Die Gueltigkeit am Schloss ist nicht nachgewiesen.")
    return 0


def main() -> int:
    try:
        return run_interactive()
    except (EOFError, KeyboardInterrupt):
        print("\nAbgebrochen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
