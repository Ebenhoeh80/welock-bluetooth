"""One explicitly authorized cloud-assisted BLE unlock experiment."""

import sys

from tools.welock_command_probe import run_interactive


def main() -> int:
    try:
        return run_interactive(send_unlock=True)
    except (EOFError, KeyboardInterrupt):
        print("\nAbgebrochen. Falls ein Unlock-Write schon begonnen hat, Ergebnis mechanisch pruefen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
