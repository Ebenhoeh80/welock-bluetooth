"""Unit tests for WeLockApiClient."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock

# Mock homeassistant modules so tests can run without homeassistant core installed
for mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.diagnostics",
]:
    sys.modules.setdefault(mod, MagicMock())

try:
    from custom_components.welock.api import (  # noqa: E402
        CannotConnect,
        InvalidAuth,
        LockUnavailable,
        WeLockApiClient,
        WeLockApiError,
    )

    HAVE_API = True
except ImportError:
    HAVE_API = False


class TestWeLockApiClient(unittest.TestCase):
    """Test API client behaviors."""

    def test_custom_exceptions_inheritance(self) -> None:
        """Verify custom exceptions inherit from WeLockApiError."""
        if not HAVE_API:
            self.skipTest("API client dependencies not available")
        self.assertTrue(issubclass(InvalidAuth, WeLockApiError))
        self.assertTrue(issubclass(CannotConnect, WeLockApiError))
        self.assertTrue(issubclass(LockUnavailable, WeLockApiError))

    def test_repr_masks_secrets(self) -> None:
        """Verify __repr__ does not expose client_secret."""
        if not HAVE_API:
            self.skipTest("API client dependencies not available")
        client = WeLockApiClient(
            client_id="demo_user_123",
            client_secret="SUPER_SECRET_VALUE",
            session=None,  # type: ignore[arg-type]
        )
        repr_str = repr(client)
        self.assertIn("demo_user_123", repr_str)
        self.assertNotIn("SUPER_SECRET_VALUE", repr_str)


if __name__ == "__main__":
    unittest.main()
