"""Misst Verbindungsaufbau und Ablauf zum WeLock-Schloss (gleiche Phasen wie die HA-Integration).

Pro Durchgang: Scan (bis das Schloss gehört wird) -> Verbinden -> Status -> (Befehl senden)
-> Trennen. Die Phasen heißen wie im Entsperr-Verlauf der Home-Assistant-Integration
(scan/connect/status/command/confirm/teardown), damit sich die Werte direkt vergleichen lassen.

Ohne --unlock wird NICHT entriegelt (nur Verbindung und Statusabfrage, beliebig oft möglich).
Mit --unlock --table DATEI wird der lokal bekannte Befehl zur Challenge gesendet (Tabellenformat
wie beim HA-Dienst import_commands; die Datei ist privat). Zwischen zwei Entriegelungen liegen
mindestens 30 s. Der Test läuft über den Bluetooth-Adapter dieses Rechners, nicht über den
Dongle von Home Assistant; Home Assistant und die WeLock-App sollten währenddessen nicht mit dem
Schloss verbunden sein.

Beispiele:
    python welock_bench.py C4:43:4A:03:42:A9
    python welock_bench.py C4:43:4A:03:42:A9 --rounds 10 --ha-connect 31
    python welock_bench.py C4:43:4A:03:42:A9 --listen 60 --rounds 0
    python welock_bench.py C4:43:4A:03:42:A9 --unlock --table welock-oracle-table.json

Exitcode: 0 = alle Durchgänge erfolgreich, 1 = mindestens ein Fehler, 2 = falsche Eingabe,
130 = mit Strg+C abgebrochen.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
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
PROGRESS_INTERVAL = 10.0  # ohne Terminal höchstens alle 10 s eine Fortschrittszeile

# Richtwerte für die Bewertung (keine Garantien, nur Orientierung).
GOOD_MEDIAN_S = 5.0
WOBBLY_MEDIAN_S = 15.0
WOBBLY_MIN_RATE = 0.7
MIN_ROUNDS_FOR_RATING = 3
SLOW_SCAN_S = 5.0

# Fehlerarten mit Meldung und nächstem Schritt.
ERRORS: dict[str, tuple[str, str]] = {
    "not_found": (
        "Schloss nicht gefunden",
        "Abstand unter 2 m, Schloss durch Berühren wecken, Bluetooth am PC prüfen, erneut starten.",
    ),
    "connect_timeout": (
        "Verbindung kam nicht zustande (Zeitüberschreitung)",
        "Mit --timeout erhöhen; prüfen, ob Home Assistant oder die WeLock-App gerade verbunden ist.",
    ),
    "connect_failed": (
        "Verbindung abgelehnt oder abgebrochen",
        "Bluetooth am PC aus- und wieder einschalten, danach erneut starten.",
    ),
    "exchange_failed": (
        "Statusabfrage fehlgeschlagen",
        "Erneut versuchen; tritt es wiederholt auf, den Abstand zum Schloss verringern.",
    ),
    "no_command": (
        "Kein Befehl für diese Challenge in der Tabelle",
        "Vollständige Tabelle verwenden (256 Einträge); es wurde nichts gesendet.",
    ),
}


@dataclass
class Round:
    """Ergebnis eines Durchgangs. Zeiten in ms, ``None`` = nicht erfasst (nie 0)."""

    index: int
    time: str
    scan_ms: int | None = None
    connect_ms: int | None = None
    status_ms: int | None = None
    command_ms: int | None = None
    confirm_ms: int | None = None
    teardown_ms: int | None = None
    rssi: int | None = None
    random_factor: int | None = None
    battery: int | None = None
    unlocked: bool = False  # Befehl wurde an das Schloss geschrieben
    confirmed: bool | None = None  # Schloss hat geantwortet (nur wenn unlocked)
    error: str | None = None  # Schlüssel aus ERRORS
    error_detail: str | None = None  # Ausnahmetyp und -text der Bluetooth-Bibliothek

    @property
    def ok(self) -> bool:
        return self.error is None


# --------------------------------------------------------------------------- Darstellung


def num(value: float, digits: int = 1) -> str:
    """Zahl mit Dezimalkomma."""
    return f"{value:.{digits}f}".replace(".", ",")


def fmt_seconds(ms: int | None) -> str:
    """Sekunden: unter 1 s zwei Stellen, sonst eine; ``-`` wenn nicht erfasst."""
    if ms is None:
        return "-"
    seconds = ms / 1000
    return num(seconds, 2 if seconds < 1 else 1)


def use_color(stream: object, environ: dict[str, str], no_color_flag: bool) -> bool:
    """Farbe nur auf einem Terminal und wenn NO_COLOR nicht gesetzt ist."""
    isatty = getattr(stream, "isatty", lambda: False)()
    return bool(isatty) and "NO_COLOR" not in environ and not no_color_flag


def paint(text: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text


def describe(err: BaseException) -> str:
    """Kurzer Ausnahmetext für die Fehlersuche (Typ und gekürzte Meldung)."""
    message = str(err).strip().replace("\n", " ")
    return f"{type(err).__name__}: {message}"[:100] if message else type(err).__name__


def percentile(sorted_values: list[int], fraction: float) -> int:
    """Wert am Anteil ``fraction`` (0..1) einer sortierten, nicht leeren Liste (Nearest-Rank)."""
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return sorted_values[index]


def time_to_connected(r: Round) -> int | None:
    """Zeit bis zur Verbindung inkl. Suche (scan + connect); nur wenn verbunden wurde.

    Home Assistant meldet als ``connect`` die Zeit bis zur Verbindung, einschließlich des
    Wartens auf das nächste Werbepaket des Schlosses. Damit der Vergleich fair bleibt, zählt
    hier die Suche mit.
    """
    if r.connect_ms is None or r.error in ("connect_timeout", "connect_failed"):
        return None
    return r.connect_ms + (r.scan_ms or 0)


def total_values(rounds: list[Round]) -> list[int]:
    return sorted(v for r in rounds if (v := time_to_connected(r)) is not None)


def phase_values(rounds: list[Round], key: str) -> list[int]:
    return sorted(v for r in rounds if isinstance(v := getattr(r, key), int))


def phase_stats(values: list[int]) -> tuple[int, int, int, int]:
    """(min, Median, P90, max) in ms; ``values`` muss sortiert und nicht leer sein."""
    return values[0], round(statistics.median(values)), percentile(values, 0.9), values[-1]


def rate(rounds: list[Round]) -> tuple[str, str]:
    """Bewertung nach Erfolgsquote und Median des Verbindungsaufbaus: (Stufe, Begründung)."""
    if len(rounds) < MIN_ROUNDS_FOR_RATING:
        return "ZU WENIG DATEN", f"mindestens {MIN_ROUNDS_FOR_RATING} Durchgänge nötig"
    ok = sum(r.ok for r in rounds)
    connects = total_values(rounds)
    if not connects:
        return "SCHLECHT", "keine einzige Verbindung kam zustande"
    median_s = statistics.median(connects) / 1000
    failures = len(rounds) - ok
    why = f"Verbindung steht im Median nach {num(median_s)} s (inkl. Suche)"
    if failures:
        why += f", {failures} Ausfall" + ("" if failures == 1 else "e")
    if failures == 0 and median_s < GOOD_MEDIAN_S:
        return "GUT", why
    if ok / len(rounds) >= WOBBLY_MIN_RATE and median_s < WOBBLY_MEDIAN_S:
        return "WACKELIG", why
    return "SCHLECHT", why


def conclusions(rounds: list[Round], ha_connect_s: float | None) -> list[str]:
    """Regelbasierte Hinweise zur Einordnung (Richtwerte, keine Garantie)."""
    lines: list[str] = []
    scans = phase_values(rounds, "scan_ms")
    connects = total_values(rounds)
    statuses = phase_values(rounds, "status_ms")
    if scans and statistics.median(scans) / 1000 > SLOW_SCAN_S:
        lines.append(
            "Das Schloss wird erst nach längerer Zeit gehört: seltene Werbung oder schwache "
            "Funkstrecke."
        )
    if connects:
        connect_s = statistics.median(connects) / 1000
        fast_status = bool(statuses) and statistics.median(statuses) / 1000 < 1
        if connect_s >= GOOD_MEDIAN_S * 2 and fast_status:
            lines.append(
                "Der Verbindungsaufbau ist langsam, danach läuft alles schnell: Das spricht für "
                "das Schloss bzw. die Funkstrecke, nicht für die Software."
            )
        if ha_connect_s is not None:
            slower = ha_connect_s - connect_s > max(5.0, connect_s * 0.5)
            verdict = (
                "Home Assistant ist deutlich langsamer: Dongle, VM oder gleichzeitige "
                "Verbindungen prüfen."
                if slower
                else "Home Assistant liegt in der gleichen Größenordnung: Das Schloss selbst "
                "ist die Ursache."
            )
            lines.append(
                f"Vergleich bis zur Verbindung (inkl. Suche): hier {num(connect_s)} s, Home Assistant "
                f"{num(ha_connect_s)} s. {verdict}"
            )
    lines.append(
        "Der Test nutzt den Bluetooth-Adapter dieses Rechners an dessen Standort, nicht den von Home Assistant."
    )
    return lines


def columns(unlock: bool) -> list[tuple[str, str]]:
    """(Attribut, Kopf) je Spalte; Befehl/Bestätigung nur mit --unlock."""
    cols = [("scan_ms", "Scan"), ("connect_ms", "Verbinden"), ("status_ms", "Status")]
    if unlock:
        cols += [("command_ms", "Befehl"), ("confirm_ms", "Bestätigt")]
    return [*cols, ("teardown_ms", "Trennen")]


def header(unlock: bool) -> str:
    cols = columns(unlock)
    top = " Nr " + " ".join(f"{name:>9}" for _, name in cols) + "  Ergebnis"
    unit = "    " + " ".join(f"{'[s]':>9}" for _ in cols)
    return f"{top}\n{unit}"


def result_text(r: Round) -> tuple[str, str]:
    """(Status, Details) einer Zeile; der Status ist immer auch als Text lesbar."""
    if r.error:
        message, step = ERRORS[r.error]
        detail = f" [{r.error_detail}]" if r.error_detail else ""
        return "FEHLER", f"{message}{detail}\n       -> {step}"
    parts = [f"RSSI {r.rssi} dBm" if r.rssi is not None else "RSSI nicht erfasst"]
    if r.battery is not None:
        parts.append(f"Akku {r.battery} %")
    if r.unlocked:
        parts.append("ENTRIEGELT" if r.confirmed else "ENTRIEGELT, UNBESTÄTIGT: Tür prüfen")
    return "OK", ", ".join(parts)


def format_row(r: Round, unlock: bool, color: bool) -> str:
    cells = " ".join(f"{fmt_seconds(getattr(r, key)):>9}" for key, _ in columns(unlock))
    status, details = result_text(r)
    padded = paint(status.ljust(6), "32" if r.ok else "31", color)
    return f"{r.index:>3} {cells}  {padded} {details}"


def format_summary(
    rounds: list[Round], unlock: bool, ha_connect_s: float | None, color: bool
) -> str:
    ok = sum(r.ok for r in rounds)
    lines = [
        f"\nZusammenfassung: {ok} von {len(rounds)} erfolgreich ({round(100 * ok / len(rounds))} %)",
        f"  {'Phase':<10} {'min':>7} {'Median':>7} {'P90':>7} {'max':>7}   (Sekunden)",
    ]
    for key, name in columns(unlock):
        values = phase_values(rounds, key)
        if values:
            stats = (fmt_seconds(v) for v in phase_stats(values))
            lines.append(f"  {name:<10} " + " ".join(f"{s:>7}" for s in stats))
    totals = total_values(rounds)
    if totals:
        stats = (fmt_seconds(v) for v in phase_stats(totals))
        lines.append(f"  {'Bis verb.':<10} " + " ".join(f"{s:>7}" for s in stats))
    level, why = rate(rounds)
    code = {"GUT": "32", "WACKELIG": "33", "SCHLECHT": "31"}.get(level, "0")
    lines.append(f"Bewertung: {paint(level, code, color)} - {why} (Richtwerte)")
    lines.extend(f"Hinweis: {line}" for line in conclusions(rounds, ha_connect_s))
    return "\n".join(lines)


class Progress:
    """Zeigt bei langen Wartezeiten, dass etwas passiert (Terminal: eine Zeile, sonst selten)."""

    def __init__(self, stream: object, enabled: bool) -> None:
        self._stream = stream
        self._tty = bool(getattr(stream, "isatty", lambda: False)())
        self._enabled = enabled
        self._last_print = float("-inf")
        self._dirty = False

    def update(self, label: str, elapsed: float, limit: float) -> None:
        if not self._enabled:
            return
        if self._tty:
            width = 20
            filled = min(width, int(width * elapsed / limit))
            bar = "#" * filled + "-" * (width - filled)
            text = f"\r  {label} {elapsed:>3.0f} s / {limit:.0f} s [{bar}]"
            print(text, end="", file=self._stream, flush=True)
            self._dirty = True
        elif time.monotonic() - self._last_print >= PROGRESS_INTERVAL:
            text = f"  {label} {elapsed:.0f} s / {limit:.0f} s ..."
            print(text, file=self._stream, flush=True)
            self._last_print = time.monotonic()

    def clear(self) -> None:
        if self._dirty and self._tty:
            print("\r" + " " * 60 + "\r", end="", file=self._stream, flush=True)
            self._dirty = False


# --------------------------------------------------------------------------- Eingaben


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


# --------------------------------------------------------------------------- Bluetooth


def _ms(since: float) -> int:
    return round((time.monotonic() - since) * 1000)


async def listen(address: str, seconds: float) -> dict[str, object]:
    """Beobachtet nur die Werbung des Schlosses und wertet Abstände und RSSI aus."""
    seen: list[tuple[float, int]] = []
    target = address.upper()

    def _callback(device, adv) -> None:  # noqa: ANN001
        if device.address.upper() == target:
            seen.append((time.monotonic(), adv.rssi))

    async with BleakScanner(_callback):
        await asyncio.sleep(seconds)

    result: dict[str, object] = {"sekunden": seconds, "pakete": len(seen)}
    if len(seen) >= 2:
        gaps = [b[0] - a[0] for a, b in zip(seen, seen[1:], strict=False)]
        rssis = [r for _, r in seen]
        result.update(
            abstand_min_s=round(min(gaps), 2),
            abstand_median_s=round(statistics.median(gaps), 2),
            abstand_max_s=round(max(gaps), 2),
            rssi_min=min(rssis),
            rssi_median=round(statistics.median(rssis)),
            rssi_max=max(rssis),
        )
    return result


async def _scan(address: str, timeout: float, row: Round, progress: Progress) -> object | None:
    """Wartet, bis das Schloss gehört wird; ``None`` bei Zeitüberschreitung."""
    found: asyncio.Future = asyncio.get_running_loop().create_future()

    def _callback(device, adv) -> None:  # noqa: ANN001
        if device.address.upper() == address.upper():
            row.rssi = adv.rssi
            if not found.done():
                found.set_result(device)

    started = time.monotonic()
    try:
        async with BleakScanner(_callback):
            while not found.done():
                elapsed = time.monotonic() - started
                if elapsed >= timeout:
                    return None
                progress.update("Suche    ", elapsed, timeout)
                await asyncio.wait({found}, timeout=min(1.0, timeout - elapsed))
    finally:
        row.scan_ms = _ms(started)
        progress.clear()
    return found.result()


async def _connect(
    target: object, timeout: float, row: Round, progress: Progress
) -> BleakClient | None:
    """Baut die Verbindung auf; setzt ``row.error`` bei Misserfolg."""
    client = BleakClient(target, timeout=timeout)
    started = time.monotonic()
    task = asyncio.ensure_future(client.connect())
    try:
        while not task.done():
            elapsed = time.monotonic() - started
            if elapsed >= timeout + 5:
                task.cancel()
                row.error = "connect_timeout"
                break
            progress.update("Verbinden", elapsed, timeout)
            await asyncio.wait({task}, timeout=min(1.0, timeout + 5 - elapsed))
        if row.error is None:
            task.result()
    except asyncio.CancelledError:
        task.cancel()
        raise
    except (asyncio.TimeoutError, TimeoutError) as err:  # two different classes before Python 3.11
        row.error, row.error_detail = "connect_timeout", describe(err)
    except (BleakError, OSError) as err:
        row.error, row.error_detail = "connect_failed", describe(err)
    finally:
        row.connect_ms = _ms(started)
        progress.clear()
    return client if row.error is None else None


async def one_round(
    index: int,
    address: str,
    *,
    timeout: float,
    direct: bool,
    table: dict[int, bytes] | None,
    progress: Progress,
) -> Round:
    """Ein Durchgang: (scannen) -> verbinden -> Status -> (entsperren) -> trennen."""
    row = Round(index=index, time=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    target: object = address
    if not direct:
        target = await _scan(address, timeout, row, progress)
        if target is None:
            row.error = "not_found"
            return row

    client = await _connect(target, timeout, row, progress)
    if client is None:
        return row

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
        row.status_ms = _ms(phase)
        row.random_factor, row.battery = state.random_factor, state.battery

        if table is not None:
            phase = time.monotonic()
            command = table.get(state.random_factor)
            row.command_ms = _ms(phase)
            if command is None:
                row.error = "no_command"
            else:
                waiting = True
                phase = time.monotonic()
                await client.write_gatt_char(WRITE_UUID, command, response=False)
                row.unlocked = True
                try:
                    await asyncio.wait_for(followup, CONFIRM_TIMEOUT)
                    row.confirmed = True
                except asyncio.TimeoutError:
                    row.confirmed = False
                row.confirm_ms = _ms(phase)
    except (BleakError, asyncio.TimeoutError, ValueError, OSError) as err:
        row.error, row.error_detail = "exchange_failed", describe(err)
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
        row.teardown_ms = _ms(phase)
    return row


# --------------------------------------------------------------------------- Ablauf


def intro(args: argparse.Namespace) -> str:
    mode = "direkt, ohne Scan (RSSI nicht verfügbar)" if args.direct else "mit Scan vorab"
    action = "ENTRIEGELT ECHT" if args.unlock else "ohne Entriegeln"
    return (
        f"WeLock-Messung  {args.address}\n"
        f"{args.rounds} Durchgänge | Pause {args.pause:g} s | Zeitlimit {args.timeout:g} s | "
        f"{mode} | {action} | Abbruch: Strg+C\n"
        "Phasen wie im HA-Entsperr-Verlauf: Scan=scan, Verbinden=connect, Status=status, "
        "Trennen=teardown"
    )


async def run(args: argparse.Namespace, rounds: list[Round], color: bool) -> None:
    table = load_table(args.table) if args.unlock else None
    progress = Progress(sys.stdout, enabled=not args.quiet)
    print(intro(args))
    if args.listen:
        print(f"\nBeobachte die Werbung {args.listen:g} s lang ...")
        print(json.dumps(await listen(args.address, args.listen), indent=2, ensure_ascii=False))
    if not args.rounds:
        return
    print("\n" + header(args.unlock))
    last_unlock = float("-inf")
    for index in range(1, args.rounds + 1):
        if table is not None:
            wait = MIN_UNLOCK_INTERVAL - (time.monotonic() - last_unlock)
            if wait > 0:
                await asyncio.sleep(wait)
        row = await one_round(
            index,
            args.address,
            timeout=args.timeout,
            direct=args.direct,
            table=table,
            progress=progress,
        )
        if row.unlocked:
            last_unlock = time.monotonic()
        rounds.append(row)
        print(format_row(row, args.unlock, color))
        if index < args.rounds:
            await asyncio.sleep(args.pause)


def finish(args: argparse.Namespace, rounds: list[Round], color: bool, interrupted: bool) -> int:
    """Gibt Zusammenfassung und Rohdaten aus und liefert den Exitcode."""
    if rounds:
        print(format_summary(rounds, args.unlock, args.ha_connect, color))
        if args.out:
            data = [asdict(r) for r in rounds]
            Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
            print(f"Rohdaten: {args.out}")
    if interrupted:
        print("\nAbgebrochen; die bisherigen Durchgänge sind oben ausgewertet.", file=sys.stderr)
        return 130
    return 0 if all(r.ok for r in rounds) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("address", help="BLE-Adresse des Schlosses (z. B. C4:43:4A:03:42:A9)")
    parser.add_argument("--rounds", type=int, default=5, help="Anzahl Durchgänge (Standard 5)")
    parser.add_argument("--pause", type=float, default=5.0, help="Pause zwischen Durchgängen in s")
    parser.add_argument("--timeout", type=float, default=60.0, help="Zeitlimit je Schritt in s")
    parser.add_argument(
        "--listen", type=float, default=0.0, help="vorab Werbeverhalten beobachten (s)"
    )
    parser.add_argument("--direct", action="store_true", help="ohne eigenen Scan direkt verbinden")
    parser.add_argument(
        "--unlock", action="store_true", help="wirklich entsperren (braucht --table)"
    )
    parser.add_argument("--table", help="Befehlstabelle (JSON) für --unlock; privat halten")
    parser.add_argument(
        "--yes", action="store_true", help="Sicherheitsabfrage für --unlock überspringen"
    )
    parser.add_argument(
        "--ha-connect", type=float, help="Verbindungszeit in Home Assistant (s) zum Vergleich"
    )
    parser.add_argument("--out", help="Rohdaten als JSON speichern")
    parser.add_argument("--no-color", action="store_true", help="keine Farben")
    parser.add_argument("--quiet", action="store_true", help="keine Fortschrittsanzeige")
    return parser


def validate(args: argparse.Namespace) -> str | None:
    """Fehlertext bei unsinnigen Eingaben, sonst ``None``."""
    if args.rounds < 0 or args.pause < 0 or args.listen < 0 or args.timeout <= 0:
        return "--rounds, --pause, --listen dürfen nicht negativ sein; --timeout muss positiv sein."
    if args.ha_connect is not None and args.ha_connect <= 0:
        return "--ha-connect muss eine positive Zahl in Sekunden sein."
    if args.unlock and not args.table:
        return "--unlock braucht --table DATEI."
    return None


def confirm_unlock(args: argparse.Namespace) -> bool:
    minutes = args.rounds * MIN_UNLOCK_INTERVAL / 60
    print(
        f"ACHTUNG: Es werden bis zu {args.rounds} echte Entsperrbefehle gesendet "
        f"(je mindestens 30 s Abstand, Dauer etwa {minutes:.0f} min).\n"
        "Die Tür wird wirklich entriegelt. Home Assistant und die WeLock-App dürfen "
        "währenddessen nicht entsperren."
    )
    return input("ENTRIEGELN eingeben zum Fortfahren: ").strip() == "ENTRIEGELN"


def main() -> int:
    args = build_parser().parse_args()
    error = validate(args)
    if error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 2
    if BleakScanner is None:
        print(
            "Fehler: 'bleak' fehlt.\n  -> pip install -r tools/requirements-ble.txt",
            file=sys.stderr,
        )
        return 1
    if args.unlock and not args.yes and not confirm_unlock(args):
        print("Abgebrochen; es wurde nichts gesendet.")
        return 1
    if os.name == "nt":
        os.system("")  # schaltet ANSI-Farben in Windows-Konsolen ein
    color = use_color(sys.stdout, dict(os.environ), args.no_color)
    rounds: list[Round] = []
    interrupted = False
    try:
        asyncio.run(run(args, rounds, color))
    except KeyboardInterrupt:
        interrupted = True
    except (OSError, ValueError) as err:
        print(f"Fehler: {err}", file=sys.stderr)
        return 1
    return finish(args, rounds, color, interrupted)


if __name__ == "__main__":
    raise SystemExit(main())
