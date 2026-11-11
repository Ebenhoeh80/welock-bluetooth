"""Dependency- und Systemprüfungen für die WeLock Diagnose-Tools."""

from __future__ import annotations

import platform
import subprocess
import sys


def check_python_version() -> tuple[bool, str]:
    """Prüft, ob Python >= 3.10 vorhanden ist."""
    current = sys.version_info
    version_str = f"{current.major}.{current.minor}.{current.micro}"
    if current < (3, 10):
        return (
            False,
            f"Python 3.10 oder neuer erforderlich (aktuelle Version: {version_str}).",
        )
    return True, f"Python {version_str} (OK)"


def check_bleak_installed() -> tuple[bool, str]:
    """Prüft, ob das Modul bleak importiert werden kann."""
    try:
        import bleak  # noqa: F401

        version = getattr(bleak, "__version__", "unbekannt")
        return True, f"bleak v{version} installiert (OK)"
    except ImportError:
        return (
            False,
            (
                "Das Python-Modul 'bleak' fehlt. "
                "Installieren mit: pip install -r tools/requirements-ble.txt"
            ),
        )


def check_bluetooth_system() -> tuple[bool, str]:
    """Prüft betriebssystemspezifische Bluetooth-Voraussetzungen."""
    os_name = platform.system()
    if os_name == "Linux":
        return True, "Linux (BlueZ-Stack erforderlich; 'systemctl status bluetooth' prüfen)"
    if os_name == "Darwin":
        return (
            True,
            "macOS (CoreBluetooth; Terminal-Berechtigung unter Datenschutz & Sicherheit)",
        )
    if os_name == "Windows":
        return (
            True,
            "Windows (WinRT-Bluetooth-Stack erforderlich; Bluetooth aktivieren)",
        )
    return True, f"Betriebssystem {os_name} erkannt"


def print_dependency_report() -> bool:
    """Gibt einen formatierten Bericht über alle Abhängigkeiten aus."""
    print("=" * 65)
    print("  WeLock Tools — System- und Abhängigkeitsprüfung")
    print("=" * 65)

    all_ok = True

    # 1. Python
    py_ok, py_msg = check_python_version()
    status_py = "[OK]" if py_ok else "[FEHLER]"
    print(f" {status_py:<8} {py_msg}")
    if not py_ok:
        all_ok = False

    # 2. Bleak
    bleak_ok, bleak_msg = check_bleak_installed()
    status_bleak = "[OK]" if bleak_ok else "[WARNUNG]"
    print(f" {status_bleak:<8} {bleak_msg}")
    if not bleak_ok:
        all_ok = False

    # 3. OS
    _, os_msg = check_bluetooth_system()
    print(f" [INFO]   {os_msg}")

    print("-" * 65)
    if all_ok:
        print("  Status: Alle Kern-Abhängigkeiten sind erfüllt!")
    else:
        print("  Status: Bitte fehlende Abhängigkeiten vor der BLE-Nutzung beheben.")
    print("=" * 65)
    return all_ok


def install_bleak() -> bool:
    """Versucht bleak automatisch zu installieren."""
    print("Versuche automatische Installation von 'bleak>=0.22.0,<3.0.0'...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "bleak>=0.22.0,<3.0.0"]
        )
        print("Installation erfolgreich abgeschlossen!")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"Installation fehlgeschlagen (Exit-Code {exc.returncode}).", file=sys.stderr)
        print(
            "Bitte manuell ausführen: pip install -r tools/requirements-ble.txt",
            file=sys.stderr,
        )
        return False


def main() -> int:
    """CLI-Einstiegspunkt für direkte Abhängigkeitsprüfung."""
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        return 0 if install_bleak() else 1
    return 0 if print_dependency_report() else 1


if __name__ == "__main__":
    raise SystemExit(main())
