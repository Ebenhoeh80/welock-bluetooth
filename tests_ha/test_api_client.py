"""The cloud client talking to a fake HTTP session (no network)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import pytest

from custom_components.welock_ble.api import (
    ENDPOINT_AUTH,
    ENDPOINT_DEVICES,
    ENDPOINT_UNLOCK,
    ENDPOINT_UNLOCK_RECORD,
    CannotConnect,
    InvalidAuth,
    LockUnavailable,
    WeLockApiClient,
    WeLockApiError,
)

from .conftest import CLOUD_COMMAND

LOGIN_OK = {"code": 0, "data": {"access_token": "tok"}}


class FakeResponse:
    def __init__(self, status: int = 200, payload: Any = None, bad_json: bool = False) -> None:
        self.status = status
        self._payload = payload
        self._bad_json = bad_json

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self, content_type: str | None = None) -> Any:
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    """Answers each request from a table keyed by the path that ends the URL."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.requests: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def post(self, url: str, data: dict[str, str], headers: dict[str, str], **kwargs: Any):
        path = "/" + url.rstrip("/").split("/", 3)[-1] if "://" in url else url
        self.requests.append((url, data, headers))
        for key, answer in self.answers.items():
            if url.endswith(key):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected request {path}")


def _client(answers: dict[str, Any], user: str = "user@example.com", password: str = "pw"):
    session = FakeSession(answers)
    return WeLockApiClient(user, password, session, base_url="https://cloud.example/api"), session


async def test_an_unlock_command_is_requested_with_a_fresh_login() -> None:
    client, session = _client(
        {
            ENDPOINT_AUTH: FakeResponse(payload=LOGIN_OK),
            ENDPOINT_UNLOCK: FakeResponse(
                payload={"code": 0, "data": {"command": CLOUD_COMMAND.hex()}}
            ),
        }
    )
    command = await client.async_request_unlock_command("123", "WeLockX", 7, 80)
    assert command == CLOUD_COMMAND
    assert session.requests[1][1]["randomFactor"] == "7"
    assert session.requests[1][2]["Authorization"] == "tok"
    assert "authenticated=False" in repr(client)  # the token is dropped again
    assert client.username == "user@example.com"


async def test_login_log_does_not_contain_the_account(caplog: pytest.LogCaptureFixture) -> None:
    """A shared debug log must not reveal the WeLock account (diagnostics redact it too)."""
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(payload=LOGIN_OK)}, user="private@example.com")
    with caplog.at_level("DEBUG"):
        await client.async_authenticate()
    assert "private@example.com" not in caplog.text


async def test_the_device_list_and_access_log_are_parsed() -> None:
    client, _ = _client(
        {
            ENDPOINT_AUTH: FakeResponse(payload=LOGIN_OK),
            ENDPOINT_DEVICES: FakeResponse(
                payload={
                    "code": 0,
                    "data": [
                        {
                            "deviceNumber": "123",
                            "deviceName": "Door",
                            "ble": [
                                {"deviceName": "WeLockX", "deviceMac": "C4434A0342A9", "power": 90}
                            ],
                        }
                    ],
                }
            ),
            ENDPOINT_UNLOCK_RECORD: FakeResponse(
                payload={
                    "code": 0,
                    "data": [
                        {
                            "operatingState": 6,
                            "unlockResult": 1,
                            "nickName": "Dan",
                            "unlockingTime": "now",
                        }
                    ],
                }
            ),
        }
    )
    devices = await client.async_get_devices()
    assert devices[0].ble[0].address == "C4:43:4A:03:42:A9"
    records = await client.async_get_access_log("123")
    assert records[0].method == "app" and records[0].success is True


async def test_empty_or_wrong_credentials_are_rejected() -> None:
    client, _ = _client({}, user="", password="")
    with pytest.raises(InvalidAuth):
        await client.async_authenticate()
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(status=401)})
    with pytest.raises(InvalidAuth):
        await client.async_authenticate()
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(payload={"code": 5, "data": None})})
    with pytest.raises(InvalidAuth):
        await client.async_authenticate()
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(payload={"code": 0, "data": {}})})
    with pytest.raises(InvalidAuth):
        await client.async_authenticate()


async def test_transport_problems_become_cannot_connect() -> None:
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(status=500)})
    with pytest.raises(CannotConnect):
        await client.async_authenticate()
    for error in (aiohttp.ClientError("x"), asyncio.TimeoutError()):
        client, _ = _client({ENDPOINT_AUTH: error})
        with pytest.raises(CannotConnect):
            await client.async_authenticate()
    client, _ = _client({ENDPOINT_AUTH: FakeResponse(bad_json=True)})
    with pytest.raises(CannotConnect):
        await client.async_authenticate()
    client = WeLockApiClient("u", "p", None)
    with pytest.raises(CannotConnect):
        await client.async_authenticate()


async def test_a_rejected_token_or_server_error_after_login() -> None:
    for status, expected in ((403, InvalidAuth), (500, CannotConnect)):
        client, _ = _client(
            {
                ENDPOINT_AUTH: FakeResponse(payload=LOGIN_OK),
                ENDPOINT_DEVICES: FakeResponse(status=status),
            }
        )
        with pytest.raises(expected):
            await client.async_get_devices()


async def test_unlock_requests_validate_their_input_and_map_cloud_errors() -> None:
    client, _ = _client({})
    for args in (
        ("", "WeLockX", 7, 80),
        ("123", " ", 7, 80),
        ("123", "WeLockX", 300, 80),
        ("123", "WeLockX", 7, -1),
    ):
        with pytest.raises(LockUnavailable):
            await client.async_request_unlock_command(*args)
    with pytest.raises(WeLockApiError):
        await client.async_get_access_log(" ")

    client, _ = _client(
        {
            ENDPOINT_AUTH: FakeResponse(payload=LOGIN_OK),
            ENDPOINT_UNLOCK: FakeResponse(payload={"code": 9, "data": None}),
        }
    )
    with pytest.raises(LockUnavailable):
        await client.async_request_unlock_command("123", "WeLockX", 7, 80)

    client, _ = _client({ENDPOINT_AUTH: FakeResponse(status=401)})
    with pytest.raises(InvalidAuth):
        await client.async_request_unlock_command("123", "WeLockX", 7, 80)

    client, _ = _client({ENDPOINT_AUTH: FakeResponse(status=500)})
    with pytest.raises(CannotConnect):
        await client.async_request_unlock_command("123", "WeLockX", 7, 80)
