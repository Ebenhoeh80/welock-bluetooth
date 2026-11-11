"""Config flow for WeLock Smart Lock.

Setup follows the WeLock workflow and enforces each step:

1. ``bluetooth`` (optional): Home Assistant discovered a ``WeLock*`` BLE module.
2. ``user``: cloud login with the WeLock app account. Warns that a login ends
   other sessions (e.g. the WeLock app).
3. ``select``: pick the lock / BLE module from the cloud device list
   (deviceNumber, ble[].deviceName, ble[].deviceMac).
4. ``verify``: Home Assistant must reach the lock over Bluetooth and the lock
   must answer the status/challenge request (battery). No unlock is sent.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, WeLockApiClient, WeLockApiError, WeLockDevice
from .ble import LockNotInRange, WeLockBleError, async_exchange, lock_in_range
from .const import (
    CONF_ADDRESS,
    CONF_AUTO_RELOCK_DELAY,
    CONF_BATTERY_INTERVAL,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_AUTO_RELOCK_DELAY,
    DEFAULT_BATTERY_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .protocol import format_mac

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


def _candidates(devices: list[WeLockDevice]) -> dict[str, dict[str, Any]]:
    """Map BLE address -> entry data for every BLE module with a valid address."""
    out: dict[str, dict[str, Any]] = {}
    for device in devices:
        for module in device.ble:
            if not module.address:
                continue
            out[module.address] = {
                CONF_ADDRESS: module.address,
                CONF_DEVICE_NUMBER: device.device_number,
                CONF_BLE_NAME: module.name,
                CONF_MODEL: device.model,
                "battery": module.battery,
            }
    return out


async def _async_login_and_list(hass, username: str, password: str) -> list[WeLockDevice]:
    api = WeLockApiClient(username, password, async_get_clientsession(hass))
    return await api.async_get_devices()


class WeLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeLock Smart Lock."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered_address: str | None = None
        self._username: str = ""
        self._password: str = ""
        self._candidates: dict[str, dict[str, Any]] = {}
        self._selected: dict[str, Any] | None = None

    # Step 1 (optional): Bluetooth discovery
    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        """Handle a WeLock module discovered by Home Assistant Bluetooth."""
        address = format_mac(discovery_info.address) or discovery_info.address
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        self._discovered_address = address
        self.context["title_placeholders"] = {"name": discovery_info.name or address}
        return await self.async_step_user()

    # Step 2: cloud login
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Log in to the WeLock cloud and load the device list."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME].strip()
            self._password = user_input[CONF_PASSWORD]
            try:
                devices = await _async_login_and_list(self.hass, self._username, self._password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except WeLockApiError:
                errors["base"] = "cloud_error"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during WeLock login")
                errors["base"] = "unknown"
            else:
                self._candidates = _candidates(devices)
                if self._discovered_address:
                    match = self._candidates.get(self._discovered_address)
                    if match is None:
                        return self.async_abort(reason="not_in_account")
                    self._candidates = {self._discovered_address: match}
                if not self._candidates:
                    errors["base"] = "no_locks"
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                LOGIN_SCHEMA, {CONF_USERNAME: self._username}
            ),
            errors=errors,
        )

    # Step 3: pick the lock / BLE module
    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Choose which BLE module of the account to set up."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            self._selected = self._candidates[address]
            return await self.async_step_verify()

        options: dict[str, str] = {}
        default: str | None = None
        for address, cand in self._candidates.items():
            in_range = lock_in_range(self.hass, address)
            battery = f"{cand['battery']} %" if cand["battery"] is not None else "?"
            reach = "in Reichweite" if in_range else "nicht in Reichweite"
            options[address] = (
                f"{cand[CONF_BLE_NAME]} ({address}) - Schloss {cand[CONF_DEVICE_NUMBER]}, "
                f"Akku laut Cloud {battery}, {reach}"
            )
            if in_range and default is None:
                default = address
        default = default or next(iter(options))

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS, default=default): vol.In(options)}),
        )

    # Step 4: Bluetooth reachability + status/challenge check (no unlock)
    async def async_step_verify(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Check that Home Assistant reaches the lock and the lock answers."""
        assert self._selected is not None
        selected = self._selected
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                state = await async_exchange(self.hass, selected[CONF_ADDRESS])
            except LockNotInRange:
                errors["base"] = "not_in_range"
            except WeLockBleError as err:
                _LOGGER.debug("WeLock BLE check failed: %s", err)
                errors["base"] = "ble_failed"
            else:
                _LOGGER.debug("WeLock BLE check OK, battery %s %%", state.battery)
                return self.async_create_entry(
                    title=selected[CONF_BLE_NAME],
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_ADDRESS: selected[CONF_ADDRESS],
                        CONF_DEVICE_NUMBER: selected[CONF_DEVICE_NUMBER],
                        CONF_BLE_NAME: selected[CONF_BLE_NAME],
                        CONF_MODEL: selected[CONF_MODEL],
                    },
                )

        return self.async_show_form(
            step_id="verify",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "name": selected[CONF_BLE_NAME],
                "address": selected[CONF_ADDRESS],
                "device_number": selected[CONF_DEVICE_NUMBER],
            },
        )

    # Reauth: new password, lock must still be in the account
    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start reauthentication."""
        self._username = entry_data[CONF_USERNAME]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the password again and check the lock is still in the account."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            try:
                devices = await _async_login_and_list(self.hass, self._username, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except WeLockApiError:
                errors["base"] = "cloud_error"
            else:
                if entry.data[CONF_ADDRESS] not in _candidates(devices):
                    errors["base"] = "lock_not_found"
                else:
                    return self.async_update_reload_and_abort(
                        entry, data={**entry.data, CONF_PASSWORD: password}
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"username": self._username},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return WeLockOptionsFlowHandler()


class WeLockOptionsFlowHandler(config_entries.OptionsFlow):
    """Options: relock delay, battery read interval, presence poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AUTO_RELOCK_DELAY,
                    default=opts.get(CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY),
                ): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
                vol.Optional(
                    CONF_BATTERY_INTERVAL,
                    default=opts.get(CONF_BATTERY_INTERVAL, DEFAULT_BATTERY_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=168)),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
