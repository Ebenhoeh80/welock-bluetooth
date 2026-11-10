"""Autorisierter Vor-Ort Entriegelungstest via BLE und WeLock Cloud API."""

from __future__ import annotations

import sys

try:
    from welock_command_probe import run_interactive
except ImportError:
    from tools.welock_command_probe import run_interactive


def main() -> int:
    try:
        return run_interactive(send_unlock=True)
    except (EOFError, KeyboardInterrupt):
        print(
            "\nAbgebrochen. Falls ein Unlock-Write schon begonnen hat, Ergebnis mechanisch prüfen.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
