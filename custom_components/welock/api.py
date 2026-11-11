"""API client for the WeLock mobile cloud (clientapi.welock.com.cn).

The cloud is only used for two things:
- listing the locks / BLE modules of the account (during setup and reauth),
- turning a fresh BLE challenge into a one-time 15-byte unlock command.

Every login ends other sessions of the account (e.g. the WeLock app), so the
client never polls; it logs in only when one of the two calls above is needed.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp

from .const import BASE_API_URL, ENDPOINT_AUTH, ENDPOINT_DEVICES, ENDPOINT_UNLOCK
from .protocol import format_mac

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=20)


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
    """Network, TLS or timeout error."""


class InvalidAuth(WeLockApiError):
    """Invalid credentials (email / password)."""


class LockUnavailable(WeLockApiError):
    """The cloud refused to issue an unlock command."""


@dataclass(frozen=True)
class WeLockBleModule:
    """A BLE module of a lock as listed by the cloud (``ble[]`` entry)."""

    name: str  # ble[].deviceName, e.g. "WeLockABCDE" - required for /Command/UnLock
    address: str | None  # ble[].deviceMac formatted as AA:BB:CC:DD:EE:FF
    battery: int | None  # ble[].power
    position: int | None


@dataclass(frozen=True)
class WeLockDevice:
    """A lock as listed by ``/Device/GetDevices``."""

    device_number: str
    name: str
    model: str | None
    ble: tuple[WeLockBleModule, ...] = field(default_factory=tuple)


def parse_envelope(payload: Any) -> Any:
    """Return ``data`` of a ``{"code": 0, "data": ...}`` envelope or raise."""
    if not isinstance(payload, dict) or type(payload.get("code")) is not int:
        raise WeLockApiError("Invalid response format from WeLock Cloud")
    if payload["code"] != 0:
        # Do not include the message text: it is not needed and may echo request data.
        raise WeLockApiError(f"WeLock Cloud rejected the request (code {payload['code']})")
    if "data" not in payload:
        raise WeLockApiError("WeLock Cloud response has no data field")
    return payload["data"]


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_device_list(data: Any) -> list[WeLockDevice]:
    """Parse the ``data`` list of ``/Device/GetDevices``."""
    if not isinstance(data, list):
        raise WeLockApiError("Device list has an unknown format")
    devices: list[WeLockDevice] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        number = item.get("deviceNumber")
        if not isinstance(number, str) or not number.strip():
            continue
        modules: list[WeLockBleModule] = []
        for entry in item.get("ble") or []:
            if not isinstance(entry, dict):
                continue
            ble_name = entry.get("deviceName")
            if not isinstance(ble_name, str) or not ble_name.strip():
                continue
            modules.append(
                WeLockBleModule(
                    name=ble_name.strip(),
                    address=format_mac(str(entry.get("deviceMac") or "")),
                    battery=_as_int(entry.get("power")),
                    position=_as_int(entry.get("position")),
                )
            )
        name = item.get("deviceName")
        devices.append(
            WeLockDevice(
                device_number=number.strip(),
                name=name.strip() if isinstance(name, str) and name.strip() else number.strip(),
                model=item.get("model") if isinstance(item.get("model"), str) else None,
                ble=tuple(modules),
            )
        )
    return devices


def parse_unlock_command(data: Any) -> bytes:
    """Turn the ``data`` of ``/Command/UnLock`` into the raw command bytes."""
    if not isinstance(data, dict):
        raise LockUnavailable("Unlock command response has an unknown format")
    command = data.get("command")
    if not isinstance(command, str) or not command or len(command) % 2:
        raise LockUnavailable("Unlock command is not a valid hex string")
    try:
        return bytes.fromhex(command)
    except ValueError as err:
        raise LockUnavailable("Unlock command is not a valid hex string") from err


class WeLockApiClient:
    """WeLock mobile cloud client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None,
        base_url: str = BASE_API_URL,
    ) -> None:
        """Initialize the API client."""
        self._username = (username or "").strip()
        self._password = password or ""  # never strip: spaces may be part of it
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._device_id = str(uuid.uuid4()).upper()
        self._access_token: str | None = None

    @property
    def username(self) -> str:
        """Return the account username / email."""
        return self._username

    def __repr__(self) -> str:
        """Return safe string representation redacting secrets."""
        return (
            f"<WeLockApiClient account={self._username!r} "
            f"authenticated={bool(self._access_token)}>"
        )

    async def _post(
        self, path: str, form: dict[str, str], token: str | None = None
    ) -> tuple[int, Any]:
        if self._session is None:
            raise CannotConnect("ClientSession is not available")
        headers = build_request_headers(self._device_id, str(time.time_ns() // 1_000_000))
        if token:
            headers["Authorization"] = token
        try:
            async with self._session.post(
                f"{self._base_url}{path}",
                data=form,
                headers=headers,
                timeout=_TIMEOUT,
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    return response.status, None
                return 200, await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect("Connection to WeLock Cloud failed") from err
        except ValueError as err:
            raise CannotConnect("WeLock Cloud returned invalid JSON") from err

    async def async_authenticate(self) -> None:
        """Log in and keep the access token in memory only."""
        if not self._username or not self._password:
            raise InvalidAuth("Email and password must not be empty")
        offset = datetime.now().astimezone().utcoffset()
        time_offset = int(offset.total_seconds()) if offset else 0
        self._access_token = None
        status, payload = await self._post(
            ENDPOINT_AUTH,
            build_login_form(self._username, self._password, self._device_id, time_offset),
        )
        if status in (401, 403):
            raise InvalidAuth("Invalid email or password")
        if status != 200:
            raise CannotConnect(f"Unexpected HTTP status {status} during login")
        try:
            data = parse_envelope(payload)
        except WeLockApiError as err:
            raise InvalidAuth(str(err)) from None
        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token:
            raise InvalidAuth("No access_token in login response")
        self._access_token = token
        _LOGGER.debug("Logged in to WeLock Cloud as %s", self._username)

    async def _authorized(self, path: str, form: dict[str, str]) -> Any:
        """Log in, send one request and drop the token again.

        The token is treated as single-use: any app login invalidates it anyway.
        """
        await self.async_authenticate()
        try:
            status, payload = await self._post(path, form, self._access_token)
        finally:
            self._access_token = None
        if status in (401, 403):
            raise InvalidAuth(f"WeLock Cloud rejected the token (HTTP {status})")
        if status != 200:
            raise CannotConnect(f"Unexpected HTTP status {status}")
        return parse_envelope(payload)

    async def async_get_devices(self) -> list[WeLockDevice]:
        """Return the locks of the account including their BLE modules."""
        data = await self._authorized(ENDPOINT_DEVICES, {"pageSize": "40", "pageNo": "1"})
        return parse_device_list(data)

    async def async_request_unlock_command(
        self, device_number: str, ble_name: str, random_factor: int, battery: int
    ) -> bytes:
        """Ask the cloud for a one-time unlock command for a fresh BLE challenge."""
        if not device_number.strip() or not ble_name.strip():
            raise LockUnavailable("Device number and BLE name are required")
        if not 0 <= random_factor <= 255 or not 0 <= battery <= 255:
            raise LockUnavailable("BLE challenge values are out of range")
        try:
            data = await self._authorized(
                ENDPOINT_UNLOCK,
                {
                    "deviceNumber": device_number,
                    "deviceName": ble_name,
                    "randomFactor": str(random_factor),
                    "battery": str(battery),
                },
            )
        except InvalidAuth:
            raise
        except CannotConnect:
            raise
        except WeLockApiError as err:
            raise LockUnavailable(str(err)) from None
        return parse_unlock_command(data)
