"""Autorisierter Vor-Ort Entriegelungstest via BLE und WeLock Cloud API."""

from __future__ import annotations

import math
import sys

try:
    from welock_command_probe import build_arg_parser, run_interactive
except ImportError:
    from tools.welock_command_probe import build_arg_parser, run_interactive


def main() -> int:
    parser = build_arg_parser(
        "Autorisierter Vor-Ort Entriegelungstest: Sendet 15-Byte-Befehl per BLE an das Schloss."
    )
    args = parser.parse_args()

    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout muss eine positive Zahl sein.")

    target_address = args.address or args.positional_address

    try:
        return run_interactive(
            send_unlock=True,
            address=target_address,
            account=args.account,
            number=args.number,
            name=args.name,
            timeout=args.timeout,
            auto_yes=args.yes,
            show_command=args.show_command,
            as_json=args.json,
        )
    except (EOFError, KeyboardInterrupt):
        print(
            "\nAbgebrochen. Falls ein Unlock-Write schon begonnen hat, Ergebnis mechanisch prüfen.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
