"""Misst Verbindungsaufbau und Ablauf zum WeLock-Schloss und erfasst dieselben Werte wie die HA-Integration.

Pro Durchgang werden – wie im Entsperr-Verlauf der Home-Assistant-Integration – diese Zeiten
erfasst: scan (bis das Schloss gehört wird), connect, status, command, confirm, teardown,
dazu Signalstärke (RSSI) und Alter der letzten Werbung beim Verbindungsstart.

Standardmäßig wird NICHT entriegelt (nur Verbindung und Statusabfrage; unbegrenzt oft möglich).
Mit ``--unlock --table DATEI`` wird zusätzlich der lokal bekannte Befehl für die Challenge
gesendet (gleiches Tabellenformat wie ``import_commands``; die Datei ist privat und darf nicht
veröffentlicht werden). Zwischen zwei Entriegelungen liegen mindestens 30 Sekunden.

Mit ``--listen SEK`` wird vorab nur das Werbeverhalten des Schlosses beobachtet (Abstände
zwischen den Werbepaketen, RSSI), ohne eine Verbindung aufzubauen.

Beispiele:
    python welock_bench.py C4:43:4A:03:42:A9 --rounds 10
    python welock_bench.py C4:43:4A:03:42:A9 --listen 60
    python welock_bench.py C4:43:4A:03:42:A9 --rounds 5 --unlock --table welock-oracle-table.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None  # type: ignore[assignment,misc]
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakError = Exception  # type: ignore[assignment,misc]

try:
    from welock_protocol import BATTERY_REQUEST, NOTIFY_UUID, WRITE_UUID, parse_battery_response
except ImportError:
    from tools.welock_protocol import (
        BATTERY_REQUEST,
        NOTIFY_UUID,
        WRITE_UUID,
        parse_battery_response,
    )

MIN_UNLOCK_INTERVAL = 30.0
CONFIRM_TIMEOUT = 3.0
COLUMNS = ("scan_ms", "connect_ms", "status_ms", "command_ms", "confirm_ms", "teardown_ms")


def _ms(since: float) -> int:
    return round((time.monotonic() - since) * 1000)


def load_table(path: str) -> dict[int, bytes]:
    """Liest eine Befehlstabelle (Format wie der HA-Dienst import_commands)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = data.get("table") if isinstance(data, dict) else None
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Die Datei enthält keine Tabelle ('table').")
    table: dict[int, bytes] = {}
    for key, value in raw.items():
        command = str(value).encode("ascii")
        if len(command) != 15 or not command.startswith(b"U1") or not command.isalnum():
            raise ValueError(f"Ungültiger Befehl für randomFactor {key}.")
        table[int(key)] = command
    return table


async def listen(address: str, seconds: float) -> dict[str, object]:
    """Beobachtet nur die Werbung des Schlosses und wertet Abstände und RSSI aus."""
    seen: list[tuple[float, int]] = []
    target = address.upper()

    def _callback(device, adv) -> None:  # noqa: ANN001
        if device.address.upper() == target:
            seen.append((time.monotonic(), adv.rssi))

    async with BleakScanner(_callback):
        await asyncio.sleep(seconds)

    result: dict[str, object] = {"seconds": seconds, "packets": len(seen)}
    if len(seen) >= 2:
        gaps = [b[0] - a[0] for a, b in zip(seen, seen[1:], strict=False)]
        rssis = [r for _, r in seen]
        result.update(
            gap_min_s=round(min(gaps), 2),
            gap_median_s=round(statistics.median(gaps), 2),
            gap_max_s=round(max(gaps), 2),
            rssi_min=min(rssis),
            rssi_median=round(statistics.median(rssis)),
            rssi_max=max(rssis),
        )
    return result


