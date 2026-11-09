"""Unit tests for WeLockApiClient."""
import unittest

try:
    import aiohttp
    from custom_components.welock.api import (
        WeLockApiClient,
        InvalidAuth,
        CannotConnect,
        LockUnavailable,
        WeLockApiError,
    )
    HAVE_AIOHTTP = True
except ImportError:
    HAVE_AIOHTTP = False


class TestWeLockApiClient(unittest.TestCase):
    """Test API client behaviors."""

    def test_custom_exceptions_inheritance(self) -> None:
        """Verify custom exceptions inherit from WeLockApiError."""
        if not HAVE_AIOHTTP:
            self.skipTest("aiohttp is not installed in current environment")
        self.assertTrue(issubclass(InvalidAuth, WeLockApiError))
        self.assertTrue(issubclass(CannotConnect, WeLockApiError))
        self.assertTrue(issubclass(LockUnavailable, WeLockApiError))

    def test_repr_masks_secrets(self) -> None:
        """Verify __repr__ does not expose client_secret."""
        if not HAVE_AIOHTTP:
            self.skipTest("aiohttp is not installed in current environment")
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
