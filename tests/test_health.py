"""Tests for the connection-quality and repairs rules (pure functions)."""

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
    "voluptuous",
    "bleak",
    "bleak.exc",
    "bleak_retry_connector",
]:
    sys.modules.setdefault(mod, MagicMock())

from custom_components.welock import health  # noqa: E402
from custom_components.welock import issues as issues_module  # noqa: E402
from custom_components.welock.issues import WeLockIssues  # noqa: E402
from custom_components.welock.stats import UnlockAttempt  # noqa: E402


def _attempt(connect_ms: int | None = 3000, result: str = "confirmed") -> UnlockAttempt:
    return UnlockAttempt(
        time="2026-11-20T10:00:00+00:00",
        path="offline",
        result=result,
        duration_ms=(connect_ms or 0) + 600,
        connect_ms=connect_ms,
    )


class ConnectionQualityTests(unittest.TestCase):
    def test_too_few_attempts_is_unknown(self) -> None:
        report = health.connection_quality([_attempt(), _attempt()], -70)
        self.assertEqual(report.level, health.QUALITY_UNKNOWN)

    def test_fast_connects_are_good(self) -> None:
        report = health.connection_quality([_attempt(3000)] * 5, -70)
        self.assertEqual(report.level, health.QUALITY_GOOD)
        self.assertEqual(report.median_connect_s, 3.0)
        self.assertEqual(report.suggestion, "none")

    def test_slow_median_is_fair_then_poor(self) -> None:
        fair = health.connection_quality([_attempt(8000)] * 5, -70)
        poor = health.connection_quality([_attempt(16000)] * 5, -70)
        self.assertEqual(fair.level, health.QUALITY_FAIR)
        self.assertEqual(poor.level, health.QUALITY_POOR)

    def test_one_failure_is_fair_two_are_poor(self) -> None:
        base = [_attempt(3000)] * 4
        one = base + [_attempt(None, "failed")]
        two = base + [_attempt(None, "failed")] * 2
        self.assertEqual(health.connection_quality(one, -70).level, health.QUALITY_FAIR)
        self.assertEqual(health.connection_quality(two, -70).level, health.QUALITY_POOR)

    def test_very_weak_signal_alone_is_fair(self) -> None:
        report = health.connection_quality([_attempt(3000)] * 5, -92)
        self.assertEqual(report.level, health.QUALITY_FAIR)

    def test_suggests_moving_closer_only_when_slow_and_weak(self) -> None:
        slow = [_attempt(16000)] * 5
        self.assertEqual(health.connection_quality(slow, -90).suggestion, "move_closer")
        self.assertEqual(health.connection_quality(slow, -60).suggestion, "none")
        self.assertEqual(health.connection_quality([_attempt(3000)] * 5, -87).suggestion, "none")
        self.assertEqual(
            health.connection_quality([_attempt(3000)] * 5, -95).suggestion, "move_closer"
        )

    def test_only_the_latest_attempts_count(self) -> None:
        old_bad = [_attempt(None, "failed")] * 10
        recent_good = [_attempt(3000)] * health.SAMPLE_SIZE
        report = health.connection_quality(old_bad + recent_good, -70)
        self.assertEqual(report.level, health.QUALITY_GOOD)
        self.assertEqual(report.sample, health.SAMPLE_SIZE)

    def test_real_measurements(self) -> None:
        # Dongle 50 cm away: connecting took 4 to 31 s (median 10.5 s) -> fair.
        times = [4000, 12000, 31000, 9000, 6000, 17000, 8000, 5000, 19000, 14000]
        report = health.connection_quality([_attempt(t) for t in times], -86)
        self.assertEqual(report.level, health.QUALITY_FAIR)
        self.assertEqual(report.suggestion, "move_closer")


class RepairRuleTests(unittest.TestCase):
    def test_battery_issue_has_hysteresis(self) -> None:
        self.assertFalse(health.battery_issue_active(25, False))
        self.assertTrue(health.battery_issue_active(19, False))
        self.assertTrue(health.battery_issue_active(22, True))  # still shown until 25 %
        self.assertFalse(health.battery_issue_active(25, True))

    def test_unknown_battery_keeps_the_current_state(self) -> None:
        self.assertTrue(health.battery_issue_active(None, True))
        self.assertFalse(health.battery_issue_active(None, False))

    def test_unreachable_after_six_hours(self) -> None:
        self.assertFalse(health.unreachable_issue_active(None))
        self.assertFalse(health.unreachable_issue_active(5 * 3600))
        self.assertTrue(health.unreachable_issue_active(6 * 3600))

    def test_poor_connection_needs_enough_data(self) -> None:
        few = health.QualityReport(health.QUALITY_POOR, 3, 2, 16.0, "none")
        enough = health.QualityReport(health.QUALITY_POOR, 6, 2, 16.0, "none")
        fair = health.QualityReport(health.QUALITY_FAIR, 8, 1, 8.0, "none")
        self.assertFalse(health.poor_connection_issue_active(few))
        self.assertTrue(health.poor_connection_issue_active(enough))
        self.assertFalse(health.poor_connection_issue_active(fair))


class IssueTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = MagicMock()
        self._saved = issues_module.ir
        issues_module.ir = self.ir
        self.tracker = WeLockIssues(MagicMock(), "entry1", "Front door")

    def tearDown(self) -> None:
        issues_module.ir = self._saved

    def test_unreachable_issue_appears_after_six_hours_and_clears_in_range(self) -> None:
        self.tracker.update_presence(False, now=0)
        self.ir.async_create_issue.assert_not_called()
        self.tracker.update_presence(False, now=6 * 3600 + 1)
        self.assertEqual(self.ir.async_create_issue.call_count, 1)
        self.tracker.update_presence(False, now=7 * 3600)  # not created twice
        self.assertEqual(self.ir.async_create_issue.call_count, 1)
        self.tracker.update_presence(True, now=8 * 3600)
        self.assertEqual(self.ir.async_delete_issue.call_count, 1)

    def test_battery_issue_follows_the_rule(self) -> None:
        self.tracker.update_battery(80)
        self.ir.async_create_issue.assert_not_called()
        self.tracker.update_battery(15)
        self.assertEqual(self.ir.async_create_issue.call_count, 1)
        self.tracker.update_battery(23)  # between the thresholds: stays
        self.ir.async_delete_issue.assert_not_called()
        self.tracker.update_battery(90)
        self.assertEqual(self.ir.async_delete_issue.call_count, 1)

    def test_issue_ids_belong_to_the_entry(self) -> None:
        self.assertEqual(issues_module.issue_id("battery_low", "abc"), "battery_low_abc")


if __name__ == "__main__":
    unittest.main()
