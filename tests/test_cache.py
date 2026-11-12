"""Unit tests for the learned-command cache (no network, no Home Assistant).

Home Assistant is stubbed the same way as in ``test_api``; the ``Store`` is
replaced by an in-memory fake so the cache logic can be tested in isolation.
"""

from __future__ import annotations

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
    "bleak",
    "bleak.exc",
    "bleak_retry_connector",
]:
    sys.modules.setdefault(mod, MagicMock())

from custom_components.welock.cache import CommandCache  # noqa: E402

# Real commands harvested from the test lock (randomFactor -> 15-byte U1 command).
CMD_RF7 = b"U1BOFHOIOFAAAAM"
CMD_RF6 = b"U1BMEGMHMEAAAAJ"


class _FakeStore:
    """Minimal in-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self) -> None:
        self.data: dict | None = None
        self.removed = False

    async def async_load(self) -> dict | None:
        return self.data

    async def async_save(self, data: dict) -> None:
        self.data = data

    async def async_remove(self) -> None:
        self.data = None
        self.removed = True


def _make_cache(initial: dict | None = None) -> CommandCache:
    cache = CommandCache(MagicMock(), "entry-test")
    store = _FakeStore()
    store.data = initial
    cache._store = store  # noqa: SLF001 - inject the fake store for testing
    return cache


class CommandCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_put_then_get_roundtrip(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        await cache.async_put(7, CMD_RF7)
        self.assertEqual(cache.get(7), CMD_RF7)
        self.assertIsNone(cache.get(6))
        self.assertEqual(cache.count, 1)

    async def test_put_persists_hex_to_store(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        await cache.async_put(7, CMD_RF7)
        self.assertEqual(cache._store.data, {"commands": {7: CMD_RF7.hex()}})  # noqa: SLF001

    async def test_put_is_noop_when_unchanged(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        await cache.async_put(7, CMD_RF7)
        cache._store.data = "sentinel"  # noqa: SLF001 - would be overwritten by a save
        await cache.async_put(7, CMD_RF7)
        self.assertEqual(cache._store.data, "sentinel")  # noqa: SLF001 - no second save

    async def test_put_rejects_invalid_command(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        await cache.async_put(7, b"not-a-command")
        await cache.async_put(300, CMD_RF7)  # randomFactor out of range
        self.assertEqual(cache.count, 0)

    async def test_load_filters_invalid_entries(self) -> None:
        cache = _make_cache({"commands": {"7": CMD_RF7.hex(), "6": "zz", "999": CMD_RF6.hex()}})
        await cache.async_load()
        self.assertEqual(cache.get(7), CMD_RF7)
        self.assertEqual(cache.count, 1)  # "zz" invalid, 999 out of range

    async def test_get_discards_corrupt_entry(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        cache._map[7] = "deadbeef"  # noqa: SLF001 - not a valid U1 command
        self.assertIsNone(cache.get(7))
        self.assertEqual(cache.count, 0)

    async def test_coverage_and_complete(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        for rf in range(128):
            await cache.async_put(rf, CMD_RF7)
        self.assertEqual(cache.coverage, 50)
        self.assertFalse(cache.complete)
        for rf in range(128, 256):
            await cache.async_put(rf, CMD_RF7)
        self.assertEqual(cache.count, 256)
        self.assertTrue(cache.complete)
        self.assertEqual(cache.coverage, 100)

    async def test_clear_removes_store(self) -> None:
        cache = _make_cache()
        await cache.async_load()
        await cache.async_put(7, CMD_RF7)
        await cache.async_clear()
        self.assertEqual(cache.count, 0)
        self.assertTrue(cache._store.removed)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
