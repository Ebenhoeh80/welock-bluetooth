"""Read-only Analyse des BLE-Kommunikationsschluessels (devicePassword).

Holt die Geraeteinfo aus der Cloud, extrahiert pro BLE-Modul das
``devicePassword`` (24 Zeichen) und analysiert dessen Kodierung (Hex/Base64/
ASCII), Laenge und Entropie. Standardmaessig wird der Schluessel maskiert; mit
``--save`` wird ein vollstaendiger Bericht NUR in den Git-ignorierten Ordner
``tools/offline-data`` geschrieben. Es wird nichts ans Schloss gesendet.

Hinweis: Jeder Cloud-Login meldet andere Sitzungen des Kontos ab (App, HA).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from welock_cloud_login import CloudError, CloudSession
    from welock_offline import analyze_key
    from welock_ui import confirm, mask, read_password
except ImportError:
    from tools.welock_cloud_login import CloudError, CloudSession
    from tools.welock_offline import analyze_key
    from tools.welock_ui import confirm, mask, read_password

OFFLINE_DIR = Path(__file__).resolve().parent / "offline-data"


def analyze_device(info: dict) -> list[dict]:
    """Analysiert das devicePassword jedes BLE-Moduls der Geraeteinfo."""
    modules = []
    for ble in info.get("ble", []) or []:
        if not isinstance(ble, dict):
            continue
        pwd = ble.get("devicePassword")
        entry = {
            "position": ble.get("position"),
            "ble_name": ble.get("deviceName"),
            "password": pwd,
            "analysis": analyze_key(pwd) if isinstance(pwd, str) and pwd else None,
        }
        modules.append(entry)
    return modules


def print_report(info: dict, modules: list[dict], *, show_pii: bool) -> None:
    show = (lambda v: str(v)) if show_pii else mask
    print("\n" + "=" * 72)
    print("  BLE-KOMMUNIKATIONSSCHLUESSEL-ANALYSE (read-only)")
    print("=" * 72)
    print(f"  Modell={info.get('model')} Schloss={info.get('deviceNumber')}")
    for m in modules:
        a = m["analysis"]
        print(f"\n  BLE pos={m['position']} name={m['ble_name']}")
        if not a:
            print("    kein devicePassword vorhanden")
            continue
        pwd = m["password"]
        print(f"    Schluessel: {show(pwd)}  (Laenge {a['length']})")
        cs = a["charset"]
        print(
            f"    Kodierung: hex={cs['all_hex']} base64={cs['all_base64']} "
            f"alnum={cs['all_alnum']} printable={cs['all_printable']}"
        )
        print(f"    Entropie:  {a['entropy_bits_per_char']} Bit/Zeichen")
        for interp in a["interpretations"]:
            print(f"    -> Deutung '{interp.name}': {interp.note}")
    print("\n  Hinweis: Dieser Schluessel ist ein moeglicher Baustein fuer einen")
    print("  lokalen Offline-Unlock. Siehe welock_offline_experiment.py.")


def save_report(info: dict, modules: list[dict]) -> Path:
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OFFLINE_DIR / f"keyinfo-{stamp}.json"
    payload = {
        "device_number": info.get("deviceNumber"),
        "model": info.get("model"),
        "modules": [
            {
                "position": m["position"],
                "ble_name": m["ble_name"],
                "password": m["password"],
                "analysis": (
                    {
                        **m["analysis"],
                        "interpretations": [
                            {"name": i.name, "hex": i.raw_bytes.hex(), "note": i.note}
                            for i in m["analysis"]["interpretations"]
                        ],
                    }
                    if m["analysis"]
                    else None
                ),
            }
            for m in modules
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Analyse des BLE-Kommunikationsschluessels."
    )
    parser.add_argument("--account", "-u", default=None, help="WeLock-Konto (E-Mail).")
    parser.add_argument("--number", "-n", default=None, help="Schlossnummer (deviceNumber).")
    parser.add_argument("--show-pii", action="store_true", help="Schluessel im Klartext anzeigen.")
    parser.add_argument(
        "--save", action="store_true", help="Vollbericht in tools/offline-data speichern."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Bestaetigung automatisch akzeptieren."
    )
    args = parser.parse_args(argv)

    print("Read-only Schluesselanalyse: kein Unlock, keine Mutation.")
    print("Hinweis: Eine Anmeldung kann bestehende WeLock-Sitzungen (App/HA) abmelden.")
    if not confirm("Fortfahren? JA eingeben: ", auto_yes=args.yes):
        print("Abgebrochen.")
        return 1

    account = args.account or input("WeLock-Konto (E-Mail): ").strip()
    if not account:
        print("Fehler: E-Mail darf nicht leer sein.", file=sys.stderr)
        return 1
    try:
        password = read_password(prompt="WeLock-Passwort (verdeckt; oder ENV WELOCK_PASSWORD): ")
    except RuntimeError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    session = CloudSession()
    try:
        session.authenticate(account, password)
        del password
        number = args.number
        if not number:
            devices = session.list_devices()
            numbers = sorted({num for num, _n, _b in devices})
            if len(numbers) == 1:
                number = numbers[0]
            else:
                print("Mehrere Schloesser; bitte --number angeben:", numbers, file=sys.stderr)
                return 1
        info = session.get_device_info(number)
    except CloudError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    modules = analyze_device(info)
    print_report(info, modules, show_pii=args.show_pii)
    if args.save:
        path = save_report(info, modules)
        print(f"\nVollbericht gespeichert: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
