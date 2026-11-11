"""Config flow for WeLock Smart Lock integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, WeLockApiClient, WeLockApiError
from .const import (
    CONF_AUTO_RELOCK_DELAY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_AUTO_RELOCK_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class WeLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeLock Smart Lock."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = (
                user_input.get(CONF_USERNAME) or user_input.get(CONF_CLIENT_ID) or ""
            ).strip()
            password = (
                user_input.get(CONF_PASSWORD) or user_input.get(CONF_CLIENT_SECRET) or ""
            ).strip()

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = WeLockApiClient(username=username, password=password, session=session)

            try:
                await api.async_authenticate()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except (CannotConnect, WeLockApiError):
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during WeLock config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"WeLock ({username})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_CLIENT_ID: username,
                        CONF_CLIENT_SECRET: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth upon invalid authentication."""
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return WeLockOptionsFlowHandler(config_entry)


class WeLockOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for WeLock."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data

        current_scan_interval = options.get(
            CONF_SCAN_INTERVAL,
            data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_relock_delay = options.get(
            CONF_AUTO_RELOCK_DELAY,
            data.get(CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_scan_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    CONF_AUTO_RELOCK_DELAY,
                    default=current_relock_delay,
                ): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
