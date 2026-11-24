"""Unit tests for the unlock statistics, cache discard and live option handling.

Home Assistant is stubbed the same way as in ``test_cache``; the ``Store`` is
replaced by an in-memory fake.
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from unittest.mock import MagicMock

for mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.bluetooth",
    "homeassistant.components.diagnostics",
    "homeassistant.exceptions",
    "voluptuous",
    "bleak",
    "bleak.exc",
    "bleak_retry_connector",
]:
    sys.modules.setdefault(mod, MagicMock())

from custom_components.welock_ble.ble import (  # noqa: E402
    ExchangeReport,
    _async_teardown,
    scanner_label,
)
from custom_components.welock_ble.cache import (  # noqa: E402
    CommandCache,
    parse_command_table,
)
from custom_components.welock_ble.const import (  # noqa: E402
    BLE_TIMEOUT,
    CONF_LOCAL_UNLOCK,
    CONFIRM_TIMEOUT,
    HISTORY_LIMIT,
    PATH_CLOUD,
    PATH_NONE,
    PATH_OFFLINE,
    RESULT_CONFIRMED,
    RESULT_FAILED,
    RESULT_UNCONFIRMED,
)
from custom_components.welock_ble.coordinator import (  # noqa: E402
    choose_unlock_command,
    options_change_is_live,
    static_options,
)
from custom_components.welock_ble.protocol import BatteryResponse  # noqa: E402
from custom_components.welock_ble.stats import UnlockAttempt, UnlockStats  # noqa: E402

CMD_RF7 = b"U1BOFHOIOFAAAAM"


class _FakeStore:
    """Minimal in-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self, data: dict | None = None) -> None:
        self.data = data
        self.removed = False

    async def async_load(self) -> dict | None:
        return self.data

    async def async_save(self, data: dict) -> None:
        self.data = data

    async def async_remove(self) -> None:
        self.data = None
        self.removed = True


def _stats(initial: dict | None = None) -> UnlockStats:
    stats = UnlockStats(MagicMock(), "entry-test")
    stats._store = _FakeStore(initial)
    return stats


def _attempt(path: str, result: str, ms: int = 1000, **kwargs) -> UnlockAttempt:
    return UnlockAttempt(
        time="2026-11-20T14:00:00+00:00", path=path, result=result, duration_ms=ms, **kwargs
    )


