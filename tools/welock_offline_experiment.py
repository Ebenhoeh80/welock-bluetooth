"""Offline-Unlock-Forschung: ist der Cloud-command lokal reproduzierbar?

Fragt (nach ausdruecklicher Einwilligung) eine KLEINE, kontrollierte Menge von
Cloud-Unlock-Befehlen fuer verschiedene (randomFactor, battery)-Eingaben an und
untersucht sie lokal:

  1. Determinismus: Liefern gleiche Eingaben denselben Befehl? (sonst Server-
     Nonce/Zeit -> Offline-Reproduktion unwahrscheinlich)
  2. Struktur: Welche der 13 Befehlspositionen aendern sich mit rf bzw. battery?
  3. Hypothesen: Laesst sich der Befehl lokal aus dem devicePassword und den
     Eingaben nachbilden (MD5/SHA/HMAC-Varianten)?

WICHTIG: Es wird KEIN Befehl an das Schloss geschrieben; dieses Werkzeug
entriegelt nicht. Die angefragten Cloud-Befehle werden serverseitig jedoch als
Unlock-Command-Anfragen verarbeitet (und ggf. protokolliert). Deshalb bleibt
die Stichprobe klein und ausdruecklich bestaetigt. Vollstaendige Rohdaten
(echte Befehle) landen nur im Git-ignorierten Ordner tools/offline-data.
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
        analyze_key,
        determinism_verdict,
        differential_analysis,
        differential_sweep,
        evaluate_hypotheses,
        position_sensitivity,
    )
    from welock_ui import confirm, mask, read_password
except ImportError:
    from tools.welock_cloud_login import CloudError, CloudSession
    from tools.welock_offline import (
        Sample,
        analyze_key,
        determinism_verdict,
        differential_analysis,
        differential_sweep,
        evaluate_hypotheses,
        position_sensitivity,
    )
    from tools.welock_ui import confirm, mask, read_password

OFFLINE_DIR = Path(__file__).resolve().parent / "offline-data"

# Kleine, feste Stichprobe (mit einer Wiederholung fuer den Determinismustest).
DEFAULT_SWEEP: list[tuple[int, int]] = [
    (7, 100),
    (7, 100),  # Wiederholung -> Determinismus
    (0, 100),
    (1, 100),
    (2, 100),
    (255, 100),  # rf variiert
    (7, 0),
    (7, 50),  # battery variiert
]


def pick_module(info: dict) -> tuple[str, str | None]:
    """Waehlt das aktive BLE-Modul: (ble_name, devicePassword)."""
    modules = [m for m in (info.get("ble") or []) if isinstance(m, dict) and m.get("deviceName")]
    if not modules:
        raise CloudError("Keine BLE-Module in der Geraeteinfo.")
    modules.sort(key=lambda m: (m.get("power") or 0), reverse=True)
    chosen = modules[0]
    return chosen["deviceName"], chosen.get("devicePassword")


def collect_samples(
    session: CloudSession, number: str, ble_name: str, sweep: list[tuple[int, int]], delay: float
) -> list[Sample]:
    samples: list[Sample] = []
    for idx, (rf, bat) in enumerate(sweep, 1):
        try:
            command = session.request_unlock_command(number, ble_name, rf, bat)
            samples.append(Sample(random_factor=rf, battery=bat, command=command))
            print(
                f"  [{idx}/{len(sweep)}] rf={rf:<3} bat={bat:<3} -> command {len(command)} Byte OK"
            )
        except CloudError as exc:
            print(f"  [{idx}/{len(sweep)}] rf={rf:<3} bat={bat:<3} -> abgelehnt: {exc}")
        if idx < len(sweep):
            time.sleep(delay)
    return samples


def build_report(
    number: str,
    device_password: str | None,
    samples: list[Sample],
    *,
    baseline: tuple[int, int] | None = None,
) -> dict:
    det = determinism_verdict(samples)
    pos = position_sensitivity(samples)
    hyp = evaluate_hypotheses(device_password, number, samples) if device_password else []
    report = {
        "device_number": number,
        "mode": "differential" if baseline else "sweep",
        "samples": [
            {
                "random_factor": s.random_factor,
                "battery": s.battery,
                "command": s.command.decode("ascii", "replace"),
            }
            for s in samples
        ],
        "determinism": det,
        "position_sensitivity": pos,
        "key_analysis": (
            {
                "length": analyze_key(device_password)["length"],
                "charset": analyze_key(device_password)["charset"],
            }
            if device_password
            else None
        ),
        "hypotheses": [{"name": h.name, "matched": h.matched, "detail": h.detail} for h in hyp],
    }
    if baseline is not None:
        report["differential"] = differential_analysis(samples, baseline)
    return report


def print_summary(report: dict) -> None:
    det = report["determinism"]
    pos = report["position_sensitivity"]
    print("\n" + "=" * 72)
    print("  OFFLINE-REPRODUZIERBARKEIT (Auswertung)")
    print("=" * 72)
    print(f"  Samples: {len(report['samples'])}  distinct Inputs: {det['distinct_inputs']}")
    print(
        f"  Determinismus (gleiche Eingabe -> gleicher Befehl): {det['deterministic_for_tested_inputs']}"
        f"  (Wiederholung getestet: {det['tested_a_repeat']})"
    )
    if pos.get("analyzable"):
        print(f"  Variable Positionen (0-12): {pos['varying_positions']}")
        print(f"  Konstante Positionen:       {pos['constant_positions']}")
    matched = [h for h in report["hypotheses"] if h["matched"]]
    if matched:
        print("  LOKALE HYPOTHESE TRIFFT:")
        for h in matched:
            print(f"    * {h['name']}: {h['detail']}")
        print("  -> Offline-Reproduktion plausibel; naechster Schritt: verifizieren.")
    else:
        print("  Keine der getesteten lokalen Hypothesen reproduziert den Befehl.")
        if not det["deterministic_for_tested_inputs"] and det["tested_a_repeat"]:
            print("  -> Befehl ist nicht deterministisch: Offline-Reproduktion unwahrscheinlich")
            print("     (serverseitige Nonce/Zeit/Zustand wahrscheinlich beteiligt).")
        else:
            print("  -> Determinismus moeglich, aber Algorithmus unbekannt: weitere RE noetig")
            print("     (z. B. 3DES/AES mit unbekanntem Klartext-Layout, Serverschluessel).")


def print_differential(report: dict) -> None:
    diff = report.get("differential")
    if not diff:
        return
    print("\n" + "=" * 72)
    print("  DIFFERENZIELLE ANALYSE (Einzelbit-Variation der Eingaben)")
    print("=" * 72)
    if not diff.get("analyzable"):
        print(f"  Nicht auswertbar: {diff.get('reason')}")
        return
    base = diff["baseline"]
    print(
        f"  Baseline rf={base['random_factor']} battery={base['battery']} "
        f"(deterministisch: {diff['baseline_deterministic']}), "
        f"{diff['n_variations']} Variationen"
    )
    print(f"  Positionen (0-12), die auf randomFactor reagieren: {diff['random_factor_positions']}")
    print(f"  Positionen (0-12), die auf battery reagieren:      {diff['battery_positions']}")
    print(
        f"  Strukturell konstante Positionen:                  {diff['structurally_constant_positions']}"
    )
    enc0 = diff.get("rf_encoding") or {}
    mostly_closed = enc0.get("analyzable") and len(enc0.get("explained_positions", [])) >= 10
    dv = diff["diffusion"]
    if dv.get("classifiable"):
        print(
            f"\n  Bit-Heuristik: {dv['verdict'].upper()} "
            f"(im Mittel {dv['mean_changed_positions']}/{dv['mean_changed_positions_of']} "
            f"Zeichen pro Eingabebit)"
        )
        if mostly_closed:
            print(
                "  -> ABER: die geschlossene Form (unten) erklaert die Positionen als "
                "Multiplikation (rf*k); die scheinbare 'Diffusion' ist nur Bit-Streuung "
                "durch Multiplikation, KEINE echte Blockchiffre."
            )
        else:
            print(f"  -> {dv['interpretation']}")
    else:
        print(f"\n  Diffusion nicht klassifizierbar: {dv.get('reason')}")
    enc = diff.get("rf_encoding") or {}
    if enc.get("analyzable"):
        print("\n  Geschlossene Form je Position (Base64-Ziffer als Funktion von rf):")
        for pos in range(13):
            m = enc["models"][pos]
            if m["kind"] == "const":
                desc = f"konstant = {m['value']}"
            elif m["kind"] == "mul":
                desc = f"(rf*{m['coeff']}) >> 2 & 63"
            else:
                desc = "RESIDUAL (nicht multiplikativ; vermutlich Pruefziffer)"
            print(f"    pos{pos:<2} {desc}")
        if enc["fully_closed_form"]:
            print(
                "  -> ALLE Positionen geschlossen: Befehl ist OHNE Cloud allein aus rf berechenbar."
            )
        else:
            print(
                f"  -> Positionen {enc['residual_positions']} ungeklaert; Rest ist aus rf berechenbar."
            )
            print(
                "     (Exakter Offline-Generator dennoch via 256-Eintrag-Tabelle rf->command moeglich.)"
            )
    print("\n  Wirkung je Variation (Feld/Bit -> geaenderte Positionen):")
    for v in diff["per_variation"]:
        bit = f"bit{v['bit']}" if v["bit"] is not None else "multi"
        print(
            f"    {v['field']:<13} {bit:<6} wert={v['value']:<3} "
            f"-> {v['changed_count']:>2} Zeichen {v['changed_positions']}"
        )


def save_report(report: dict) -> Path:
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
    path = OFFLINE_DIR / f"experiment-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline-Unlock-Forschung: Determinismus & lokale Reproduktion des Cloud-command."
    )
    parser.add_argument("--account", "-u", default=None, help="WeLock-Konto (E-Mail).")
    parser.add_argument("--number", "-n", default=None, help="Schlossnummer (deviceNumber).")
    parser.add_argument(
        "--max-calls",
        type=int,
        default=len(DEFAULT_SWEEP),
        help=f"Obergrenze Cloud-Anfragen (Standard {len(DEFAULT_SWEEP)}).",
    )
    parser.add_argument(
        "--differential",
        action="store_true",
        help="Differenzielle Analyse: Baseline + Einzelbit-Flips von rf/battery (18 Anfragen).",
    )
    parser.add_argument(
        "--baseline-rf", type=int, default=7, help="randomFactor der Baseline (differenziell)."
    )
    parser.add_argument(
        "--baseline-battery", type=int, default=100, help="battery der Baseline (differenziell)."
    )
    parser.add_argument("--delay", type=float, default=1.2, help="Pause zwischen Anfragen (s).")
    parser.add_argument(
        "--save", action="store_true", help="Rohdaten+Bericht in tools/offline-data speichern."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Bestaetigungen automatisch akzeptieren."
    )
    args = parser.parse_args(argv)

    if args.differential and not (
        0 <= args.baseline_rf <= 255 and 0 <= args.baseline_battery <= 255
    ):
        parser.error("--baseline-rf und --baseline-battery muessen in 0..255 liegen.")

    print("=" * 72)
    print("  OFFLINE-FORSCHUNG: fragt eine KLEINE Menge Cloud-Unlock-Befehle an.")
    print("  Es wird NICHTS ans Schloss geschrieben (kein Unlock).")
    print("  Die Anfragen werden serverseitig als Unlock-Command-Anfragen verarbeitet.")
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
            f"Schluessel {mask(device_password)} vorhanden={bool(device_password)}"
        )
        baseline = (args.baseline_rf, args.baseline_battery) if args.differential else None
        if args.differential:
            sweep = differential_sweep(baseline)
            print(
                f"Differenzielle Analyse: {len(sweep)} Cloud-Anfragen "
                f"(Baseline rf={baseline[0]} battery={baseline[1]} + Einzelbit-Flips, kein BLE-Write)..."
            )
        else:
            sweep = DEFAULT_SWEEP[: max(2, args.max_calls)]
            print(f"Starte {len(sweep)} Cloud-Anfragen (kein BLE-Write)...")
        samples = collect_samples(session, number, ble_name, sweep, args.delay)
    except CloudError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1

    if not samples:
        print("Keine Samples erhalten; Auswertung nicht moeglich.", file=sys.stderr)
        return 1

    report = build_report(number, device_password, samples, baseline=baseline)
    print_summary(report)
    print_differential(report)
    if args.save:
        path = save_report(report)
        print(f"\nRohdaten+Bericht gespeichert: {path}")
    else:
        print("\n(Rohdaten nicht gespeichert; mit --save in tools/offline-data ablegen.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
