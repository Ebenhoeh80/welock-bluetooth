"""Interaktives Hauptmenü für alle WeLock BLE- und Cloud-Diagnosewerkzeuge."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent


def run_script(script_name: str, *args: str) -> int:
    """Führt ein Python-Skript im Tools-Verzeichnis mit aktuellem Interpreter aus."""
    script_path = TOOLS_DIR / script_name
    cmd = [sys.executable, str(script_path), *args]
    print(f"\n---> Starte: {script_name} {' '.join(args)} ---\n")
    try:
        res = subprocess.run(cmd)
        return res.returncode
    except KeyboardInterrupt:
        print("\nAusführung durch Benutzer abgebrochen.")
        return 1
    except Exception as exc:
        print(f"\nFehler beim Starten von {script_name}: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    while True:
        print("\n" + "=" * 65)
        print("  🔐 WeLock Smart Lock — Diagnose- und Test-Suite")
        print("=" * 65)
        print("  [1] BLE-Gerätesuche & WeLock-Erkennung      (ble_scan.py)")
        print("  [2] Akkustand & Challenge per BLE auslesen  (ble_battery.py)")
        print("  [3] GATT-Dienste & Characteristics prüfen  (ble_probe.py)")
        print("  [4] Cloud-Konto prüfen & Geräte auflisten  (welock_cloud_login.py)")
        print("  [5] Hybrid-Test: Challenge & Cloud-Befehl  (welock_command_probe.py)")
        print("  [6] Autorisierter Entriegelungstest        (welock_unlock.py)")
        print("  [7] System- & Abhängigkeitsprüfung        (dependency_check.py)")
        print("  [0] Beenden")
        print("-" * 65)

        try:
            choice = input("Option auswählen [0-7]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nProgramm beendet.")
            return 0

        if choice == "0":
            print("Auf Wiedersehen!")
            return 0

        elif choice == "1":
            welock_only = input("Nur WeLock-Schlösser anzeigen? [j/N]: ").strip().lower()
            args = ["--welock-only"] if welock_only in ("j", "ja", "y") else []
            run_script("ble_scan.py", *args)

        elif choice == "2":
            addr = input("BLE-Adresse des Schlosses (z. B. AA:BB:CC:DD:EE:FF): ").strip()
            if addr:
                run_script("ble_battery.py", addr)
            else:
                print("Keine Adresse angegeben. Breche ab.")

        elif choice == "3":
            addr = input("BLE-Adresse des Schlosses: ").strip()
            if addr:
                run_script("ble_probe.py", "--address", addr, "--connect")
            else:
                print("Keine Adresse angegeben. Breche ab.")

        elif choice == "4":
            run_script("welock_cloud_login.py")

        elif choice == "5":
            run_script("welock_command_probe.py")

        elif choice == "6":
            run_script("welock_unlock.py")

        elif choice == "7":
            run_script("dependency_check.py")

        else:
            print("Ungültige Eingabe. Bitte wählen Sie eine Zahl zwischen 0 und 7.")

        try:
            input("\n[Drücken Sie Enter, um zum Hauptmenü zurückzukehren...]")
        except (KeyboardInterrupt, EOFError):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