class UnlockStatsTests(unittest.TestCase):
    def test_counts_split_by_path_and_result(self) -> None:
        stats = _stats()
        stats.add(_attempt(PATH_OFFLINE, RESULT_CONFIRMED, 900))
        stats.add(_attempt(PATH_OFFLINE, RESULT_UNCONFIRMED, 1100))
        stats.add(_attempt(PATH_OFFLINE, RESULT_FAILED, 300))
        stats.add(_attempt(PATH_CLOUD, RESULT_CONFIRMED, 4000))
        offline = stats.paths[PATH_OFFLINE]
        self.assertEqual(
            (offline.attempts, offline.confirmed, offline.unconfirmed, offline.failed),
            (3, 1, 1, 1),
        )
        self.assertEqual(offline.delivered, 2)
        # Only delivered attempts count towards the average (failures are not timings).
        self.assertEqual(offline.average_duration_ms, 1000)
        self.assertEqual(stats.paths[PATH_CLOUD].delivered, 1)
        self.assertEqual(stats.paths[PATH_CLOUD].average_duration_ms, 4000)

    def test_average_is_none_without_delivered_attempts(self) -> None:
        stats = _stats()
        stats.add(_attempt(PATH_NONE, RESULT_FAILED))
        self.assertIsNone(stats.paths[PATH_NONE].average_duration_ms)
        self.assertEqual(stats.paths[PATH_NONE].failed, 1)

    def test_eviction_is_counted(self) -> None:
        stats = _stats()
        stats.add(_attempt(PATH_OFFLINE, RESULT_FAILED, evicted=True))
        stats.add(_attempt(PATH_OFFLINE, RESULT_FAILED))
        self.assertEqual(stats.evictions, 1)

    def test_history_is_capped_and_newest_first(self) -> None:
        stats = _stats()
        for index in range(HISTORY_LIMIT + 5):
            stats.add(_attempt(PATH_CLOUD, RESULT_CONFIRMED, index))
        self.assertEqual(len(stats.history), HISTORY_LIMIT)
        # Totals keep counting beyond the history window.
        self.assertEqual(stats.paths[PATH_CLOUD].attempts, HISTORY_LIMIT + 5)
        recent = stats.recent(3)
        self.assertEqual([item["duration_ms"] for item in recent], [104, 103, 102])
        self.assertEqual(stats.latest.duration_ms, HISTORY_LIMIT + 4)

    def test_save_and_load_roundtrip(self) -> None:
        stats = _stats()
        asyncio.run(
            stats.async_record(
                _attempt(PATH_OFFLINE, RESULT_CONFIRMED, 800, random_factor=7, rssi=-80)
            )
        )
        asyncio.run(
            stats.async_record(_attempt(PATH_CLOUD, RESULT_FAILED, 50, error="CannotConnect"))
        )
        saved = stats._store.data
        self.assertIsNotNone(saved)

        reloaded = _stats(saved)
        asyncio.run(reloaded.async_load())
        self.assertEqual(reloaded.paths[PATH_OFFLINE].confirmed, 1)
        self.assertEqual(reloaded.paths[PATH_CLOUD].failed, 1)
        self.assertEqual(len(reloaded.history), 2)
        self.assertEqual(reloaded.history[0].random_factor, 7)
        self.assertEqual(reloaded.history[0].rssi, -80)
        self.assertEqual(reloaded.history[1].error, "CannotConnect")

    def test_load_ignores_damaged_data(self) -> None:
        damaged = {
            "paths": {"cloud": {"attempts": -3, "confirmed": "x"}, "offline": "oops"},
            "evictions": True,
            "history": [
                "bad",
                {"time": 5, "path": "cloud", "result": "confirmed"},
                {"time": "t", "path": "mars", "result": "confirmed"},
                {"time": "t", "path": "cloud", "result": "confirmed", "random_factor": 999},
            ],
        }
        stats = _stats(damaged)
        asyncio.run(stats.async_load())
        self.assertEqual(stats.paths[PATH_CLOUD].attempts, 0)
        self.assertEqual(stats.paths[PATH_OFFLINE].attempts, 0)
        self.assertEqual(stats.evictions, 0)
        self.assertEqual(len(stats.history), 1)
        self.assertIsNone(stats.history[0].random_factor)

    def test_load_without_data_is_empty(self) -> None:
        stats = _stats(None)
        asyncio.run(stats.async_load())
        self.assertIsNone(stats.latest)
        self.assertEqual(stats.paths[PATH_CLOUD].attempts, 0)

    def test_clear_removes_storage(self) -> None:
        stats = _stats()
        stats.add(_attempt(PATH_CLOUD, RESULT_CONFIRMED))
        asyncio.run(stats.async_clear())
        self.assertTrue(stats._store.removed)
        self.assertEqual(stats.paths[PATH_CLOUD].attempts, 0)
        self.assertEqual(len(stats.history), 0)

    def test_stored_data_holds_no_secrets(self) -> None:
        stats = _stats()
        stats.add(_attempt(PATH_OFFLINE, RESULT_CONFIRMED, random_factor=7, error=None))
        text = str(stats.as_dict())
        self.assertNotIn(CMD_RF7.decode(), text)


