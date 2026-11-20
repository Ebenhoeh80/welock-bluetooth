"""Repairs issues for a lock: unreachable, battery low, poor connection."""

from __future__ import annotations

import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .health import (
    BATTERY_LOW_PERCENT,
    UNREACHABLE_AFTER_S,
    QualityReport,
    battery_issue_active,
    poor_connection_issue_active,
    unreachable_issue_active,
)

ISSUE_UNREACHABLE = "lock_unreachable"
ISSUE_BATTERY = "battery_low"
ISSUE_POOR_CONNECTION = "poor_connection"
ALL_ISSUES = (ISSUE_UNREACHABLE, ISSUE_BATTERY, ISSUE_POOR_CONNECTION)


def issue_id(key: str, entry_id: str) -> str:
    """Return the repairs issue id of one issue type for one config entry."""
    return f"{key}_{entry_id}"


def clear_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Remove every issue of a config entry (when it is removed)."""
    for key in ALL_ISSUES:
        ir.async_delete_issue(hass, DOMAIN, issue_id(key, entry_id))


class WeLockIssues:
    """Raises and clears the repairs issues of one lock as its state changes.

    Issues are informational (not fixable from the repairs dialog) and clear themselves when the
    condition ends. Each one is created only when it appears and deleted when it ends.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str) -> None:
        """Initialize the issue tracker for one config entry."""
        self._hass = hass
        self._entry_id = entry_id
        self._name = name
        self._unreachable_since: float | None = None
        self._active: dict[str, bool] = dict.fromkeys(ALL_ISSUES, False)

    def _set(self, key: str, active: bool, placeholders: dict[str, str]) -> None:
        if active == self._active[key]:
            return
        self._active[key] = active
        if active:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                issue_id(key, self._entry_id),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=key,
                translation_placeholders={"name": self._name, **placeholders},
            )
        else:
            ir.async_delete_issue(self._hass, DOMAIN, issue_id(key, self._entry_id))

    def update_presence(self, present: bool, now: float | None = None) -> None:
        """Track how long the lock has been out of Bluetooth reach."""
        now = time.monotonic() if now is None else now
        if present:
            self._unreachable_since = None
        elif self._unreachable_since is None:
            self._unreachable_since = now
        since = None if self._unreachable_since is None else now - self._unreachable_since
        self._set(
            ISSUE_UNREACHABLE,
            unreachable_issue_active(since),
            {"hours": str(UNREACHABLE_AFTER_S // 3600)},
        )

    def update_battery(self, battery: int | None) -> None:
        """Raise the low-battery issue below the threshold; clear it with a margin."""
        self._set(
            ISSUE_BATTERY,
            battery_issue_active(battery, self._active[ISSUE_BATTERY]),
            {"percent": str(battery if battery is not None else BATTERY_LOW_PERCENT)},
        )

    def update_quality(self, report: QualityReport) -> None:
        """Tell the user when the Bluetooth connection is clearly poor."""
        median = "?" if report.median_connect_s is None else f"{report.median_connect_s:.0f}"
        self._set(
            ISSUE_POOR_CONNECTION,
            poor_connection_issue_active(report),
            {"seconds": median, "failures": str(report.failures)},
        )
