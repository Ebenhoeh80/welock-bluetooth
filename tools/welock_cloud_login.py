"""Experimental WELOCK cloud-login probe; it does not unlock a lock."""

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
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


BASE_URL = "https://clientapi.welock.com.cn/api"
LOGIN_PATH = "/Account/token/welock"
UNLOCK_PATH = "/Command/UnLock"
DEVICES_PATH = "/Device/GetDevices"
MAX_RESPONSE_BYTES = 1024 * 1024


class CloudError(Exception):
    """A cloud operation failed without exposing request or response secrets."""


class NoRedirect(HTTPRedirectHandler):
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


def parse_login_response(raw: bytes) -> str:
    data = parse_response(raw)
    if not isinstance(data, dict):
        raise CloudError("Das Anmeldeergebnis hat ein unbekanntes Datenformat.")
    token = data.get("access_token")
    if not isinstance(token, str) or not token:
        raise CloudError("Die erfolgreiche Antwort enthaelt kein access_token.")
    if any(ord(c) < 32 or ord(c) > 126 for c in token):
        raise CloudError("Das access_token ist kein gueltiger HTTP-Headerwert.")
    return token


def post_form(path: str, form: dict[str, str], device_id: str, token: str | None = None) -> bytes:
    if path not in (LOGIN_PATH, UNLOCK_PATH, DEVICES_PATH):
        raise CloudError("Nicht erlaubter Cloud-Endpunkt.")
    headers = request_headers(device_id, str(time.time_ns() // 1_000_000))
    if token is not None:
        if not token or any(ord(c) < 32 or ord(c) > 126 for c in token):
            raise CloudError("Das access_token ist kein gueltiger HTTP-Headerwert.")
        headers["Authorization"] = token
    request = Request(BASE_URL + path, data=urlencode(form).encode("utf-8"), headers=headers, method="POST")
    opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler())
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise CloudError(f"Die Cloud-Anfrage schlug fehl (HTTP {exc.code}); Weiterleitungen sind gesperrt.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise CloudError("Die Cloud-Anfrage scheiterte an Verbindung, TLS oder Zeitlimit.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise CloudError("Die Serverantwort ueberschreitet das Groessenlimit.")
    return raw


@dataclass
class CloudSession:
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()).upper())
    access_token: str | None = field(default=None, repr=False)

    def authenticate(self, account: str, password: str) -> None:
        if not account.strip() or not password:
            raise CloudError("Konto und Passwort duerfen nicht leer sein.")
        offset = datetime.now().astimezone().utcoffset()
        if offset is None:
            raise CloudError("Die lokale Zeitzonenabweichung konnte nicht ermittelt werden.")
        self.access_token = None
        form = login_form(account, password, self.device_id, int(offset.total_seconds()))
        self.access_token = parse_login_response(post_form(LOGIN_PATH, form, self.device_id))

    def list_devices(self) -> list[tuple[str, str, str]]:
        if self.access_token is None:
            raise CloudError("Keine aktive Cloud-Anmeldung.")
        data = parse_response(post_form(
            DEVICES_PATH, {"pageSize": "40", "pageNo": "1"}, self.device_id, self.access_token
        ))
        if not isinstance(data, list):
            raise CloudError("Die Cloud-Geraeteliste hat ein unbekanntes Datenformat.")
        devices = []
        for item in data:
            if not isinstance(item, dict):
                raise CloudError("Die Cloud-Geraeteliste enthaelt einen ungueltigen Eintrag.")
            number, name = item.get("deviceNumber"), item.get("deviceName")
            if not isinstance(number, str) or not number.strip() or not isinstance(name, str) or not name.strip():
                raise CloudError("Ein Cloud-Geraet hat keine gueltige Nummer oder keinen gueltigen Namen.")
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

    def request_unlock_command(self, device_number: str, device_name: str, random_factor: int, battery: int) -> bytes:
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
    print("Experimenteller Cloud-Login; kein Unlock und kein Speichern von Zugangsdaten.")
    print("Eine neue Anmeldung kann andere WELOCK-Sitzungen, einschliesslich der App, abmelden.")
    if input("Fuer diesen Login ausdruecklich JA eingeben: ").strip() != "JA":
        print("Abgebrochen; keine Anmeldung durchgefuehrt.")
        return 1
    account = input("WELOCK-E-Mail: ").strip()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("WELOCK-Passwort (verdeckte Eingabe): ")
        token = login(account, password)
        del password, token
    except getpass.GetPassWarning:
        print("Verdeckte Passworteingabe nicht verfuegbar; abgebrochen.", file=sys.stderr)
        return 1
    except CloudError as exc:
        print(f"Anmeldung fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    print("Cloud-Anmeldung akzeptiert. Kein Token gespeichert und kein Unlock durchgefuehrt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