class PhaseTimeTests(unittest.TestCase):
    def test_phase_times_survive_a_save_and_load(self) -> None:
        stats = _stats()
        asyncio.run(
            stats.async_record(
                _attempt(
                    PATH_CLOUD,
                    RESULT_CONFIRMED,
                    8000,
                    connect_ms=5200,
                    status_ms=700,
                    command_ms=1500,
                    confirm_ms=400,
                    teardown_ms=200,
                )
            )
        )
        reloaded = _stats(stats._store.data)
        asyncio.run(reloaded.async_load())
        latest = reloaded.latest
        self.assertEqual(
            (latest.connect_ms, latest.status_ms, latest.command_ms),
            (5200, 700, 1500),
        )
        self.assertEqual((latest.confirm_ms, latest.teardown_ms), (400, 200))

    def test_connection_diagnostics_survive_a_save_and_load(self) -> None:
        stats = _stats()
        asyncio.run(
            stats.async_record(
                _attempt(PATH_CLOUD, RESULT_CONFIRMED, 9000, adv_age_ms=1800, connect_attempts=2)
            )
        )
        reloaded = _stats(stats._store.data)
        asyncio.run(reloaded.async_load())
        self.assertEqual((reloaded.latest.adv_age_ms, reloaded.latest.connect_attempts), (1800, 2))

    def test_the_scanner_label_is_stored_and_a_foreign_value_is_dropped(self) -> None:
        label = scanner_label("AA:BB:CC:DD:EE:FF")
        self.assertRegex(label, r"^scanner-[0-9a-f]{8}$")
        self.assertNotIn("AA:BB", label)
        self.assertEqual(label, scanner_label("AA:BB:CC:DD:EE:FF"))
        self.assertNotEqual(label, scanner_label("AA:BB:CC:DD:EE:00"))
        self.assertIsNone(scanner_label(None))
        self.assertIsNone(scanner_label(""))
        stats = _stats()
        asyncio.run(stats.async_record(_attempt(PATH_CLOUD, RESULT_CONFIRMED, scanner=label)))
        data = stats._store.data
        reloaded = _stats(data)
        asyncio.run(reloaded.async_load())
        self.assertEqual(reloaded.latest.scanner, label)
        data["history"][0]["scanner"] = "AA:BB:CC:DD:EE:FF"  # not a label: ignored
        again = _stats(data)
        asyncio.run(again.async_load())
        self.assertIsNone(again.latest.scanner)

    def test_key_figures_come_from_what_is_recorded(self) -> None:
        stats = _stats()
        self.assertEqual(stats.key_figures()["unlock_attempts"], 0)
        self.assertIsNone(stats.key_figures()["success_rate"])
        self.assertIsNone(stats.key_figures()["connect_ms_median"])
        stats.add(_attempt(PATH_CLOUD, RESULT_CONFIRMED, 5000, connect_ms=4000, connect_attempts=1))
        stats.add(
            _attempt(PATH_OFFLINE, RESULT_UNCONFIRMED, 6000, connect_ms=9000, connect_attempts=2)
        )
        stats.add(
            _attempt(PATH_OFFLINE, RESULT_CONFIRMED, 7000, connect_ms=500, connect_attempts=1)
        )
        stats.add(
            _attempt(
                PATH_NONE, RESULT_FAILED, 300, error="WeLockBleError", scanner="scanner-0123abcd"
            )
        )
        figures = stats.key_figures()
        self.assertEqual(
            (figures["unlock_attempts"], figures["unlock_successes"], figures["unlock_failures"]),
            (4, 3, 1),
        )
        self.assertEqual(figures["unlock_confirmed"], 2)
        self.assertEqual(figures["success_rate"], 0.75)
        self.assertEqual((figures["connect_ms_median"], figures["connect_ms_max"]), (4000, 9000))
        self.assertEqual(figures["connect_attempts"], {"1": 2, "2": 1})
        self.assertEqual(figures["failures_by_error"], {"WeLockBleError": 1})
        self.assertEqual(figures["scanners"], {"scanner-0123abcd": 1})

    def test_attempts_without_phase_times_still_load(self) -> None:
        # Statistics written by rc.1/rc.2 have no phase times.
        old = {"history": [{"time": "t", "path": "cloud", "result": "confirmed", "duration_ms": 9}]}
        stats = _stats(old)
        asyncio.run(stats.async_load())
        self.assertEqual(len(stats.history), 1)
        self.assertIsNone(stats.history[0].connect_ms)

    def test_invalid_phase_times_are_ignored(self) -> None:
        bad = {
            "history": [
                {
                    "time": "t",
                    "path": "cloud",
                    "result": "failed",
                    "connect_ms": -5,
                    "status_ms": "x",
                }
            ]
        }
        stats = _stats(bad)
        asyncio.run(stats.async_load())
        self.assertIsNone(stats.history[0].connect_ms)
        self.assertIsNone(stats.history[0].status_ms)


