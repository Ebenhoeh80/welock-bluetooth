"""Experimental WELOCK cloud-login probe; it does not unlock a lock."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import secrets
import sys
import time
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

BASE_URL = "https://clientapi.welock.com.cn/api"
LOGIN_PATH = "/Account/token/welock"
UNLOCK_PATH = "/Command/UnLock"
DEVICES_PATH = "/Device/GetDevices"
MAX_RESPONSE_BYTES = 1024 * 1024


class CloudError(Exception):
    """A cloud operation failed without exposing request or response secrets."""


class NoRedirect(HTTPRedirectHandler):
    """Prevent automated HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def request_signature(timestamp: str, device_id: str) -> str:
    encoded = base64.b64encode((device_id + timestamp)[::-1].encode("utf-8")).decode("ascii")
    return md5_hex(md5_hex(encoded))


def login_form(account: str, password: str, device_id: str, time_offset: int) -> dict[str, str]:
    return {
        "account": account.strip(),
        "password": password,
        "timeOffset": str(time_offset),
        "platform": "ios",
        "model": "iPhone",
        "language": "en",
        "Jpushid": md5_hex(account.strip() + "welockid-" + device_id),
        "isIot": "1",
    }


def request_headers(device_id: str, timestamp: str) -> dict[str, str]:
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dart/3.7 (dart:io)",
        "identifierForVendor": device_id,
        "isPhysicalDevice": "true",
        "deviceModel": "iPhone",
        "operatingSystem": "ios",
        "appVersion": "4.5.2",
        "requestClientTimestamp": timestamp,
        "nonce": "".join(str(secrets.randbelow(10)) for _ in range(12)),
        "sign": request_signature(timestamp, device_id),
    }


def parse_response(raw: bytes) -> object:
    try:
        envelope = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudError("Die Serverantwort ist kein gueltiges JSON.") from exc
    if not isinstance(envelope, dict) or type(envelope.get("code")) is not int:
        raise CloudError("Das Antwortformat enthaelt keinen gueltigen Statuscode.")
    if envelope["code"] != 0:
        raise CloudError(f"Die Cloud hat die Anfrage abgelehnt (Code {envelope['code']}).")
    if "data" not in envelope:
        raise CloudError("Die Serverantwort enthaelt kein Datenfeld.")
    return envelope["data"]


def post_form(path: str, form: dict[str, str], device_id: str, token: str | None = None) -> bytes:
    if path not in (LOGIN_PATH, UNLOCK_PATH, DEVICES_PATH):
        raise CloudError("Nicht erlaubter Cloud-Endpunkt.")
    headers = request_headers(device_id, str(time.time_ns() // 1_000_000))
    if token is not None:
        if not token or any(ord(c) < 32 or ord(c) > 126 for c in token):
            raise CloudError("Das access_token ist kein gueltiger HTTP-Headerwert.")
        headers["Authorization"] = token
    data_bytes = urlencode(form).encode("utf-8")
    request = Request(BASE_URL + path, data=data_bytes, headers=headers, method="POST")
    opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler())
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        msg = f"Die Cloud-Anfrage schlug fehl (HTTP {exc.code}); Weiterleitungen sind gesperrt."
        raise CloudError(msg) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise CloudError("Die Cloud-Anfrage scheiterte an Verbindung, TLS oder Zeitlimit.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise CloudError("Die Serverantwort ueberschreitet das Groessenlimit.")
    return raw


@dataclass
class CloudSession:
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()).upper())
    access_token: str | None = field(default=None, repr=False)
    login_data: dict[str, object] | None = field(default=None, repr=False)

    def authenticate(self, account: str, password: str) -> None:
        if not account.strip() or not password:
            raise CloudError("Konto und Passwort duerfen nicht leer sein.")
        offset = datetime.now().astimezone().utcoffset()
        if offset is None:
            raise CloudError("Die lokale Zeitzonenabweichung konnte nicht ermittelt werden.")
        self.access_token = None
        self.login_data = None
        form = login_form(account, password, self.device_id, int(offset.total_seconds()))
        raw_resp = post_form(LOGIN_PATH, form, self.device_id)
        data = parse_response(raw_resp)
        if not isinstance(data, dict):
            raise CloudError("Das Anmeldeergebnis hat ein unbekanntes Datenformat.")
        self.login_data = data
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise CloudError("Die erfolgreiche Antwort enthaelt kein access_token.")
        if any(ord(c) < 32 or ord(c) > 126 for c in token):
            raise CloudError("Das access_token ist kein gueltiger HTTP-Headerwert.")
        self.access_token = token

    def list_devices(self) -> list[tuple[str, str, str]]:
        if self.access_token is None:
            raise CloudError("Keine aktive Cloud-Anmeldung.")
        data = parse_response(
            post_form(
                DEVICES_PATH, {"pageSize": "40", "pageNo": "1"}, self.device_id, self.access_token
            )
        )
        if not isinstance(data, list):
            raise CloudError("Die Cloud-Geraeteliste hat ein unbekanntes Datenformat.")
        devices = []
        for item in data:
            if not isinstance(item, dict):
                raise CloudError("Die Cloud-Geraeteliste enthaelt einen ungueltigen Eintrag.")
            number, name = item.get("deviceNumber"), item.get("deviceName")
            invalid_num = not isinstance(number, str) or not number.strip()
            invalid_name = not isinstance(name, str) or not name.strip()
            if invalid_num or invalid_name:
                raise CloudError("Cloud-Geraet hat keine gueltige Nummer oder keinen Namen.")
            ble = item.get("ble")
            if ble is None:
                continue
            if not isinstance(ble, list):
                raise CloudError("Die BLE-Geraeteliste hat ein unbekanntes Datenformat.")
            for entry in ble:
                if not isinstance(entry, dict):
                    raise CloudError("Die BLE-Geraeteliste enthaelt einen ungueltigen Eintrag.")
                ble_name = entry.get("deviceName")
                if not isinstance(ble_name, str) or not ble_name.strip():
                    raise CloudError("Ein BLE-Eintrag hat keinen gueltigen Namen.")
                devices.append((number, name, ble_name))
        return devices

    def request_unlock_command(
        self, device_number: str, device_name: str, random_factor: int, battery: int
    ) -> bytes:
        if self.access_token is None:
            raise CloudError("Keine aktive Cloud-Anmeldung.")
        if not device_number.strip() or not device_name.strip():
            raise CloudError("Schlossnummer und Geraetename duerfen nicht leer sein.")
        if not 0 <= random_factor <= 255 or not 0 <= battery <= 255:
            raise CloudError("BLE-Antwortwerte liegen ausserhalb des Bytebereichs.")
        form = {
            "deviceNumber": device_number,
            "deviceName": device_name,
            "randomFactor": str(random_factor),
            "battery": str(battery),
        }
        data = parse_response(post_form(UNLOCK_PATH, form, self.device_id, self.access_token))
        if not isinstance(data, dict):
            raise CloudError("Das Command-Ergebnis hat ein unbekanntes Datenformat.")
        command = data.get("command")
        if not isinstance(command, str) or not command or len(command) % 2:
            raise CloudError("Das Command-Feld ist kein gueltiger Hex-String.")
        if any(c not in "0123456789abcdefABCDEF" for c in command):
            raise CloudError("Das Command-Feld enthaelt ungueltige Hex-Zeichen.")
        return bytes.fromhex(command)


