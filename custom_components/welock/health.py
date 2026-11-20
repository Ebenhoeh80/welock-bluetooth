"""Connection quality and health rules (pure functions, no Home Assistant imports)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from .stats import UnlockAttempt

QUALITY_UNKNOWN = "unknown"
QUALITY_GOOD = "good"
QUALITY_FAIR = "fair"
QUALITY_POOR = "poor"
QUALITIES = (QUALITY_UNKNOWN, QUALITY_GOOD, QUALITY_FAIR, QUALITY_POOR)

# How many of the latest unlock attempts are looked at, and how many are needed to say anything.
SAMPLE_SIZE = 10
MIN_SAMPLE = 3

# Thresholds in seconds / dBm. They are guides, not guarantees: the lock advertises only about
# every 3 s, so even a perfect link needs a few seconds to connect.
POOR_MEDIAN_CONNECT_S = 15.0
FAIR_MEDIAN_CONNECT_S = 6.0
POOR_FAILURES = 2
WEAK_RSSI = -85  # at or below this the adapter hears the lock badly
VERY_WEAK_RSSI = -90

# Repairs.
BATTERY_LOW_PERCENT = 20
BATTERY_RECOVERED_PERCENT = 25  # hysteresis: the issue clears only above this
UNREACHABLE_AFTER_S = 6 * 3600
POOR_QUALITY_MIN_SAMPLE = 5  # do not raise the "poor connection" issue on a handful of attempts


@dataclass(frozen=True)
class QualityReport:
    """Result of ``connection_quality``."""

    level: str
    sample: int
    failures: int
    median_connect_s: float | None
    suggestion: str  # "move_closer" or "none"


def connection_quality(attempts: Sequence[UnlockAttempt], rssi: int | None) -> QualityReport:
    """Rate how well Home Assistant reaches the lock from its recent unlock attempts."""
    recent = list(attempts)[-SAMPLE_SIZE:]
    failures = sum(1 for a in recent if a.result == "failed")
    connects = [a.connect_ms for a in recent if a.connect_ms is not None]
    median_s = statistics.median(connects) / 1000 if connects else None
    weak = rssi is not None and rssi <= WEAK_RSSI

    if len(recent) < MIN_SAMPLE:
        return QualityReport(QUALITY_UNKNOWN, len(recent), failures, median_s, "none")

    if failures >= POOR_FAILURES or (median_s is not None and median_s >= POOR_MEDIAN_CONNECT_S):
        level = QUALITY_POOR
    elif (
        failures >= 1
        or (median_s is not None and median_s >= FAIR_MEDIAN_CONNECT_S)
        or (rssi is not None and rssi <= VERY_WEAK_RSSI)
    ):
        level = QUALITY_FAIR
    else:
        level = QUALITY_GOOD
    suggestion = "move_closer" if level in (QUALITY_FAIR, QUALITY_POOR) and weak else "none"
    return QualityReport(level, len(recent), failures, median_s, suggestion)


def battery_issue_active(battery: int | None, currently_active: bool) -> bool:
    """Whether the low-battery issue should be shown (with hysteresis against flapping)."""
    if battery is None:
        return currently_active
    if currently_active:
        return battery < BATTERY_RECOVERED_PERCENT
    return battery < BATTERY_LOW_PERCENT


def unreachable_issue_active(unreachable_for_s: float | None) -> bool:
    """Whether the lock has been out of Bluetooth reach long enough to raise an issue."""
    return unreachable_for_s is not None and unreachable_for_s >= UNREACHABLE_AFTER_S


def poor_connection_issue_active(report: QualityReport) -> bool:
    """Whether to tell the user that the connection is poor (enough data, clearly poor)."""
    return report.level == QUALITY_POOR and report.sample >= POOR_QUALITY_MIN_SAMPLE
