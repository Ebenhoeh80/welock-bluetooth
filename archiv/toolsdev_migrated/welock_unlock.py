"""One explicitly authorized cloud-assisted BLE unlock experiment."""

import subprocess
import sys


def ensure_dependencies() -> None:
    # 1. Prüfen, ob pip vorhanden ist
    try:
        import pip
    except ImportError:
        print("pip ist nicht installiert. Versuche pip zu installieren...", file=sys.stderr)
        try:
            import ensurepip
            ensurepip.bootstrap()
        except Exception as e:
            print(f"Fehler beim Installieren von pip: {e}", file=sys.stderr)
            sys.exit(1)

    # 2. Prüfen, ob bleak vorhanden ist
    try:
        import bleak  # noqa: F401
    except ImportError:
        print("Die Bibliothek 'bleak' ist nicht installiert. Wird automatisch installiert...", file=sys.stderr)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "bleak"])
            print("'bleak' wurde erfolgreich installiert.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei der Installation von 'bleak': {e}", file=sys.stderr)
            sys.exit(1)


# Abhängigkeiten vor dem Start prüfen
ensure_dependencies()

from welock_command_probe import run_interactive


def main() -> int:
    try:
        return run_interactive(send_unlock=True)
    except (EOFError, KeyboardInterrupt):
        print("\nAbgebrochen. Falls ein Unlock-Write schon begonnen hat, Ergebnis mechanisch pruefen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())