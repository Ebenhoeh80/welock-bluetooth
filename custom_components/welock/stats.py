"""Persistent unlock statistics and history (cloud path vs. offline path).

Every unlock attempt made through Home Assistant is recorded with the way the
unlock command was obtained (``cloud`` or ``offline``), what happened and how
long it took. The totals and the last attempts survive restarts. Nothing secret
is stored: no commands, no account data, no addresses.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, deque
from dataclasses import asdict, dataclass, field, replace
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    HISTORY_LIMIT,
    PATH_CLOUD,
    PATH_NONE,
    PATH_OFFLINE,
    RESULT_CONFIRMED,
    RESULT_FAILED,
    RESULT_UNCONFIRMED,
    STATS_STORAGE_VERSION,
)

PATHS = (PATH_CLOUD, PATH_OFFLINE, PATH_NONE)
RESULTS = (RESULT_CONFIRMED, RESULT_UNCONFIRMED, RESULT_FAILED)


def _storage_key(entry_id: str) -> str:
    """Return the HA storage key for one config entry's statistics."""
    return f"{DOMAIN}.{entry_id}.stats"


@dataclass(frozen=True)
class UnlockAttempt:
    """One unlock attempt."""

    time: str  # ISO 8601, UTC
    path: str  # cloud | offline | none
    result: str  # confirmed | unconfirmed | failed
    duration_ms: int
    random_factor: int | None = None
    error: str | None = None  # exception class name only, never a message
    rssi: int | None = None
    evicted: bool = False  # offline command was dropped from the cache afterwards
    # Where the time went, in milliseconds (``None`` = phase not reached).
    connect_ms: int | None = None
    status_ms: int | None = None
    command_ms: int | None = None
    confirm_ms: int | None = None
    teardown_ms: int | None = None
    # State when the connection was started (see ``ExchangeReport``).
    adv_age_ms: int | None = None
    connect_attempts: int | None = None
    # Neutral label of the adapter or proxy that last heard the lock (see ``ble.scanner_label``).
    scanner: str | None = None


class PhaseTimes(TypedDict):
    """The per-phase times of an exchange, as stored in an ``UnlockAttempt``."""

    connect_ms: int | None
    status_ms: int | None
    command_ms: int | None
    confirm_ms: int | None
    teardown_ms: int | None
    adv_age_ms: int | None
    connect_attempts: int | None
    scanner: str | None


@dataclass
class PathStats:
    """Totals for one path."""

    attempts: int = 0
    confirmed: int = 0
    unconfirmed: int = 0
    failed: int = 0
    duration_total_ms: int = 0  # over delivered (confirmed + unconfirmed) attempts

    @property
    def delivered(self) -> int:
        """Attempts in which the command was written to the lock."""
        return self.confirmed + self.unconfirmed

    @property
    def average_duration_ms(self) -> int | None:
        """Average duration of delivered attempts, or ``None`` without any."""
        return round(self.duration_total_ms / self.delivered) if self.delivered else None

    def as_attributes(self) -> dict[str, Any]:
        """Return the totals as sensor attributes."""
        return {
            "attempts": self.attempts,
            "delivered": self.delivered,
            "confirmed": self.confirmed,
            "unconfirmed": self.unconfirmed,
            "failed": self.failed,
            "average_duration_ms": self.average_duration_ms,
        }


_SCANNER_LABEL = re.compile(r"scanner-[0-9a-f]{8}")

PHASE_KEYS = (
    "connect_ms",
    "status_ms",
    "command_ms",
    "confirm_ms",
    "teardown_ms",
    "adv_age_ms",
    "connect_attempts",
)


