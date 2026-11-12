"""Offline-Befehls-Oracle: vollstaendige Tabelle ``randomFactor -> command``.

Die differenzielle Analyse hat gezeigt, dass der Cloud-Unlock-Befehl eine
Funktion des einzelnen Challenge-Bytes ``randomFactor`` ist (``battery`` und
``devicePassword`` gehen nicht variabel ein). Es gibt daher nur 256 moegliche
Befehle pro Schloss. Dieses Werkzeug hat zwei Betriebsarten:

  * ``--harvest``   Fragt EINMALIG (nach ausdruecklicher Einwilligung) die
    Befehle fuer rf = 0..255 bei der Cloud an und speichert die Tabelle als
    JSON in ``tools/offline-data`` (git-ignoriert). Danach ist die
    Befehlserzeugung vollstaendig OFFLINE moeglich. Es wird KEIN Befehl an das
    Schloss geschrieben; die Anfragen werden serverseitig jedoch als
    Unlock-Command-Anfragen verarbeitet (und ggf. protokolliert).

  * ``--table PATH --rf N``   Erzeugt den Befehl fuer ein Challenge-Byte ``N``
    rein OFFLINE aus einer zuvor geernteten Tabelle. Zusaetzlich prueft
    ``--self-check`` Vollstaendigkeit und Formelkonsistenz der Tabelle.

WICHTIG: Dieses Werkzeug entriegelt nicht. Ein lokal erzeugter Befehl darf erst
nach ausdruecklicher Entscheidung, vor Ort, mit mechanischer Kontrolle und
>30 s Abstand zwischen Versuchen an das Schloss geschrieben werden. Eine
geraeteseitige Replay-/Zaehlersperre ist bisher nicht ausgeschlossen.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from welock_cloud_login import CloudError, CloudSession
    from welock_offline import (
        Sample,
        command_for_rf,
        rf_table_from_samples,
        verify_table_consistency,
    )
    from welock_ui import confirm, mask, read_password
except ImportError:
    from tools.welock_cloud_login import CloudError, CloudSession
    from tools.welock_offline import (
        Sample,
        command_for_rf,
        rf_table_from_samples,
        verify_table_consistency,
    )
    from tools.welock_ui import confirm, mask, read_password

OFFLINE_DIR = Path(__file__).resolve().parent / "offline-data"


def pick_module(info: dict) -> tuple[str, str | None]:
    """Waehlt das aktive BLE-Modul mit dem hoechsten Ladestand: (name, key)."""
    modules = [m for m in (info.get("ble") or []) if isinstance(m, dict) and m.get("deviceName")]
    if not modules:
        raise CloudError("Keine BLE-Module in der Geraeteinfo.")
    modules.sort(key=lambda m: (m.get("power") or 0), reverse=True)
    return modules[0]["deviceName"], modules[0].get("devicePassword")


def harvest_table(
    session: CloudSession,
    number: str,
    ble_name: str,
    rf_values: list[int],
    *,
    battery: int,
    delay: float,
    stop_after_errors: int = 8,
) -> dict[int, str]:
    """Erntet rf -> command fuer die angegebenen rf-Werte. KEIN BLE-Write.

    Bricht nach ``stop_after_errors`` aufeinanderfolgenden Ablehnungen ab
    (typisch: serverseitige Ratenbegrenzung), um die Sitzung nicht weiter zu
    belasten; die bis dahin erfassten Eintraege werden zurueckgegeben.
    """
    samples: list[Sample] = []
    total = len(rf_values)
    consecutive_errors = 0
    for idx, rf in enumerate(rf_values, 1):
        try:
            command = session.request_unlock_command(number, ble_name, rf, battery)
            samples.append(Sample(random_factor=rf, battery=battery, command=command))
            consecutive_errors = 0
        except CloudError as exc:
            consecutive_errors += 1
            print(f"  rf={rf:<3} abgelehnt: {exc}", file=sys.stderr)
            if consecutive_errors >= stop_after_errors:
                print(
                    f"  Abbruch nach {consecutive_errors} Ablehnungen in Folge "
                    f"(vermutlich Ratenbegrenzung). {len(samples)} Befehle erfasst.",
                    file=sys.stderr,
                )
                break
        if idx % 32 == 0 or idx == total:
            print(f"  {idx}/{total} angefragt (zuletzt rf={rf})")
        if idx < total:
            time.sleep(delay)
    return rf_table_from_samples(samples)


def save_table(table: dict[int, str], number: str, battery: int) -> Path:
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
    path = OFFLINE_DIR / f"oracle-table-{number}-{datetime.now():%Y%m%d-%H%M%S}.json"
    payload = {
        "device_number": number,
        "battery_used": battery,
        "note": "command haengt nur von randomFactor ab; battery ist irrelevant.",
        "table": {str(rf): cmd for rf, cmd in sorted(table.items())},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_table(path: Path) -> dict[int, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("table", data)  # erlaubt auch eine blanke {rf: cmd}-Map
    return {int(k): str(v) for k, v in raw.items()}


def print_consistency(table: dict[int, str]) -> None:
    chk = verify_table_consistency(table)
    print(f"  Eintraege: {chk['count']}/256  vollstaendig={chk['complete']}")
    if chk["missing"]:
        head = chk["missing"][:12]
        more = "" if len(chk["missing"]) <= 12 else f" (+{len(chk['missing']) - 12} weitere)"
        print(f"  Fehlende rf: {head}{more}")
    fit = chk["fit"]
    if fit.get("analyzable"):
        if fit["fully_closed_form"]:
            print(
                "  Formelkonsistenz: pos0-11 geschlossen, pos12 (Pruefziffer) via Tabelle abgedeckt."
            )
        else:
            print(
                f"  Formelkonsistenz: Positionen {fit['residual_positions']} nicht multiplikativ "
                f"(erwartet: nur pos12)."
            )
    else:
        print(f"  Formelpruefung nicht moeglich: {fit.get('reason')}")


def run_harvest(args: argparse.Namespace) -> int:
    rf_start, rf_end = args.rf_start, args.rf_end
    if not (0 <= rf_start <= rf_end <= 255):
        print("Fehler: 0 <= --rf-start <= --rf-end <= 255 erforderlich.", file=sys.stderr)
        return 1

    existing: dict[int, str] = {}
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.is_absolute() and not resume_path.exists():
            resume_path = OFFLINE_DIR / args.resume
        if not resume_path.exists():
            print(f"Fehler: --resume-Tabelle nicht gefunden: {resume_path}", file=sys.stderr)
            return 1
        existing = load_table(resume_path)
        rf_values = [rf for rf in range(rf_start, rf_end + 1) if rf not in existing]
        print(
            f"Resume aus {resume_path.name}: {len(existing)} vorhanden, {len(rf_values)} fehlen noch."
        )
    else:
        rf_values = list(range(rf_start, rf_end + 1))
    count = len(rf_values)
    if count == 0:
        print("Nichts zu ernten; Tabelle bereits vollstaendig fuer den Bereich.")
        return 0

    print("=" * 72)
    print(f"  OFFLINE-ORACLE: erntet {count} Cloud-Befehle.")
    print("  Es wird NICHTS ans Schloss geschrieben (kein Unlock).")
    print("  Jede Anfrage wird serverseitig als Unlock-Command-Anfrage verarbeitet.")
    print("=" * 72)
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
            numbers = sorted({num for num, _n, _b in session.list_devices()})
            if len(numbers) != 1:
                print("Mehrere/keine Schloesser; bitte --number angeben:", numbers, file=sys.stderr)
                return 1
            number = numbers[0]
        info = session.get_device_info(number)
        ble_name, device_password = pick_module(info)
        print(
            f"\nSchloss {number}, BLE-Modul {ble_name}, "
            f"Schluessel {mask(device_password)} (fuer den Befehl irrelevant)"
        )
        print(f"Starte Ernte von {count} Befehlen (Pause {args.delay}s, kein BLE-Write)...")
        harvested = harvest_table(
            session,
            number,
            ble_name,
            rf_values,
            battery=args.battery,
            delay=args.delay,
        )
        table = {**existing, **harvested}
    except CloudError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1

    if not harvested and not existing:
        print("Keine Befehle erhalten; Tabelle leer.", file=sys.stderr)
        return 1

    print("\n" + "=" * 72)
    print("  ERNTE ABGESCHLOSSEN")
    print("=" * 72)
    print_consistency(table)
    path = save_table(table, number, args.battery)
    print(f"\nTabelle gespeichert: {path}")
    print("Ab jetzt ist die Befehlserzeugung offline moeglich:")
    print(f'  python tools/welock_offline_oracle.py --table "{path.name}" --rf <0..255>')
    return 0


def run_offline(args: argparse.Namespace) -> int:
    path = Path(args.table)
    if not path.is_absolute() and not path.exists():
        path = OFFLINE_DIR / args.table
    if not path.exists():
        print(f"Fehler: Tabelle nicht gefunden: {path}", file=sys.stderr)
        return 1
    try:
        table = load_table(path)
    except (ValueError, OSError) as exc:
        print(f"Fehler beim Laden der Tabelle: {exc}", file=sys.stderr)
        return 1

    if args.self_check:
        print(f"Selbstpruefung der Tabelle {path.name} (offline):")
        print_consistency(table)

    if args.rf is not None:
        if not 0 <= args.rf <= 255:
            print("Fehler: --rf muss in 0..255 liegen.", file=sys.stderr)
            return 1
        command = command_for_rf(table, args.rf)
        if command is None:
            print(f"Fehler: kein Eintrag fuer rf={args.rf} in der Tabelle.", file=sys.stderr)
            return 1
        hex_command = command.encode("ascii", "replace").hex()
        print(f"\nOffline-Befehl fuer rf={args.rf}:")
        print(f"  ASCII: {command}")
        print(f"  Hex  : {hex_command}")
        print("\nHinweis: NICHT automatisch senden. Nur vor Ort, mit mechanischer")
        print("Kontrolle und >30 s Abstand, darf ein Schreibversuch erfolgen.")
    elif not args.self_check:
        print("Nichts zu tun: --rf N und/oder --self-check angeben.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline-Befehls-Oracle: Tabelle randomFactor -> command (ernten/nutzen)."
    )
    parser.add_argument(
        "--harvest",
        action="store_true",
        help="256 Cloud-Befehle ernten und als Tabelle speichern (Online).",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Vorhandene Tabelle laden und nur noch fehlende rf ernten (mit --harvest).",
    )
    parser.add_argument(
        "--table", default=None, help="Pfad/Name einer geernteten Tabelle (Offline-Nutzung)."
    )
    parser.add_argument(
        "--rf", type=int, default=None, help="Challenge-Byte 0..255 fuer Offline-Erzeugung."
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Tabelle offline auf Vollstaendigkeit/Formel pruefen.",
    )
    parser.add_argument(
        "--account", "-u", default=None, help="WeLock-Konto (E-Mail), nur bei --harvest."
    )
    parser.add_argument(
        "--number", "-n", default=None, help="Schlossnummer (deviceNumber), nur bei --harvest."
    )
    parser.add_argument("--rf-start", type=int, default=0, help="Erstes rf der Ernte (Standard 0).")
    parser.add_argument(
        "--rf-end", type=int, default=255, help="Letztes rf der Ernte (Standard 255)."
    )
    parser.add_argument(
        "--battery",
        type=int,
        default=100,
        help="battery-Wert der Anfrage (irrelevant; Standard 100).",
    )
    parser.add_argument("--delay", type=float, default=0.8, help="Pause zwischen Anfragen (s).")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Bestaetigungen automatisch akzeptieren."
    )
    args = parser.parse_args(argv)

    if not 0 <= args.battery <= 255:
        parser.error("--battery muss in 0..255 liegen.")

    if args.harvest:
        return run_harvest(args)
    if args.table:
        return run_offline(args)
    parser.error("Entweder --harvest (Online-Ernte) oder --table (Offline-Nutzung) angeben.")


if __name__ == "__main__":
    raise SystemExit(main())
