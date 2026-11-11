"""API client for WeLock Cloud Services."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    BASE_API_URL,
    ENDPOINT_AUTH,
    ENDPOINT_GATEWAY_LIST,
    ENDPOINT_LOCK_DETAIL,
    ENDPOINT_LOCK_LIST,
    ENDPOINT_UNLOCK,
)

_LOGGER = logging.getLogger(__name__)


class WeLockApiError(Exception):
    """General WeLock API exception."""


class CannotConnect(WeLockApiError):
    """Exception to indicate network connection error."""


class InvalidAuth(WeLockApiError):
    """Exception to indicate invalid credentials (client_id / client_secret)."""


class LockUnavailable(WeLockApiError):
    """Exception to indicate that the lock or gateway is unreachable."""


class WeLockApiClient:
    """WeLock Cloud REST API Client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession,
        base_url: str = BASE_API_URL,
    ) -> None:
        """Initialize the API client."""
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def client_id(self) -> str:
        """Return the client id."""
        return self._client_id

    def __repr__(self) -> str:
        """Return safe string representation redacting secrets."""
        is_auth = bool(self._access_token)
        return f"<WeLockApiClient client_id={self._client_id!r} authenticated={is_auth}>"

    async def async_authenticate(self) -> bool:
        """Authenticate with the WeLock Open Cloud API and acquire an access token."""
        url = f"{self._base_url}{ENDPOINT_AUTH}"
        payload = {
            "clientId": self._client_id,
            "clientSecret": self._client_secret,
            "grantType": "client_credentials",
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HomeAssistant-WeLock/1.3.0",
        }

        try:
            async with self._session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.error("WeLock authentication failed: HTTP %s", response.status)
                    raise InvalidAuth("Invalid Client ID or Client Secret")

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("WeLock auth unexpected status %s: %s", response.status, text)
                    raise CannotConnect(f"Unexpected status: {response.status}")

                data = await response.json(content_type=None)
                code = data.get("code")
                # WeLock APIs typically return code 200 or 0 on success
                has_token = "data" in data or "access_token" in data
                if code not in (200, 0, "200", "0") and not has_token:
                    msg = data.get("msg") or data.get("message") or "Unknown auth failure"
                    _LOGGER.error("WeLock auth response error: %s", msg)
                    raise InvalidAuth(msg)

                token_data = data.get("data") if isinstance(data.get("data"), dict) else data
                self._access_token = (
                    token_data.get("access_token")
                    or token_data.get("accessToken")
                    or token_data.get("token")
                )
                if not self._access_token:
                    raise InvalidAuth("No access token found in WeLock response")

                _LOGGER.debug("Successfully authenticated with WeLock Cloud API")
                return True

        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as err:
            _LOGGER.error("Connection error communicating with WeLock: %s", err)
            raise CannotConnect from err

    async def _request(
        self, method: str, endpoint: str, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make an authenticated request to WeLock Cloud."""
        if not self._access_token:
            await self.async_authenticate()

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": "HomeAssistant-WeLock/1.3.0",
        }

        try:
            req_timeout = aiohttp.ClientTimeout(total=20)
            async with self._session.request(
                method, url, json=json_data, headers=headers, timeout=req_timeout
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.info("WeLock token expired or unauthorized. Refreshing token...")
                    await self.async_authenticate()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with self._session.request(
                        method, url, json=json_data, headers=headers, timeout=req_timeout
                    ) as retry_response:
                        if retry_response.status != 200:
                            raise WeLockApiError(f"HTTP {retry_response.status} on retried request")
                        return await retry_response.json(content_type=None)

                if response.status != 200:
                    text = await response.text()
                    raise WeLockApiError(f"HTTP {response.status}: {text}")

                return await response.json(content_type=None)

        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as err:
            raise CannotConnect from err

    async def async_get_locks(self) -> list[dict[str, Any]]:
        """Retrieve the list of smart locks associated with this account."""
        resp = await self._request("POST", ENDPOINT_LOCK_LIST, {})
        data = resp.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "list" in data:
            return data["list"]
        return []

    async def async_get_lock_detail(self, lock_sn: str) -> dict[str, Any]:
        """Retrieve detailed lock information including battery and connectivity."""
        resp = await self._request("POST", ENDPOINT_LOCK_DETAIL, {"lockSn": lock_sn})
        data = resp.get("data")
        if isinstance(data, dict):
            return data
        return {}

    async def async_unlock(self, lock_sn: str) -> bool:
        """Send unlock command to the lock via the WeLock WiFiBox gateway."""
        payload = {"lockSn": lock_sn}
        resp = await self._request("POST", ENDPOINT_UNLOCK, payload)
        code = resp.get("code")
        if code in (200, 0, "200", "0"):
            _LOGGER.info("Unlock command sent successfully to lock %s", lock_sn)
            return True
        msg = resp.get("msg") or resp.get("message") or "Unlock command failed"
        _LOGGER.error("WeLock unlock failed for %s: %s", lock_sn, msg)
        raise LockUnavailable(msg)

    async def async_get_gateways(self) -> list[dict[str, Any]]:
        """Retrieve connected WiFiBox gateways."""
        try:
            resp = await self._request("POST", ENDPOINT_GATEWAY_LIST, {})
            data = resp.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "list" in data:
                return data["list"]
            return []
        except Exception as err:
            _LOGGER.debug("Could not fetch gateway list (optional feature): %s", err)
            return []