def _valid_int(value: object, minimum: int | None = None, maximum: int | None = None) -> int | None:
    """Return ``value`` if it is a real integer (not a bool) within the bounds, else ``None``."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        return None
    return value


def _optional_ms(value: object) -> int | None:
    """Return a stored phase time, or ``None`` if it is missing or not a valid time."""
    return _valid_int(value, minimum=0)


def _scanner(value: object) -> str | None:
    """Return a stored scanner label, or ``None`` if it is not one."""
    return value if isinstance(value, str) and _SCANNER_LABEL.fullmatch(value) else None


def _non_negative_int(value: object) -> int:
    return _valid_int(value, minimum=0) or 0


def _attempt_from_dict(item: object) -> UnlockAttempt | None:
    """Rebuild one attempt from stored data; ``None`` if it is not well-formed."""
    if not isinstance(item, dict):
        return None
    time = item.get("time")
    path = item.get("path")
    result = item.get("result")
    if not isinstance(time, str) or path not in PATHS or result not in RESULTS:
        return None
    error = item.get("error")
    return UnlockAttempt(
        time=time,
        path=path,
        result=result,
        duration_ms=_non_negative_int(item.get("duration_ms")),
        random_factor=_valid_int(item.get("random_factor"), minimum=0, maximum=255),
        error=error if isinstance(error, str) else None,
        rssi=_valid_int(item.get("rssi")),
        evicted=item.get("evicted") is True,
        scanner=_scanner(item.get("scanner")),
        **{key: _optional_ms(item.get(key)) for key in PHASE_KEYS},
    )


@dataclass
class UnlockStats:
    """Totals per path plus the most recent attempts, backed by HA storage."""

    hass: HomeAssistant
    entry_id: str
    paths: dict[str, PathStats] = field(init=False)
    history: deque[UnlockAttempt] = field(init=False)
    evictions: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        """Create the store and empty totals."""
        self._store: Store = Store(self.hass, STATS_STORAGE_VERSION, _storage_key(self.entry_id))
        self._reset()

    def _reset(self) -> None:
        self.paths = {path: PathStats() for path in PATHS}
        self.history = deque(maxlen=HISTORY_LIMIT)
        self.evictions = 0

    async def async_load(self) -> None:
        """Load the persisted statistics; damaged parts are ignored."""
        self._reset()
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return
        stored_paths = data.get("paths")
        if isinstance(stored_paths, dict):
            for path in PATHS:
                item = stored_paths.get(path)
                if isinstance(item, dict):
                    self.paths[path] = PathStats(
                        attempts=_non_negative_int(item.get("attempts")),
                        confirmed=_non_negative_int(item.get("confirmed")),
                        unconfirmed=_non_negative_int(item.get("unconfirmed")),
                        failed=_non_negative_int(item.get("failed")),
                        duration_total_ms=_non_negative_int(item.get("duration_total_ms")),
                    )
        self.evictions = _non_negative_int(data.get("evictions"))
        for item in data.get("history") or []:
            attempt = _attempt_from_dict(item)
            if attempt is not None:
                self.history.append(attempt)

    def as_dict(self) -> dict[str, Any]:
        """Return everything as plain data (storage format and diagnostics)."""
        return {
            "paths": {path: asdict(stats) for path, stats in self.paths.items()},
            "evictions": self.evictions,
            "history": [asdict(attempt) for attempt in self.history],
        }

    def add(self, attempt: UnlockAttempt) -> None:
        """Count one attempt and append it to the history (no I/O)."""
        stats = self.paths.get(attempt.path) or self.paths[PATH_NONE]
        stats.attempts += 1
        if attempt.result == RESULT_CONFIRMED:
            stats.confirmed += 1
        elif attempt.result == RESULT_UNCONFIRMED:
            stats.unconfirmed += 1
        else:
            stats.failed += 1
        if attempt.result in (RESULT_CONFIRMED, RESULT_UNCONFIRMED):
            stats.duration_total_ms += max(attempt.duration_ms, 0)
        if attempt.evicted:
            self.evictions += 1
        self.history.append(attempt)

    def key_figures(self) -> dict[str, Any]:
        """Return key figures from what is already recorded (no new measurement).

        The totals cover all attempts since the statistics were last cleared; the
        connection figures cover the kept history (the latest ``HISTORY_LIMIT``
        attempts). Nothing in it identifies the lock, the account or a scanner.
        """
        totals = list(self.paths.values())
        attempts = sum(p.attempts for p in totals)
        delivered = sum(p.delivered for p in totals)
        connects = [a.connect_ms for a in self.history if a.connect_ms is not None]
        tries = Counter(a.connect_attempts for a in self.history if a.connect_attempts is not None)
        return {
            "unlock_attempts": attempts,
            "unlock_successes": delivered,
            "unlock_confirmed": sum(p.confirmed for p in totals),
            "unlock_failures": sum(p.failed for p in totals),
            "success_rate": round(delivered / attempts, 3) if attempts else None,
            "history_size": len(self.history),
            "connect_ms_median": round(statistics.median(connects)) if connects else None,
            "connect_ms_max": max(connects) if connects else None,
            "connect_attempts": {str(n): count for n, count in sorted(tries.items())},
            "failures_by_error": dict(
                Counter(a.error or "unknown" for a in self.history if a.result == RESULT_FAILED)
            ),
            "scanners": dict(Counter(a.scanner for a in self.history if a.scanner)),
        }

    async def async_record(self, attempt: UnlockAttempt) -> None:
        """Count one attempt and persist the statistics."""
        self.add(attempt)
        await self._store.async_save(self.as_dict())

    async def async_update_latest(self, expected: UnlockAttempt, **changes: Any) -> bool:
        """Change fields of the newest attempt if it is still ``expected``; persist it.

        Used to add the teardown time once the connection has been closed in the
        background. Returns ``False`` if a newer attempt has been recorded since.
        """
        if not self.history or self.history[-1] is not expected:
            return False
        self.history[-1] = replace(expected, **changes)
        await self._store.async_save(self.as_dict())
        return True

    async def async_clear(self) -> None:
        """Forget all statistics and remove the stored file."""
        self._reset()
        await self._store.async_remove()

    @property
    def latest(self) -> UnlockAttempt | None:
        """Return the most recent attempt, if any."""
        return self.history[-1] if self.history else None

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the newest attempts first, as plain dicts."""
        return [asdict(attempt) for attempt in list(self.history)[-limit:][::-1]]