def login(account: str, password: str) -> str:
    session = CloudSession()
    session.authenticate(account, password)
    assert session.access_token is not None
    return session.access_token


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WeLock Cloud-Login-Test und Abruf registrierter Schlösser."
    )
    parser.add_argument(
        "positional_account",
        nargs="?",
        default=None,
        help="WeLock-Konto / E-Mail-Adresse.",
    )
    parser.add_argument(
        "--account",
        "-u",
        type=str,
        default=None,
        help="WeLock-Konto / E-Mail-Adresse.",
    )
    parser.add_argument(
        "--list-devices",
        "-l",
        action="store_true",
        help="Registrierte Schlösser und BLE-Namen nach dem Login abrufen und auflisten.",
    )
    parser.add_argument(
        "--show-data",
        "-s",
        action="store_true",
        help="Vollständige Login-Antwortdaten (Data-Payload) im Terminal anzeigen.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Sicherheitsbestätigung automatisch akzeptieren.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ausgabe als JSON-Datenstruktur.",
    )

    args = parser.parse_args()
    account = args.account or args.positional_account

    if not args.json:
        print("Experimenteller Cloud-Login; kein Unlock und kein Speichern von Zugangsdaten.")
        print("Hinweis: Eine neue Anmeldung kann bestehende WeLock-Sitzungen in der App abmelden.")

    if not args.yes and not args.json:
        if input("Für diesen Login ausdrücklich JA eingeben: ").strip() != "JA":
            print("Abgebrochen; keine Anmeldung durchgeführt.")
            return 1

    if not account:
        account = input("WeLock-E-Mail: ").strip()

    if not account:
        print("Fehler: E-Mail-Adresse darf nicht leer sein.", file=sys.stderr)
        return 1

    session = CloudSession()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("WeLock-Passwort (verdeckte Eingabe): ")

        session.authenticate(account, password)
        del password
    except getpass.GetPassWarning:
        print("Fehler: Verdeckte Passworteingabe nicht verfügbar; abgebrochen.", file=sys.stderr)
        return 1
    except CloudError as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}))
        else:
            print(f"Anmeldung fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    devices_list = []
    if args.list_devices or not args.json:
        try:
            raw_devices = session.list_devices()
            for number, name, ble_name in raw_devices:
                devices_list.append(
                    {
                        "device_number": number,
                        "device_name": name,
                        "ble_name": ble_name,
                    }
                )
        except CloudError as exc:
            if not args.json:
                print(f"Hinweis beim Abruf der Geräteliste: {exc}")

    if args.json:
        print(
            json.dumps(
                {
                    "success": True,
                    "account": account,
                    "login_response_data": session.login_data,
                    "devices": devices_list,
                },
                indent=2,
            )
        )
        return 0

    print("\nCloud-Anmeldung erfolgreich akzeptiert!")

    if session.login_data and (args.show_data or not devices_list):
        print("\nLogin-Antwortdaten (Data-Objekt):")
        print("-" * 65)
        for key, value in session.login_data.items():
            print(f"  {key}: {value}")
        print("-" * 65)

    if devices_list:
        print(f"\nRegistrierte Schlösser ({len(devices_list)}):")
        print("-" * 65)
        for idx, dev in enumerate(devices_list, 1):
            num = dev["device_number"]
            dname = dev["device_name"]
            bname = dev["ble_name"]
            print(f"[{idx}] Schlossnummer: {num} | Name: {dname} | BLE: {bname}")
        print("-" * 65)

    print("Kein Token gespeichert und kein Unlock-Befehl gesendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
