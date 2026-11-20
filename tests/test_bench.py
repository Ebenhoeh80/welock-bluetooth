"""Tests for the pure logic of tools/welock_bench.py (formatting, statistics, rating)."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from tools import welock_bench as bench


def _round(index: int = 1, **fields: object) -> bench.Round:
    return bench.Round(index=index, time="2026-11-20T10:00:00+00:00", **fields)  # type: ignore[arg-type]


def _ok(connect_ms: int, index: int = 1) -> bench.Round:
    return _round(index, connect_ms=connect_ms, status_ms=60, teardown_ms=200, battery=100)


class FormatTests(unittest.TestCase):
    def test_seconds_use_decimal_comma_and_precision(self) -> None:
        self.assertEqual(bench.fmt_seconds(17543), "17,5")
        self.assertEqual(bench.fmt_seconds(58), "0,06")
        self.assertEqual(bench.fmt_seconds(1000), "1,0")

    def test_missing_value_is_a_dash_never_zero(self) -> None:
        self.assertEqual(bench.fmt_seconds(None), "-")
        self.assertNotEqual(bench.fmt_seconds(0), "-")

    def test_color_needs_a_terminal_and_no_no_color(self) -> None:
        class Tty(io.StringIO):
            def isatty(self) -> bool:
                return True

        self.assertTrue(bench.use_color(Tty(), {}, False))
        self.assertFalse(bench.use_color(Tty(), {"NO_COLOR": "1"}, False))
        self.assertFalse(bench.use_color(Tty(), {}, True))
        self.assertFalse(bench.use_color(io.StringIO(), {}, False))

    def test_plain_output_has_no_escape_codes(self) -> None:
        text = bench.format_row(_ok(5000), False, False)
        self.assertNotIn("\033", text)
        self.assertIn("OK", text)

    def test_unlock_columns_only_with_unlock(self) -> None:
        self.assertNotIn("Befehl", bench.header(False))
        self.assertIn("Befehl", bench.header(True))

    def test_missing_rssi_is_explained(self) -> None:
        self.assertIn("RSSI nicht erfasst", bench.format_row(_ok(5000), False, False))

    def test_every_error_names_the_next_step(self) -> None:
        for key in bench.ERRORS:
            text = bench.format_row(_round(error=key), False, False)
            self.assertIn("FEHLER", text)
            self.assertIn("->", text)

    def test_unconfirmed_unlock_warns_to_check_the_door(self) -> None:
        row = _round(connect_ms=1, unlocked=True, confirmed=False)
        self.assertIn("Tür prüfen", bench.result_text(row)[1])
        self.assertIn("ENTRIEGELT", bench.result_text(_round(unlocked=True, confirmed=True))[1])


class StatisticsTests(unittest.TestCase):
    def test_phase_stats(self) -> None:
        self.assertEqual(bench.phase_stats([1, 2, 3, 4, 100]), (1, 3, 100, 100))

    def test_missing_values_are_ignored(self) -> None:
        rounds = [_ok(1000), _round(2, error="not_found"), _ok(3000, 3)]
        self.assertEqual(bench.phase_values(rounds, "connect_ms"), [1000, 3000])
        self.assertEqual(bench.phase_values(rounds, "scan_ms"), [])

    def test_percentile_of_single_value(self) -> None:
        self.assertEqual(bench.percentile([7], 0.9), 7)


class RatingTests(unittest.TestCase):
    def test_too_few_rounds(self) -> None:
        self.assertEqual(bench.rate([_ok(1000), _ok(1000)])[0], "ZU WENIG DATEN")

    def test_good(self) -> None:
        self.assertEqual(bench.rate([_ok(2000, i) for i in range(1, 4)])[0], "GUT")

    def test_wobbly_when_medium_slow(self) -> None:
        self.assertEqual(bench.rate([_ok(9000, i) for i in range(1, 4)])[0], "WACKELIG")

    def test_bad_when_very_slow(self) -> None:
        # The real PC measurement: about 17.5 s to connect.
        self.assertEqual(bench.rate([_ok(17500, i) for i in range(1, 4)])[0], "SCHLECHT")

    def test_one_failure_is_never_good(self) -> None:
        rounds = [_ok(1000, 1), _ok(1000, 2), _ok(1000, 3), _round(4, error="not_found")]
        self.assertEqual(bench.rate(rounds)[0], "WACKELIG")

    def test_no_connection_at_all_is_bad(self) -> None:
        rounds = [_round(i, error="not_found") for i in range(1, 4)]
        self.assertEqual(bench.rate(rounds)[0], "SCHLECHT")


class ConclusionTests(unittest.TestCase):
    def test_slow_connect_with_fast_status_points_to_the_lock(self) -> None:
        text = " ".join(bench.conclusions([_ok(17500, i) for i in range(1, 4)], None))
        self.assertIn("Schloss", text)

    def test_comparison_with_home_assistant(self) -> None:
        rounds = [_ok(17500, i) for i in range(1, 4)]
        same = " ".join(bench.conclusions(rounds, 20.0))
        slower = " ".join(bench.conclusions(rounds, 60.0))
        self.assertIn("gleichen Größenordnung", same)
        self.assertIn("deutlich langsamer", slower)
        self.assertIn("17,5", same)

    def test_always_states_which_adapter_was_used(self) -> None:
        self.assertIn("Adapter", bench.conclusions([_ok(1000)], None)[-1])

    def test_summary_lists_only_measured_phases(self) -> None:
        text = bench.format_summary([_ok(2000, i) for i in range(1, 4)], False, None, False)
        self.assertIn("Verbinden", text)
        self.assertNotIn("Scan ", text)


class InputTests(unittest.TestCase):
    def _args(self, *argv: str) -> object:
        return bench.build_parser().parse_args(["AA:BB:CC:DD:EE:FF", *argv])

    def test_defaults(self) -> None:
        args = self._args()
        self.assertEqual((args.rounds, args.pause, args.timeout), (5, 5.0, 60.0))
        self.assertIsNone(bench.validate(args))

    def test_unlock_needs_a_table(self) -> None:
        self.assertIn("--table", bench.validate(self._args("--unlock")))

    def test_rejects_nonsense_numbers(self) -> None:
        self.assertIsNotNone(bench.validate(self._args("--timeout", "0")))
        self.assertIsNotNone(bench.validate(self._args("--rounds", "-1")))
        self.assertIsNotNone(bench.validate(self._args("--ha-connect", "0")))

    def test_load_table(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.json"
            path.write_text(json.dumps({"table": {"7": "U1abcdefghijklm"}}), encoding="utf-8")
            self.assertEqual(bench.load_table(str(path)), {7: b"U1abcdefghijklm"})
            path.write_text(json.dumps({"table": {"7": "bad"}}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                bench.load_table(str(path))
            self.assertNotIn("bad", str(ctx.exception))
            path.write_text(json.dumps({"nothing": 1}), encoding="utf-8")
            with self.assertRaises(ValueError):
                bench.load_table(str(path))

    def test_exit_codes(self) -> None:
        args = self._args()
        args.out = None
        self.assertEqual(bench.finish(args, [_ok(1000)], False, False), 0)
        self.assertEqual(bench.finish(args, [_round(error="not_found")], False, False), 1)
        self.assertEqual(bench.finish(args, [_ok(1000)], False, True), 130)
        self.assertEqual(bench.finish(args, [], False, False), 0)


if __name__ == "__main__":
    unittest.main()


class _FakeBleakError(Exception):
    pass


class _FakeScanner:
    """Stands in for BleakScanner; ``seen`` is the device it reports (or ``None``)."""

    seen: object | None = None

    def __init__(self, callback: object) -> None:
        self._callback = callback

    async def __aenter__(self) -> _FakeScanner:
        if self.seen is not None:
            self._callback(self.seen, type("Adv", (), {"rssi": -71})())  # type: ignore[operator]
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeClient:
    """Stands in for BleakClient and answers the status request like the lock."""

    connect_error: Exception | None = None
    writes: list[bytes] = []

    def __init__(self, _target: object, timeout: float = 0) -> None:
        self._notify = None

    async def connect(self) -> None:
        if self.connect_error is not None:
            raise self.connect_error

    async def start_notify(self, _uuid: str, callback: object) -> None:
        self._notify = callback

    async def write_gatt_char(self, _uuid: str, data: bytes, response: bool = True) -> None:
        type(self).writes.append(bytes(data))
        if data == bench.BATTERY_REQUEST:
            self._notify(None, bytearray(b"\x55\x30\x07\x64"))  # type: ignore[misc]
        else:
            self._notify(None, bytearray(b"\x55\x31\x00\x00\x00"))  # type: ignore[misc]

    async def stop_notify(self, _uuid: str) -> None:
        return None

    async def disconnect(self) -> None:
        return None


class RoundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._saved = (bench.BleakClient, bench.BleakScanner, bench.BleakError)
        bench.BleakClient, bench.BleakScanner, bench.BleakError = (
            _FakeClient,
            _FakeScanner,
            _FakeBleakError,
        )
        _FakeScanner.seen = type("Dev", (), {"address": "AA:BB:CC:DD:EE:FF"})()
        _FakeClient.connect_error = None
        _FakeClient.writes = []
        self.progress = bench.Progress(io.StringIO(), enabled=False)

    def tearDown(self) -> None:
        bench.BleakClient, bench.BleakScanner, bench.BleakError = self._saved

    async def _run(self, **kwargs: object) -> bench.Round:
        options = {"timeout": 1.0, "direct": False, "table": None, "progress": self.progress}
        options.update(kwargs)
        return await bench.one_round(1, "aa:bb:cc:dd:ee:ff", **options)  # type: ignore[arg-type]

    async def test_status_only_round_never_writes_a_command(self) -> None:
        row = await self._run()
        self.assertTrue(row.ok)
        self.assertEqual((row.rssi, row.random_factor, row.battery), (-71, 7, 100))
        self.assertFalse(row.unlocked)
        self.assertEqual(_FakeClient.writes, [bench.BATTERY_REQUEST])
        self.assertIsNotNone(row.teardown_ms)

    async def test_direct_mode_has_no_scan_values(self) -> None:
        row = await self._run(direct=True)
        self.assertTrue(row.ok)
        self.assertIsNone(row.scan_ms)
        self.assertIsNone(row.rssi)

    async def test_lock_not_heard(self) -> None:
        _FakeScanner.seen = None
        row = await self._run(timeout=0.05)
        self.assertEqual(row.error, "not_found")
        self.assertIsNone(row.connect_ms)

    async def test_connect_failure_is_classified(self) -> None:
        _FakeClient.connect_error = _FakeBleakError("boom")
        row = await self._run()
        self.assertEqual(row.error, "connect_failed")
        self.assertIsNotNone(row.connect_ms)
        self.assertIsNone(row.status_ms)

    async def test_connect_timeout_is_classified(self) -> None:
        _FakeClient.connect_error = TimeoutError()
        row = await self._run()
        self.assertEqual(row.error, "connect_timeout")

    async def test_unlock_writes_the_table_command_and_reports_confirmation(self) -> None:
        command = b"U1abcdefghijklm"
        row = await self._run(table={7: command})
        self.assertTrue(row.unlocked)
        self.assertTrue(row.confirmed)
        self.assertEqual(_FakeClient.writes, [bench.BATTERY_REQUEST, command])

    async def test_unknown_challenge_sends_nothing(self) -> None:
        row = await self._run(table={8: b"U1abcdefghijklm"})
        self.assertEqual(row.error, "no_command")
        self.assertFalse(row.unlocked)
        self.assertEqual(_FakeClient.writes, [bench.BATTERY_REQUEST])