class TimeoutTests(unittest.TestCase):
    def test_confirmation_wait_is_short(self) -> None:
        """The post-write wait must not stall the unlocked state like the 15 s status wait."""
        self.assertGreater(CONFIRM_TIMEOUT, 0)
        self.assertLessEqual(CONFIRM_TIMEOUT, 5)
        self.assertLess(CONFIRM_TIMEOUT, BLE_TIMEOUT)


class CacheDiscardTests(unittest.TestCase):
    def _cache(self) -> CommandCache:
        cache = CommandCache(MagicMock(), "entry-test")
        cache._store = _FakeStore()
        return cache

    def test_discard_removes_only_that_command(self) -> None:
        cache = self._cache()
        asyncio.run(cache.async_put(7, CMD_RF7))
        asyncio.run(cache.async_put(6, b"U1BMEGMHMEAAAAJ"))
        self.assertTrue(asyncio.run(cache.async_discard(7)))
        self.assertIsNone(cache.get(7))
        self.assertIsNotNone(cache.get(6))
        self.assertEqual(cache.count, 1)
        # The removal is persisted.
        self.assertEqual(list(cache._store.data["commands"]), [6])

    def test_discard_unknown_is_a_noop(self) -> None:
        cache = self._cache()
        self.assertFalse(asyncio.run(cache.async_discard(9)))
        self.assertIsNone(cache._store.data)


CMD_RF6 = "U1BMEGMHMEAAAAJ"
CMD_RF7_STR = "U1BOFHOIOFAAAAM"


def _table_file(**table) -> dict:
    return {"device_number": "22231059", "battery_used": 100, "table": table}


