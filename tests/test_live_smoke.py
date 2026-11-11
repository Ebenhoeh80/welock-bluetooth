"""Optional live smoke test against the real WELOCK cloud and the HA Bluetooth cache.

Read-only: cloud login, lock list and reading the Home Assistant Bluetooth cache file.
No unlock call and no BLE write path is used; both are blocked actively during the test.

Opt-in (current shell session only, never in CI):
    WELOCK_LIVE_TEST=1      enables the test
    WELOCK_USER             WELOCK account (not secret)
    WELOCK_PASSWORD         WELOCK password (secret, never printed)
    WELOCK_LOCK_ID          optional: expected lock id / deviceNumber
    WELOCK_HA_BT_CACHE      optional: path to the HA Bluetooth cache, e.g.
                            <ha-config>/.storage/bluetooth.remote_scanners (file or .storage dir)

Run:  pytest -m live -s
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.live

SECRET_KEY_PATTERN = re.compile(r"token|secret|passw|pwd|key|sign|auth|session|cookie", re.I)
MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
REDACTED = "[entfernt]"


class _Secrets:
    """Holds every value that must never reach the output."""

    def __init__(self) -> None:
        self.values: list[str] = []

    def add(self, value: object) -> None:
        if isinstance(value, str) and value:
            self.values.append(value)

    def scrub(self, text: str) -> str:
        for value in self.values:
            text = text.replace(value, REDACTED)
        return text

    def contains(self, text: str) -> bool:
        return any(value in text for value in self.values)


def _normalize_mac(value: str) -> str | None:
    hex_only = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(hex_only) == 12 and (MAC_PATTERN.fullmatch(value) or len(value) == 12):
        return hex_only.upper()
    return None


def _flatten(obj: Any, path: str = "") -> list[tuple[str, Any]]:
    """Return (path, leaf value) pairs for a nested JSON structure."""
    if isinstance(obj, dict):
        if not obj:
            return [(path or "<root>", obj)]
        out: list[tuple[str, Any]] = []
        for key, value in obj.items():
            out.extend(_flatten(value, f"{path}.{key}" if path else str(key)))
        return out
    if isinstance(obj, list):
        if not obj:
            return [(path or "<root>", obj)]
        out = []
        for idx, value in enumerate(obj):
            out.extend(_flatten(value, f"{path}[{idx}]"))
        return out
    return [(path or "<root>", obj)]


def _safe_value(path: str, value: Any, secrets: _Secrets) -> str:
    last_key = re.split(r"[.\[]", path)[-1]
    if SECRET_KEY_PATTERN.search(last_key):
        return "<nicht ausgegeben: Feldname deutet auf Geheimnis>"
    text = json.dumps(value, ensure_ascii=False)
    if secrets.contains(text):
        return "<nicht ausgegeben: enthaelt Geheimnis>"
    return text


def _collect_cloud_identifiers(devices: Any) -> tuple[set[str], set[str], set[str]]:
    """Return (macs, ble_names, id-like values) from the raw cloud device list."""
    macs: set[str] = set()
    names: set[str] = set()
    ids: set[str] = set()
    for path, value in _flatten(devices):
        if not isinstance(value, (str, int)):
            continue
        key = re.split(r"[.\[]", path)[-1].lower()
        text = str(value)
        if "mac" in key or "address" in key or MAC_PATTERN.search(text):
            mac = _normalize_mac(text)
            if mac:
                macs.add(mac)
        if key == "devicename" and ".ble[" in path:
            names.add(text)
        if key in {"devicenumber", "lockid", "id", "locksn", "deviceid", "sn"}:
            ids.add(text)
    return macs, names, ids


def _read_ha_bt_cache(path_str: str) -> tuple[list[Path], set[str], set[str]]:
    """Read HA Bluetooth cache file(s) read-only; return (files, macs, names)."""
    path = Path(path_str).expanduser()
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.is_file() and p.name.startswith("bluetooth"))
    else:
        files = [path]
    if not files or not all(f.is_file() for f in files):
        raise FileNotFoundError(f"Kein HA-Bluetooth-Cache unter {path} gefunden.")
    macs: set[str] = set()
    names: set[str] = set()
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        for leaf_path, value in _flatten(data):
            for part in re.split(r"[.\[\]]", leaf_path):
                mac = _normalize_mac(part) if MAC_PATTERN.fullmatch(part) else None
                if mac:
                    macs.add(mac)
            if isinstance(value, str):
                for match in MAC_PATTERN.findall(value):
                    macs.add(_normalize_mac(match) or match)
                if leaf_path.lower().endswith(("name", "local_name")):
                    names.add(value)
    return files, macs, names


def test_live_cloud_and_ha_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    user = os.environ.get("WELOCK_USER", "").strip()
    password = os.environ.get("WELOCK_PASSWORD", "")
    if not user or not password:
        pytest.skip("WELOCK_USER und/oder WELOCK_PASSWORD fehlen in der Umgebung.")

    from tools import welock_cloud_login as wcl

    secrets = _Secrets()
    secrets.add(password)
    del password  # only kept inside `secrets` from here on

    # Hard guards: no unlock, no BLE write path - not even indirectly.
    original_post_form = wcl.post_form

    def guarded_post_form(path: str, *args: Any, **kwargs: Any) -> bytes:
        if path not in (wcl.LOGIN_PATH, wcl.DEVICES_PATH):
            raise AssertionError(f"Nicht erlaubter Endpunkt im Live-Test: {path}")
        return original_post_form(path, *args, **kwargs)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Unlock-/Schreibpfad im Live-Test aufgerufen.")

    monkeypatch.setattr(wcl, "post_form", guarded_post_form)
    monkeypatch.setattr(wcl.CloudSession, "request_unlock_command", forbidden)
    try:
        import bleak

        monkeypatch.setattr(bleak.BleakClient, "write_gatt_char", forbidden, raising=False)
        monkeypatch.setattr(bleak.BleakClient, "connect", forbidden, raising=False)
    except ImportError:
        pass

    results: list[tuple[str, str]] = []
    errors: list[str] = []

    def out(line: str = "") -> None:
        print(secrets.scrub(line))

    def record_error(step: str, exc: Exception) -> None:
        # Never print the original exception text or traceback; scrub first.
        errors.append(f"{step}: {type(exc).__name__}: {secrets.scrub(str(exc))}")
        results.append((step, "FEHLER"))

    out("\n=== WELOCK Live-Smoke-Test (read-only) ===")
    out(f"Konto: {user}")

    # Step 1: login
    session = wcl.CloudSession()
    try:
        form = wcl.login_form(user, secrets.values[0], session.device_id, _utc_offset_seconds())
        login_data = wcl.parse_response(wcl.post_form(wcl.LOGIN_PATH, form, session.device_id))
        del form
        if not isinstance(login_data, dict):
            raise wcl.CloudError("Login-Antwort hat ein unbekanntes Datenformat.")
        for value in login_data.values():
            if isinstance(value, str) and len(value) >= 16:
                secrets.add(value)  # refresh tokens etc. count as secret too
        token = login_data.get("access_token")
        if not isinstance(token, str) or not token:
            raise wcl.CloudError("Login-Antwort enthaelt kein access_token.")
        secrets.add(token)
        session.access_token = token
        del token
        results.append(("Login", "OK"))
        out("Login: OK (Token erhalten: ja)")
        out("Login-Antwort, nur Feldnamen und Typen:")
        for key, value in login_data.items():
            out(f"  {key}: {type(value).__name__}")
        del login_data
    except Exception as exc:  # noqa: BLE001 - must not leak any text
        record_error("Login", exc)
        out("Login: FEHLER (Token erhalten: nein)")

    # Step 2: lock list (raw, to see every field the cloud delivers)
    devices: Any = None
    if session.access_token:
        try:
            devices = wcl.parse_response(
                wcl.post_form(
                    wcl.DEVICES_PATH,
                    {"pageSize": "40", "pageNo": "1"},
                    session.device_id,
                    session.access_token,
                )
            )
            if not isinstance(devices, list):
                raise wcl.CloudError("Schlossliste ist keine Liste.")
            results.append(("Schlossliste", f"OK ({len(devices)} Eintraege)"))
            out(f"\nSchlossliste: OK ({len(devices)} Eintraege)")
            out("Felder (Pfad | Typ | Wert):")
            for path, value in _flatten(devices):
                out(f"  {path} | {type(value).__name__} | {_safe_value(path, value, secrets)}")
            # Also run the tool's own parser to verify api compatibility.
            parsed = session.list_devices()
            out(f"list_devices() des Tools: {len(parsed)} BLE-Eintraege erkannt")
        except Exception as exc:  # noqa: BLE001
            record_error("Schlossliste", exc)
    else:
        results.append(("Schlossliste", "UEBERSPRUNGEN (kein Login)"))

    cloud_macs, cloud_names, cloud_ids = (
        _collect_cloud_identifiers(devices) if devices else (set(), set(), set())
    )

    # Step 3: optional expected lock id
    expected_id = os.environ.get("WELOCK_LOCK_ID", "").strip()
    if expected_id and devices is not None:
        status = "OK" if expected_id in cloud_ids else "NICHT GEFUNDEN"
        results.append(("WELOCK_LOCK_ID in Schlossliste", status))
    elif expected_id:
        results.append(("WELOCK_LOCK_ID in Schlossliste", "UEBERSPRUNGEN (keine Liste)"))

    # Step 4: HA Bluetooth cache (read-only)
    cache_path = os.environ.get("WELOCK_HA_BT_CACHE", "").strip()
    if cache_path:
        try:
            files, cache_macs, cache_names = _read_ha_bt_cache(cache_path)
            out(f"\nHA-Bluetooth-Cache: {', '.join(str(f) for f in files)}")
            out(f"  Adressen im Cache: {len(cache_macs)}")
            mac_hits = sorted(cloud_macs & cache_macs)
            name_hits = sorted(cloud_names & cache_names)
            out(f"  Cloud-Adressen im Cache: {mac_hits or 'keine'}")
            out(f"  Cloud-BLE-Namen im Cache: {name_hits or 'keine'}")
            hit = bool(mac_hits or name_hits)
            results.append(
                (
                    "HA-Bluetooth-Cache",
                    "OK, Schloss gefunden" if hit else "gelesen, Schloss nicht gefunden",
                )
            )
        except Exception as exc:  # noqa: BLE001
            record_error("HA-Bluetooth-Cache", exc)
    else:
        results.append(("HA-Bluetooth-Cache", "UEBERSPRUNGEN (WELOCK_HA_BT_CACHE nicht gesetzt)"))

    out("\n=== Ergebnis ===")
    for step, status in results:
        out(f"  {step}: {status}")
    if errors:
        out("Exceptions:")
        for line in errors:
            out(f"  {line}")
    out("Kein Unlock-Befehl gesendet, kein BLE-Schreibzugriff, nichts gespeichert.")

    if errors:
        # pytrace=False: no traceback, so no local variables or request data are shown.
        pytest.fail(secrets.scrub("; ".join(errors)), pytrace=False)


def _utc_offset_seconds() -> int:
    from datetime import datetime

    offset = datetime.now().astimezone().utcoffset()
    return int(offset.total_seconds()) if offset else 0