async def one_round(
    address: str,
    *,
    timeout: float,
    direct: bool,
    table: dict[int, bytes] | None,
) -> dict[str, object]:
    """Ein Durchgang: (scannen) -> verbinden -> Status -> (entsperren) -> trennen."""
    row: dict[str, object] = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    target: object = address
    last_adv = time.monotonic()

    if not direct:
        phase = time.monotonic()
        found: asyncio.Future = asyncio.get_running_loop().create_future()

        def _callback(device, adv) -> None:  # noqa: ANN001
            nonlocal last_adv
            if device.address.upper() == address.upper():
                last_adv = time.monotonic()
                row["rssi"] = adv.rssi
                if not found.done():
                    found.set_result(device)

        try:
            async with BleakScanner(_callback):
                target = await asyncio.wait_for(found, timeout)
        except asyncio.TimeoutError:
            row["scan_ms"] = _ms(phase)
            row["error"] = "nicht gefunden (Scan-Timeout)"
            return row
        row["scan_ms"] = _ms(phase)
        row["adv_age_ms"] = _ms(last_adv)

    client = BleakClient(target, timeout=timeout)
    phase = time.monotonic()
    try:
        await client.connect()
    except (BleakError, asyncio.TimeoutError, OSError) as err:
        row["connect_ms"] = _ms(phase)
        row["error"] = f"Verbindung fehlgeschlagen: {type(err).__name__}"
        return row
    row["connect_ms"] = _ms(phase)

    loop = asyncio.get_running_loop()
    status: asyncio.Future = loop.create_future()
    followup: asyncio.Future = loop.create_future()
    waiting = False

    def _notify(_sender: object, data: bytearray) -> None:
        if waiting and not followup.done():
            followup.set_result(None)
            return
        if not status.done() and bytes(data)[:2] == b"\x55\x30":
            try:
                status.set_result(parse_battery_response(bytes(data)))
            except ValueError as err:
                status.set_exception(err)

    try:
        phase = time.monotonic()
        await client.start_notify(NOTIFY_UUID, _notify)
        await client.write_gatt_char(WRITE_UUID, BATTERY_REQUEST, response=False)
        state = await asyncio.wait_for(status, timeout)
        row["status_ms"] = _ms(phase)
        row["random_factor"] = state.random_factor
        row["battery"] = state.battery

        if table is not None:
            phase = time.monotonic()
            command = table.get(state.random_factor)
            row["command_ms"] = _ms(phase)
            if command is None:
                row["error"] = "kein Befehl für diese Challenge in der Tabelle"
            else:
                waiting = True
                phase = time.monotonic()
                await client.write_gatt_char(WRITE_UUID, command, response=False)
                try:
                    await asyncio.wait_for(followup, CONFIRM_TIMEOUT)
                    row["confirmed"] = True
                except asyncio.TimeoutError:
                    row["confirmed"] = False
                row["confirm_ms"] = _ms(phase)
                row["unlocked_at"] = time.monotonic()
    except (BleakError, asyncio.TimeoutError, ValueError, OSError) as err:
        row["error"] = f"Austausch fehlgeschlagen: {type(err).__name__}"
    finally:
        phase = time.monotonic()
        try:
            await client.stop_notify(NOTIFY_UUID)
        except (BleakError, asyncio.TimeoutError, OSError):
            pass
        try:
            await client.disconnect()
        except (BleakError, asyncio.TimeoutError, OSError):
            pass
        row["teardown_ms"] = _ms(phase)
    return row


def _fmt(value: object) -> str:
    return "-" if value is None else str(value)


def print_row(index: int, row: dict[str, object]) -> None:
    cells = " ".join(f"{_fmt(row.get(key)):>9}" for key in COLUMNS)
    extra = f"rssi={_fmt(row.get('rssi'))} alter={_fmt(row.get('adv_age_ms'))}ms"
    if "random_factor" in row:
        extra += f" rf={row['random_factor']} akku={row.get('battery')}%"
    if row.get("confirmed") is not None:
        extra += " bestätigt" if row["confirmed"] else " UNBESTÄTIGT"
    if "error" in row:
        extra += f"  FEHLER: {row['error']}"
    print(f"{index:>3} {cells}  {extra}")