class ParseCommandTableTests(unittest.TestCase):
    def test_valid_file(self) -> None:
        device, table = parse_command_table(_table_file(**{"6": CMD_RF6, "7": CMD_RF7_STR}))
        self.assertEqual(device, "22231059")
        self.assertEqual(table, {6: CMD_RF6.encode(), 7: CMD_RF7_STR.encode()})

    def test_rejects_non_objects_and_missing_parts(self) -> None:
        for bad in (None, [], "x", {}, {"device_number": "1"}, {"table": {"1": CMD_RF6}}):
            with self.assertRaises(ValueError):
                parse_command_table(bad)
        with self.assertRaises(ValueError):
            parse_command_table({"device_number": " ", "table": {"1": CMD_RF6}})
        with self.assertRaises(ValueError):
            parse_command_table({"device_number": "1", "table": {}})

    def test_one_bad_entry_rejects_the_whole_file(self) -> None:
        for bad_value in ("U1SHORT", "X1BMEGMHMEAAAAJ", "U1BMEGMHMEAA-AJ", 5, None):
            with self.assertRaises(ValueError):
                parse_command_table(_table_file(**{"6": CMD_RF6, "7": bad_value}))

    def test_rejects_bad_challenge_numbers(self) -> None:
        for bad_key in ("256", "-1", "abc", ""):
            with self.assertRaises(ValueError):
                parse_command_table(_table_file(**{bad_key: CMD_RF6}))

    def test_error_text_never_echoes_keys_that_look_like_commands(self) -> None:
        # A table keyed by commands instead of challenge numbers (a mix-up) is rejected without
        # putting any of the commands into the message that is shown to the user.
        with self.assertRaises(ValueError) as caught:
            parse_command_table(_table_file(**{CMD_RF6: "6", CMD_RF7_STR: "7"}))
        message = str(caught.exception)
        self.assertNotIn(CMD_RF6[:6], message)
        self.assertNotIn(CMD_RF7_STR[:6], message)
        self.assertIn("2 invalid", message)

    def test_error_text_names_the_entry_but_never_a_command(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_command_table(_table_file(**{"6": CMD_RF6, "7": "U1BAD"}))
        message = str(caught.exception)
        self.assertIn("7", message)
        self.assertNotIn("U1BAD", message)
        self.assertNotIn(CMD_RF6, message)


class CacheImportTests(unittest.TestCase):
    def _cache(self) -> CommandCache:
        cache = CommandCache(MagicMock(), "entry-test")
        cache._store = _FakeStore()
        return cache

    def test_import_adds_new_commands_and_persists(self) -> None:
        cache = self._cache()
        result = asyncio.run(cache.async_import({6: CMD_RF6.encode(), 7: CMD_RF7}))
        self.assertEqual((result.added, result.unchanged, result.conflicts), (2, 0, []))
        self.assertEqual(cache.count, 2)
        self.assertEqual(cache.get(7), CMD_RF7)
        self.assertEqual(sorted(cache._store.data["commands"]), [6, 7])

    def test_import_is_idempotent(self) -> None:
        cache = self._cache()
        asyncio.run(cache.async_import({7: CMD_RF7}))
        result = asyncio.run(cache.async_import({7: CMD_RF7}))
        self.assertEqual((result.added, result.unchanged, result.conflicts), (0, 1, []))

    def test_import_never_overwrites_a_learned_command(self) -> None:
        cache = self._cache()
        asyncio.run(cache.async_put(7, CMD_RF7))
        other = b"U1ZZZZZZZZZZZZZ"
        result = asyncio.run(cache.async_import({7: other, 6: CMD_RF6.encode()}))
        self.assertEqual(result.conflicts, [7])
        self.assertEqual(result.added, 1)
        self.assertEqual(cache.get(7), CMD_RF7)  # the learned command stays

    def test_import_without_new_commands_does_not_write(self) -> None:
        cache = self._cache()
        asyncio.run(cache.async_put(7, CMD_RF7))
        cache._store.data = None
        asyncio.run(cache.async_import({7: CMD_RF7}))
        self.assertIsNone(cache._store.data)


class LiveOptionTests(unittest.TestCase):
    """The offline switch applies live; changing any other option reloads."""

    def test_static_options_ignore_the_switch(self) -> None:
        self.assertEqual(
            static_options({"scan_interval": 60, CONF_LOCAL_UNLOCK: True}),
            {"scan_interval": 60},
        )
        self.assertEqual(static_options({}), {})

    def test_switch_change_is_live(self) -> None:
        applied = static_options({"scan_interval": 60})
        self.assertTrue(
            options_change_is_live(applied, {"scan_interval": 60, CONF_LOCAL_UNLOCK: True})
        )
        self.assertTrue(options_change_is_live({}, {CONF_LOCAL_UNLOCK: False}))

    def test_other_option_change_needs_a_reload(self) -> None:
        applied = static_options({"scan_interval": 60})
        self.assertFalse(
            options_change_is_live(applied, {"scan_interval": 30, CONF_LOCAL_UNLOCK: True})
        )
        self.assertFalse(options_change_is_live({}, {"auto_relock_delay": 9}))


class BackgroundTeardownTests(unittest.TestCase):
    def test_teardown_stops_notifications_then_disconnects_and_times_itself(self) -> None:
        calls: list[str] = []

        class Client:
            async def stop_notify(self, _uuid: str) -> None:
                calls.append("stop_notify")

            async def disconnect(self) -> None:
                calls.append("disconnect")

        report = ExchangeReport()
        asyncio.run(_async_teardown(Client(), report))  # type: ignore[arg-type]
        self.assertEqual(calls, ["stop_notify", "disconnect"])
        self.assertIsNotNone(report.teardown_ms)

    def test_teardown_time_is_added_to_the_latest_attempt(self) -> None:
        stats = _stats()
        first = _attempt(PATH_CLOUD, RESULT_CONFIRMED, 8000)
        asyncio.run(stats.async_record(first))
        self.assertTrue(asyncio.run(stats.async_update_latest(first, teardown_ms=1900)))
        self.assertEqual(stats.latest.teardown_ms, 1900)
        self.assertEqual(stats.latest.duration_ms, 8000)
        reloaded = _stats(stats._store.data)
        asyncio.run(reloaded.async_load())
        self.assertEqual(reloaded.latest.teardown_ms, 1900)

    def test_a_newer_attempt_is_never_overwritten(self) -> None:
        stats = _stats()
        old = _attempt(PATH_CLOUD, RESULT_CONFIRMED, 8000)
        asyncio.run(stats.async_record(old))
        asyncio.run(stats.async_record(_attempt(PATH_OFFLINE, RESULT_CONFIRMED, 6000)))
        self.assertFalse(asyncio.run(stats.async_update_latest(old, teardown_ms=1)))
        self.assertIsNone(stats.latest.teardown_ms)


class ChooseUnlockCommandTests(unittest.TestCase):
    """Where the command for an unlock comes from: stored table or cloud."""

    STORED = b"U1BOFHOIOFAAAAM"
    FROM_CLOUD = b"U1CLOUDCMDXXXXX"
    STATE = BatteryResponse(random_factor=7, battery=100)

    def _cache(self, stored: bytes | None = None) -> CommandCache:
        cache = CommandCache(MagicMock(), "entry-test")
        cache._store = _FakeStore()
        if stored is not None:
            asyncio.run(cache.async_put(7, stored))
        return cache

    def _choose(self, cache: CommandCache, *, local_unlock: bool, cloud_error: bool = False):
        calls: list[int] = []

        async def request_cloud(state: BatteryResponse) -> bytes:
            calls.append(state.random_factor)
            if cloud_error:
                raise RuntimeError("cloud down")
            return self.FROM_CLOUD

        async def run():
            return await choose_unlock_command(
                local_unlock=local_unlock,
                cache=cache,
                request_cloud=request_cloud,
                state=self.STATE,
            )

        return run, calls

    def test_switch_on_and_stored_command_uses_it_without_the_cloud(self) -> None:
        run, calls = self._choose(self._cache(self.STORED), local_unlock=True)
        self.assertEqual(asyncio.run(run()), (PATH_OFFLINE, self.STORED))
        self.assertEqual(calls, [])

    def test_switch_off_never_uses_the_stored_command(self) -> None:
        cache = self._cache(self.STORED)
        run, calls = self._choose(cache, local_unlock=False)
        self.assertEqual(asyncio.run(run()), (PATH_CLOUD, self.FROM_CLOUD))
        self.assertEqual(calls, [7])

    def test_unknown_challenge_asks_the_cloud_and_learns_the_answer(self) -> None:
        cache = self._cache()
        run, calls = self._choose(cache, local_unlock=True)
        self.assertEqual(asyncio.run(run()), (PATH_CLOUD, self.FROM_CLOUD))
        self.assertEqual(calls, [7])
        self.assertEqual(cache.get(7), self.FROM_CLOUD)

    def test_switch_off_does_not_learn_the_cloud_answer(self) -> None:
        cache = self._cache()
        run, _ = self._choose(cache, local_unlock=False)
        asyncio.run(run())
        self.assertIsNone(cache.get(7))
        self.assertEqual(cache.count, 0)

    def test_damaged_stored_entry_falls_back_to_the_cloud(self) -> None:
        cache = self._cache()
        cache._map[7] = "not-a-command"
        run, calls = self._choose(cache, local_unlock=True)
        self.assertEqual(asyncio.run(run()), (PATH_CLOUD, self.FROM_CLOUD))
        self.assertEqual(calls, [7])

    def test_cloud_failure_is_raised_and_nothing_is_stored(self) -> None:
        cache = self._cache()
        run, _ = self._choose(cache, local_unlock=True, cloud_error=True)
        with self.assertRaises(RuntimeError):
            asyncio.run(run())
        self.assertIsNone(cache.get(7))

    def test_only_a_stored_command_for_this_exact_challenge_is_used(self) -> None:
        cache = self._cache()
        asyncio.run(cache.async_put(8, self.STORED))  # a command for another challenge
        run, calls = self._choose(cache, local_unlock=True)
        self.assertEqual(asyncio.run(run()), (PATH_CLOUD, self.FROM_CLOUD))
        self.assertEqual(calls, [7])


if __name__ == "__main__":
    unittest.main()
