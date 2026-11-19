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

from custom_components.welock.cache import CommandCache  # noqa: E402
from custom_components.welock.const import (  # noqa: E402
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
from custom_components.welock.coordinator import (  # noqa: E402
    options_change_is_live,
    static_options,
)
from custom_components.welock.stats import UnlockAttempt, UnlockStats  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