def summarize(rows: list[dict[str, object]]) -> None:
    ok = [r for r in rows if "error" not in r]
    print(f"\nErfolgreich: {len(ok)} von {len(rows)}")
    for key in COLUMNS:
        values = sorted(int(r[key]) for r in rows if isinstance(r.get(key), int))  # type: ignore[arg-type]
        if not values:
            continue
        p90 = values[min(len(values) - 1, round(0.9 * (len(values) - 1)))]
        print(
            f"  {key:<12} min {values[0]:>6}  Median {round(statistics.median(values)):>6}"
            f"  P90 {p90:>6}  max {values[-1]:>6}"
        )


async def main_async(args: argparse.Namespace) -> int:
    table = load_table(args.table) if args.unlock else None
    if args.listen:
        print(f"Beobachte die Werbung des Schlosses {args.listen:.0f} s lang ...")
        print(json.dumps(await listen(args.address, args.listen), indent=2))
        if not args.rounds:
            return 0

    print(f"\n{'#':>3} " + " ".join(f"{c:>9}" for c in COLUMNS) + "  Details")
    rows: list[dict[str, object]] = []
    last_unlock = float("-inf")
    for index in range(1, args.rounds + 1):
        if table is not None:
            wait = MIN_UNLOCK_INTERVAL - (time.monotonic() - last_unlock)
            if wait > 0:
                await asyncio.sleep(wait)
        row = await one_round(args.address, timeout=args.timeout, direct=args.direct, table=table)
        if "unlocked_at" in row:
            last_unlock = float(row.pop("unlocked_at"))  # type: ignore[arg-type]
        rows.append(row)
        print_row(index, row)
        if index < args.rounds:
            await asyncio.sleep(args.pause)
    summarize(rows)
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nRohdaten gespeichert: {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("address", help="BLE-Adresse des Schlosses (z. B. C4:43:4A:03:42:A9)")
    parser.add_argument("--rounds", type=int, default=10, help="Anzahl Durchgänge (Standard 10)")
    parser.add_argument("--pause", type=float, default=10.0, help="Pause zwischen Durchgängen in s")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout je Schritt in s")
    parser.add_argument(
        "--listen", type=float, default=0.0, help="vorab Werbeverhalten beobachten (s)"
    )
    parser.add_argument("--direct", action="store_true", help="ohne eigenen Scan direkt verbinden")
    parser.add_argument(
        "--unlock", action="store_true", help="auch wirklich entsperren (braucht --table)"
    )
    parser.add_argument("--table", help="Befehlstabelle (JSON) für --unlock; privat halten")
    parser.add_argument(
        "--yes", action="store_true", help="Sicherheitsabfrage für --unlock überspringen"
    )
    parser.add_argument("--out", help="Rohdaten als JSON speichern")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if BleakScanner is None:
        print(
            "Fehler: 'bleak' fehlt. Installation: pip install -r tools/requirements-ble.txt",
            file=sys.stderr,
        )
        return 1
    if args.rounds < 0 or args.timeout <= 0 or args.pause < 0:
        print(
            "Fehler: --rounds, --timeout und --pause müssen sinnvolle Werte haben.", file=sys.stderr
        )
        return 1
    if args.unlock:
        if not args.table:
            print("Fehler: --unlock braucht --table DATEI.", file=sys.stderr)
            return 1
        if not args.yes:
            print(
                f"Es werden bis zu {args.rounds} echte Entsperrbefehle gesendet (je >= 30 s Abstand)."
            )
            if input("ENTRIEGELN eingeben zum Fortfahren: ").strip() != "ENTRIEGELN":
                print("Abgebrochen; es wurde nichts gesendet.")
                return 1
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as err:
        print(f"Fehler: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
