"""Shared pytest configuration.

Tests marked ``live`` talk to the real WELOCK cloud. They are skipped unless
``WELOCK_LIVE_TEST=1`` is set and they never run in CI.
"""

from __future__ import annotations

import os

import pytest


def _live_skip_reason() -> str | None:
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return "Live-Test laeuft nie in CI."
    if os.environ.get("WELOCK_LIVE_TEST") != "1":
        return "Live-Test deaktiviert; zum Aktivieren WELOCK_LIVE_TEST=1 setzen."
    return None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    reason = _live_skip_reason()
    if reason is None:
        return
    marker = pytest.mark.skip(reason=reason)
    for item in items:
        if "live" in item.keywords:
            item.add_marker(marker)
