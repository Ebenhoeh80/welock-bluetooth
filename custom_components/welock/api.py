"""API client for WeLock Cloud Services."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime
import hashlib
import logging
import secrets
import time
from typing import Any
import uuid

import aiohttp

from .const import (
    BASE_API_URL,
    ENDPOINT_AUTH,
    ENDPOINT_DEVICES,
    ENDPOINT_UNLOCK,
)

_LOGGER = logging.getLogger(__name__)


def md5_hex(value: str) -> str:
    """Compute MD5 hash in hex format."""
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def request_signature(timestamp: str, device_id: str) -> str:
    """Compute double-MD5 reversed base64 request signature expected by WeLock Cloud."""
    encoded = base64.b64encode((device_id + timestamp)[::-1].encode("utf-8")).decode("ascii")
    return md5_hex(md5_hex(encoded))


def build_login_form(
    account: str, password: str, device_id: str, time_offset: int
) -> dict[str, str]:
    """Build form payload for WeLock cloud authentication."""
    acc = account.strip()
    return {
        "account": acc,
        "password": password,
        "timeOffset": str(time_offset),
        "platform": "ios",
        "model": "iPhone",
        "language": "en",
        "Jpushid": md5_hex(acc + "welockid-" + device_id),
        "isIot": "1",
    }


def build_request_headers(device_id: str, timestamp: str) -> dict[str, str]:
    """Build HTTP headers required by WeLock client API."""
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dart/3.7 (dart:io)",
        "identifierForVendor": device_id,
        "isPhysicalDevice": "true",
        "deviceModel": "iPhone",
        "operatingSystem": "ios",
        "appVersion": "4.5.2",
        "requestClientTimestamp": timestamp,
        "nonce": "".join(str(secrets.randbelow(10)) for _ in range(12)),
        "sign": request_signature(timestamp, device_id),
    }


class WeLockApiError(Exception):
    """General WeLock API exception."""


class CannotConnect(WeLockApiError):
    """Exception to indicate network connection error."""


class InvalidAuth(WeLockApiError):
    """Exception to indicate invalid credentials (email / password)."""


class LockUnavailable(WeLockApiError):
    """Exception to indicate that the lock or gateway is unreachable."""


class WeLockApiClient:
    """WeLock Cloud REST API Client."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
        base_url: str = BASE_API_URL,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize the API client."""
        user = username or client_id or ""
        pwd = password or client_secret or ""
        self._username = user.strip()
        self._password = pwd.strip()
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._device_id = str(uuid.uuid4()).upper()
        self._access_token: str | None = None
        self._login_data: dict[str, Any] | None = None

    @property
    def username(self) -> str:
        """Return the account username / email."""
        return self._username

    @property
    def client_id(self) -> str:
        """Return backward-compatible client_id alias."""
        return self._username

    def __repr__(self) -> str:
        """Return safe string representation redacting secrets."""
        is_auth = bool(self._access_token)
        return f"<WeLockApiClient account={self._username!r} authenticated={is_auth}>"

    async def async_authenticate(self) -> bool:
        """Authenticate with the WeLock Cloud API and acquire an access token."""
        if not self._username or not self._password:
            raise InvalidAuth("E-Mail-Adresse und Passwort dürfen nicht leer sein.")

        if self._session is None:
            raise CannotConnect("ClientSession is not available")

        offset = datetime.now().astimezone().utcoffset()
        time_offset = int(offset.total_seconds()) if offset else 0
        form = build_login_form(self._username, self._password, self._device_id, time_offset)
        timestamp = str(time.time_ns() // 1_000_000)
        headers = build_request_headers(self._device_id, timestamp)
        url = f"{self._base_url}{ENDPOINT_AUTH}"

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with self._session.post(
                url, data=form, headers=headers, timeout=timeout
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.error("WeLock authentication failed: HTTP %s", response.status)
                    raise InvalidAuth("Ungültige E-Mail-Adresse oder Passwort")

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("WeLock auth unexpected status %s: %s", response.status, text)
                    raise CannotConnect(f"Unexpected status: {response.status}")

                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise CannotConnect("Invalid response format from WeLock Cloud")

                code = data.get("code")
                if code != 0:
                    msg = data.get("msg") or data.get("message") or f"Auth failed (code {code})"
                    _LOGGER.error("WeLock auth response error: %s", msg)
                    raise InvalidAuth(msg)

                token_data = data.get("data")
                if not isinstance(token_data, dict):
                    raise InvalidAuth("No data field in authentication response")

                self._login_data = token_data
                token = token_data.get("access_token")
                if not isinstance(token, str) or not token:
                    raise InvalidAuth("No access_token found in response")

                self._access_token = token
                _LOGGER.info(
                    "Successfully authenticated with WeLock Cloud API for %s", self._username
                )
                return True

        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as err:
            _LOGGER.error("Connection error communicating with WeLock: %s", err)
            raise CannotConnect from err

    async def _post_cloud(self, path: str, form: dict[str, str]) -> dict[str, Any]:
        """Send an authenticated POST request to WeLock Cloud."""
        if not self._access_token:
            await self.async_authenticate()

        if self._session is None:
            raise CannotConnect("ClientSession is not available")

        timestamp = str(time.time_ns() // 1_000_000)
        headers = build_request_headers(self._device_id, timestamp)
        if self._access_token:
            headers["Authorization"] = self._access_token
        url = f"{self._base_url}{path}"

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with self._session.post(
                url, data=form, headers=headers, timeout=timeout
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.info("WeLock token expired, re-authenticating...")
                    await self.async_authenticate()
                    headers["Authorization"] = self._access_token or ""
                    async with self._session.post(
                        url, data=form, headers=headers, timeout=timeout
                    ) as retry_response:
                        if retry_response.status != 200:
                            raise WeLockApiError(f"HTTP {retry_response.status} on retry")
                        return await retry_response.json(content_type=None)

                if response.status != 200:
                    text = await response.text()
                    raise WeLockApiError(f"HTTP {response.status}: {text}")

                return await response.json(content_type=None)

        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as err:
            raise CannotConnect from err

    async def async_get_locks(self) -> list[dict[str, Any]]:
        """Retrieve the list of smart locks associated with this account."""
        resp = await self._post_cloud(ENDPOINT_DEVICES, {"pageSize": "40", "pageNo": "1"})
        data = resp.get("data")
        if not isinstance(data, list):
            return []

        locks: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            number = item.get("deviceNumber") or item.get("lockSn") or item.get("sn") or ""
            name = item.get("deviceName") or item.get("lockName") or f"WeLock {str(number)[-4:]}"

            ble_name = None
            ble_list = item.get("ble")
            if isinstance(ble_list, list) and ble_list and isinstance(ble_list[0], dict):
                ble_name = ble_list[0].get("deviceName")

            model = ble_name or item.get("model") or item.get("deviceType") or "Smart Lock"
            battery = item.get("battery", 100)
            status = item.get("status", 1)

            lock_entry: dict[str, Any] = {
                **item,
                "lockSn": str(number),
                "deviceNumber": str(number),
                "lockName": name,
                "deviceName": name,
                "model": model,
                "battery": battery,
                "status": status,
                "ble_name": ble_name,
            }
            locks.append(lock_entry)

        return locks

    async def async_get_lock_detail(self, lock_sn: str) -> dict[str, Any]:
        """Retrieve detailed lock status."""
        return {}

    async def async_unlock(self, lock_sn: str) -> bool:
        """Send unlock command via WeLock Cloud."""
        payload = {"deviceNumber": lock_sn, "lockSn": lock_sn}
        try:
            resp = await self._post_cloud(ENDPOINT_UNLOCK, payload)
            code = resp.get("code")
            if code in (0, 200, "0", "200"):
                _LOGGER.info("Unlock command accepted for lock %s", lock_sn)
                return True
            msg = resp.get("msg") or resp.get("message") or f"Unlock failed (code {code})"
            _LOGGER.error("WeLock unlock failed for %s: %s", lock_sn, msg)
            raise LockUnavailable(msg)
        except Exception as err:
            _LOGGER.error("Exception during unlock of %s: %s", lock_sn, err)
            raise LockUnavailable(str(err)) from err

    async def async_get_gateways(self) -> list[dict[str, Any]]:
        """Retrieve gateways connected to this account."""
        return []
