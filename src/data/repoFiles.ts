import { RepoFile } from '../types';

export const REPO_FILES: RepoFile[] = [
  {
    path: 'custom_components/welock/manifest.json',
    name: 'manifest.json',
    category: 'json',
    description: {
      de: 'Home Assistant Komponenten-Manifest (Domain, Version, Codeowners, IoT-Klasse)',
      en: 'Home Assistant integration manifest (Domain, version, codeowners, IoT class)',
      es: 'Manifiesto de integración de Home Assistant (Dominio, versión, propietarios, clase IoT)',
      fr: "Manifeste d'intégration Home Assistant (Domaine, version, propriétaires, classe IoT)",
    },
    content: `{
  "domain": "welock",
  "name": "WeLock Smart Lock",
  "codeowners": ["@Ebenhoeh80"],
  "config_flow": true,
  "documentation": "https://github.com/Ebenhoeh80/welock-aistudio",
  "issue_tracker": "https://github.com/Ebenhoeh80/welock-aistudio/issues",
  "iot_class": "cloud_polling",
  "version": "1.2.0",
  "requirements": ["aiohttp>=3.9.0"]
}`,
  },
  {
    path: 'custom_components/welock/const.py',
    name: 'const.py',
    category: 'python',
    description: {
      de: 'Konstanten, Endpunkte der WeLock Cloud API und Standardwerte',
      en: 'Constants, WeLock cloud API endpoints, and configuration defaults',
      es: 'Constantes, extremos de la API en la nube de WeLock y valores predeterminados',
      fr: 'Constantes, points de terminaison de l’API WeLock et valeurs par défaut',
    },
    content: `"""Constants for the WeLock Smart Lock integration."""
from typing import Final

DOMAIN: Final = "welock"

# Configuration keys
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AUTO_RELOCK_DELAY: Final = "auto_relock_delay"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
DEFAULT_AUTO_RELOCK_DELAY: Final = 7  # seconds (WeLock locks mechanically lock after turning)

# API endpoints
BASE_API_URL: Final = "https://api.welockglobal.com"
ENDPOINT_AUTH: Final = "/app/v1/open/oauth/token"
ENDPOINT_LOCK_LIST: Final = "/app/v1/open/lock/list"
ENDPOINT_LOCK_DETAIL: Final = "/app/v1/open/lock/detail"
ENDPOINT_UNLOCK: Final = "/app/v1/open/lock/unlock"
ENDPOINT_GATEWAY_LIST: Final = "/app/v1/open/gateway/list"

# Device attributes
ATTR_LOCK_SN: Final = "lock_sn"
ATTR_MAC: Final = "mac"
ATTR_MODEL: Final = "model"
ATTR_BATTERY: Final = "battery"
ATTR_WIFI_BOX_ID: Final = "wifi_box_id"
ATTR_LAST_UNLOCK_TIME: Final = "last_unlock_time"
ATTR_LAST_UNLOCK_TYPE: Final = "last_unlock_type"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_SIGNAL_STRENGTH: Final = "signal_strength"`,
  },
  {
    path: 'custom_components/welock/api.py',
    name: 'api.py',
    category: 'python',
    description: {
      de: 'Asynchroner WeLock Cloud REST-API Client (Authentifizierung, Schlösser, Entriegeln)',
      en: 'Asynchronous WeLock Cloud REST API client (authentication, locks, remote unlock)',
      es: 'Cliente de API REST en la nube asíncrono para WeLock (autenticación, cerraduras, desbloqueo)',
      fr: 'Client API REST Cloud asynchrone pour WeLock (authentification, serrures, déverrouillage)',
    },
    content: `"""API client for WeLock Cloud Services."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
import aiohttp

from .const import (
    BASE_API_URL,
    ENDPOINT_AUTH,
    ENDPOINT_LOCK_LIST,
    ENDPOINT_LOCK_DETAIL,
    ENDPOINT_UNLOCK,
    ENDPOINT_GATEWAY_LIST,
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
            "User-Agent": "HomeAssistant-WeLock/1.2.0",
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
                if code not in (200, 0, "200", "0") and "data" not in data and "access_token" not in data:
                    msg = data.get("msg") or data.get("message") or "Unknown authentication failure"
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
            "User-Agent": "HomeAssistant-WeLock/1.2.0",
        }

        try:
            async with self._session.request(
                method, url, json=json_data, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.info("WeLock token expired. Refreshing token...")
                    await self.async_authenticate()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with self._session.request(
                        method, url, json=json_data, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
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
            _LOGGER.debug("Could not fetch gateway list: %s", err)
            return []`,
  },
  {
    path: 'custom_components/welock/__init__.py',
    name: '__init__.py',
    category: 'python',
    description: {
      de: 'Hauptmodul: Initialisierung des Coordinators, Entitätenverwaltung und Lifecycle',
      en: 'Main module: Coordinator setup, entity management, and integration lifecycle',
      es: 'Módulo principal: Configuración del coordinador, gestión de entidades y ciclo de vida',
      fr: 'Module principal : Configuration du coordinateur, gestion des entités et cycle de vie',
    },
    content: `"""The WeLock Smart Lock integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, WeLockApiClient, WeLockApiError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LOCK,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


class WeLockDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching WeLock data from the cloud API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WeLockApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from WeLock Cloud."""
        try:
            locks = await self.api.async_get_locks()
            gateways = await self.api.async_get_gateways()

            lock_dict: dict[str, dict[str, Any]] = {}
            for lock in locks:
                lock_sn = lock.get("lockSn") or lock.get("lock_sn") or lock.get("sn")
                if lock_sn:
                    detail = await self.api.async_get_lock_detail(lock_sn)
                    merged = {**lock, **detail}
                    lock_dict[str(lock_sn)] = merged

            return {
                "locks": lock_dict,
                "gateways": gateways,
            }
        except (InvalidAuth, CannotConnect, WeLockApiError) as err:
            raise UpdateFailed(f"Error communicating with WeLock Cloud: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WeLock Smart Lock from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    session = async_get_clientsession(hass)
    api = WeLockApiClient(client_id=client_id, client_secret=client_secret, session=session)

    try:
        await api.async_authenticate()
    except Exception as err:
        _LOGGER.error("Failed to authenticate with WeLock during setup: %s", err)
        raise

    coordinator = WeLockDataUpdateCoordinator(
        hass=hass,
        api=api,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)`,
  },
  {
    path: 'custom_components/welock/config_flow.py',
    name: 'config_flow.py',
    category: 'python',
    description: {
      de: 'Grafischer Einrichtungsdialog (ConfigFlow & OptionsFlow) in Home Assistant',
      en: 'Home Assistant graphical setup UI (ConfigFlow & OptionsFlow)',
      es: 'Asistente de configuración gráfica (ConfigFlow y OptionsFlow) en Home Assistant',
      fr: 'Assistant de configuration graphique (ConfigFlow et OptionsFlow) dans Home Assistant',
    },
    content: `"""Config flow for WeLock Smart Lock integration."""
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
    CONF_SCAN_INTERVAL,
    DEFAULT_AUTO_RELOCK_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class WeLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeLock Smart Lock."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()

            await self.async_set_unique_id(client_id.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = WeLockApiClient(client_id, client_secret, session)

            try:
                await api.async_authenticate()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except WeLockApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during WeLock config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"WeLock ({client_id[:8]}...)",
                    data={
                        CONF_CLIENT_ID: client_id,
                        CONF_CLIENT_SECRET: client_secret,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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

        return self.async_show_form(step_id="init", data_schema=options_schema)`,
  },
  {
    path: 'custom_components/welock/lock.py',
    name: 'lock.py',
    category: 'python',
    description: {
      de: 'Schloss-Plattform (Entriegeln via WiFiBox, mechanischer Auto-Relock-Reset)',
      en: 'Lock platform (remote unlock via WiFiBox, mechanical auto-relock reset)',
      es: 'Plataforma de cerradura (desbloqueo remoto por WiFiBox, autorreenganche mecánico)',
      fr: 'Plateforme de serrure (déverrouillage à distance via WiFiBox, réenclenchement mécanique)',
    },
    content: `"""Support for WeLock smart locks."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AUTO_RELOCK_DELAY,
    DEFAULT_AUTO_RELOCK_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock locks from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    relock_delay = entry.options.get(
        CONF_AUTO_RELOCK_DELAY,
        entry.data.get(CONF_AUTO_RELOCK_DELAY, DEFAULT_AUTO_RELOCK_DELAY),
    )

    entities: list[WeLockLock] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(
            WeLockLock(
                coordinator=coordinator,
                api=api,
                lock_sn=lock_sn,
                relock_delay=relock_delay,
            )
        )

    async_add_entities(entities)


class WeLockLock(CoordinatorEntity, LockEntity):
    """Representation of a WeLock Smart Lock entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: Any,
        api: Any,
        lock_sn: str,
        relock_delay: int,
    ) -> None:
        """Initialize the lock entity."""
        super().__init__(coordinator)
        self.api = api
        self._lock_sn = lock_sn
        self._relock_delay = relock_delay
        self._is_locked = True
        self._is_unlocking = False
        self._attr_unique_id = f"welock_{lock_sn}_lock"

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Home Assistant device registry."""
        model = self.lock_data.get("model") or self.lock_data.get("deviceType") or "Smart Lock"
        custom_name = self.lock_data.get("lockName") or self.lock_data.get("name") or f"WeLock {self._lock_sn[-4:]}"
        fw = self.lock_data.get("firmwareVersion") or self.lock_data.get("firmware") or "1.0"
        wifi_box = self.lock_data.get("wifiBoxId") or self.lock_data.get("gatewayId")

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._lock_sn)},
            "name": custom_name,
            "manufacturer": "WeLock",
            "model": f"WeLock {model}",
            "sw_version": str(fw),
        }
        if wifi_box:
            info["via_device"] = (DOMAIN, str(wifi_box))

        return info

    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        return self._is_locked

    @property
    def is_unlocking(self) -> bool:
        """Return true if lock is unlocking."""
        return self._is_unlocking

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device-specific attributes."""
        data = self.lock_data
        return {
            "serial_number": self._lock_sn,
            "mac_address": data.get("mac") or data.get("macAddress"),
            "model": data.get("model") or data.get("deviceType"),
            "battery_percent": data.get("battery") or data.get("electric"),
            "gateway_sn": data.get("wifiBoxId") or data.get("gatewayId"),
            "last_active": data.get("lastActive") or data.get("updateTime"),
        }

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the WeLock device via WiFiBox gateway."""
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            await self.api.async_unlock(self._lock_sn)
            self._is_locked = False
            self._is_unlocking = False
            self.async_write_ha_state()

            self.hass.async_create_task(self._async_auto_relock())

        except Exception as err:
            _LOGGER.error("Failed to unlock WeLock %s: %s", self._lock_sn, err)
            self._is_unlocking = False
            self._is_locked = True
            self.async_write_ha_state()
            raise

    async def _async_auto_relock(self) -> None:
        """Simulate mechanical auto-relock of the WeLock cylinder knob."""
        await asyncio.sleep(self._relock_delay)
        self._is_locked = True
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device (WeLock auto-locks mechanically)."""
        self._is_locked = True
        self._is_unlocking = False
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()`,
  },
  {
    path: 'custom_components/welock/sensor.py',
    name: 'sensor.py',
    category: 'python',
    description: {
      de: 'Sensoren: Batterieprozent, Signalstärke und letzte Entriegelungsmethode',
      en: 'Sensors: Battery percentage, signal strength, and last unlock method',
      es: 'Sensores: Porcentaje de batería, intensidad de señal y último método de apertura',
      fr: 'Capteurs : Pourcentage de batterie, intensité du signal et dernière méthode d’ouverture',
    },
    content: `"""Sensor platform for WeLock smart locks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: list[SensorEntity] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(WeLockBatterySensor(coordinator, lock_sn))
        entities.append(WeLockSignalSensor(coordinator, lock_sn))
        entities.append(WeLockLastUnlockTypeSensor(coordinator, lock_sn))

    async_add_entities(entities)


class WeLockSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for WeLock sensor entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._lock_sn = lock_sn

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking sensor to the lock."""
        model = self.lock_data.get("model") or "Smart Lock"
        name = self.lock_data.get("lockName") or f"WeLock {self._lock_sn[-4:]}"
        fw = self.lock_data.get("firmwareVersion") or "1.0"
        wifi_box = self.lock_data.get("wifiBoxId")

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._lock_sn)},
            "name": name,
            "manufacturer": "WeLock",
            "model": f"WeLock {model}",
            "sw_version": str(fw),
        }
        if wifi_box:
            info["via_device"] = (DOMAIN, str(wifi_box))
        return info


class WeLockBatterySensor(WeLockSensorBase):
    """Battery level sensor for WeLock."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "battery"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_battery"

    @property
    def native_value(self) -> int | None:
        """Return the current battery percentage."""
        val = self.lock_data.get("battery") or self.lock_data.get("electric")
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                return None
        return None


class WeLockSignalSensor(WeLockSensorBase):
    """Bluetooth / WiFi Gateway signal strength sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_translation_key = "signal_strength"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the signal strength sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_signal"

    @property
    def native_value(self) -> int | None:
        """Return the RSSI signal strength."""
        val = self.lock_data.get("rssi") or self.lock_data.get("signal")
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                return None
        return None


class WeLockLastUnlockTypeSensor(WeLockSensorBase):
    """Sensor reporting the last unlock mechanism."""

    _attr_translation_key = "last_unlock_type"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the last unlock sensor."""
        super().__init__(coordinator, lock_sn)
        self._attr_unique_id = f"welock_{lock_sn}_last_unlock_type"

    @property
    def native_value(self) -> str | None:
        """Return the last unlock method."""
        val = (
            self.lock_data.get("lastUnlockType")
            or self.lock_data.get("unlockType")
            or self.lock_data.get("lastAction")
        )
        if not val:
            return "None"
        mapping = {
            "1": "Fingerprint",
            "2": "RFID Card",
            "3": "Passcode",
            "4": "App / Bluetooth",
            "5": "Gateway / Cloud",
            "fingerprint": "Fingerprint",
            "card": "RFID Card",
            "password": "Passcode",
            "app": "App / Gateway",
        }
        return mapping.get(str(val).lower(), str(val))`,
  },
  {
    path: 'custom_components/welock/binary_sensor.py',
    name: 'binary_sensor.py',
    category: 'python',
    description: {
      de: 'Binärsensoren: Verbindungsstatus des Schlosses & WiFiBox Gateway online/offline',
      en: 'Binary sensors: Lock connection status & WiFiBox gateway online/offline',
      es: 'Sensores binarios: Estado de conexión de cerradura y estado online/offline del gateway',
      fr: 'Capteurs binaires : État de connexion de la serrure et de la passerelle WiFiBox',
    },
    content: `"""Binary sensor platform for WeLock smart locks."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeLock binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: list[BinarySensorEntity] = []
    locks = coordinator.data.get("locks", {})
    for lock_sn in locks:
        entities.append(WeLockLockOnlineBinarySensor(coordinator, lock_sn))

    gateways = coordinator.data.get("gateways", [])
    if isinstance(gateways, list):
        for gw in gateways:
            gw_id = gw.get("gatewayId") or gw.get("wifiBoxId") or gw.get("id")
            if gw_id:
                entities.append(WeLockGatewayBinarySensor(coordinator, str(gw_id), gw))

    async_add_entities(entities)


class WeLockLockOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor reporting whether the lock is communicating with the gateway."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator: Any, lock_sn: str) -> None:
        """Initialize the online binary sensor."""
        super().__init__(coordinator)
        self._lock_sn = lock_sn
        self._attr_unique_id = f"welock_{lock_sn}_online"

    @property
    def lock_data(self) -> dict[str, Any]:
        """Return the dictionary of data for this lock."""
        return self.coordinator.data.get("locks", {}).get(self._lock_sn, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking binary sensor to the lock."""
        model = self.lock_data.get("model") or "Smart Lock"
        name = self.lock_data.get("lockName") or f"WeLock {self._lock_sn[-4:]}"
        fw = self.lock_data.get("firmwareVersion") or "1.0"
        wifi_box = self.lock_data.get("wifiBoxId")

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._lock_sn)},
            "name": name,
            "manufacturer": "WeLock",
            "model": f"WeLock {model}",
            "sw_version": str(fw),
        }
        if wifi_box:
            info["via_device"] = (DOMAIN, str(wifi_box))
        return info

    @property
    def is_on(self) -> bool:
        """Return true if lock is online and reachable."""
        status = self.lock_data.get("status")
        online = self.lock_data.get("online")
        if online is not None:
            return bool(online)
        if status is not None:
            return str(status) in ("1", "online", "normal")
        return True


class WeLockGatewayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for the WeLock WiFiBox gateway."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "gateway_connectivity"

    def __init__(self, coordinator: Any, gateway_id: str, initial_data: dict[str, Any]) -> None:
        """Initialize the gateway binary sensor."""
        super().__init__(coordinator)
        self._gateway_id = gateway_id
        self._initial_data = initial_data
        self._attr_unique_id = f"welock_gateway_{gateway_id}_online"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the gateway."""
        return {
            "identifiers": {(DOMAIN, self._gateway_id)},
            "name": f"WeLock WiFiBox ({self._gateway_id[-4:]})",
            "manufacturer": "WeLock",
            "model": "WiFiBox Gateway",
        }

    @property
    def is_on(self) -> bool:
        """Return true if gateway is online."""
        gateways = self.coordinator.data.get("gateways", [])
        for gw in gateways:
            gid = str(gw.get("gatewayId") or gw.get("wifiBoxId") or gw.get("id"))
            if gid == self._gateway_id:
                return bool(gw.get("online", True))
        return True`,
  },
  {
    path: 'custom_components/welock/translations/de.json',
    name: 'translations/de.json',
    category: 'json',
    description: {
      de: 'Deutsche Lokalisierung für Konfigurationsassistent, Optionen & Entitäten',
      en: 'German localization for setup wizard, options, and entities',
      es: 'Localización en alemán para asistente de configuración, opciones y entidades',
      fr: 'Localisation allemande pour assistant de configuration, options et entités',
    },
    content: `{
  "config": {
    "step": {
      "user": {
        "title": "WeLock Smart Lock Einrichtung",
        "description": "Geben Sie Ihre WeLock API-Zugangsdaten ein, die Sie in der WeLock Mobile-App finden (Seitenmenü -> Home Assistant).",
        "data": {
          "client_id": "Client-ID",
          "client_secret": "Client-Secret"
        }
      },
      "reauth": {
        "title": "WeLock-Konto erneut authentifizieren",
        "description": "Bitte aktualisieren Sie Ihre Zugangsdaten, um die Verbindung zu Ihren WeLock-Geräten wiederherzustellen.",
        "data": {
          "client_id": "Client-ID",
          "client_secret": "Client-Secret"
        }
      }
    },
    "error": {
      "cannot_connect": "Verbindung zur WeLock Cloud (api.welockglobal.com) fehlgeschlagen. Bitte prüfen Sie Ihre Netzwerkverbindung.",
      "invalid_auth": "Ungültige Client-ID oder ungültiges Client-Secret. Bitte überprüfen Sie die Eingabe in der WeLock-App.",
      "unknown": "Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut."
    },
    "abort": {
      "already_configured": "Dieses WeLock-Konto ist in Home Assistant bereits eingerichtet."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "WeLock Integrations-Optionen",
        "description": "Konfigurieren Sie das Abfrageintervall und das Schlossverhalten.",
        "data": {
          "scan_interval": "Abfrageintervall (Sekunden)",
          "auto_relock_delay": "Mechanische Rückstellverzögerung (Sekunden)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "battery": {
        "name": "Batterie"
      },
      "signal_strength": {
        "name": "Signalstärke"
      },
      "last_unlock_type": {
        "name": "Letzte Entriegelungsmethode"
      }
    },
    "binary_sensor": {
      "connectivity": {
        "name": "Schloss-Verbindung"
      },
      "gateway_connectivity": {
        "name": "Gateway-Verbindung"
      }
    }
  }
}`,
  },
  {
    path: 'custom_components/welock/translations/en.json',
    name: 'translations/en.json',
    category: 'json',
    description: {
      de: 'Englische Lokalisierung (Referenzsprache für Home Assistant Core)',
      en: 'English localization (reference strings for Home Assistant Core)',
      es: 'Localización en inglés (referencia para Home Assistant Core)',
      fr: 'Localisation anglaise (référence pour Home Assistant Core)',
    },
    content: `{
  "config": {
    "step": {
      "user": {
        "title": "WeLock Smart Lock Setup",
        "description": "Enter your WeLock API credentials obtained from the WeLock mobile application (Sidebar Menu -> Home Assistant).",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      },
      "reauth": {
        "title": "Re-authenticate WeLock Account",
        "description": "Please update your credentials to restore the connection to your WeLock devices.",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to WeLock Cloud (api.welockglobal.com). Please verify internet connection.",
      "invalid_auth": "Invalid Client ID or Client Secret. Please verify in the WeLock mobile app.",
      "unknown": "An unexpected error occurred. Please try again."
    },
    "abort": {
      "already_configured": "This WeLock account is already configured in Home Assistant."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "WeLock Integration Options",
        "description": "Configure update polling frequency and lock behavior.",
        "data": {
          "scan_interval": "Data polling interval (seconds)",
          "auto_relock_delay": "Mechanical relock reset delay (seconds)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "battery": {
        "name": "Battery"
      },
      "signal_strength": {
        "name": "Signal Strength"
      },
      "last_unlock_type": {
        "name": "Last Unlock Method"
      }
    },
    "binary_sensor": {
      "connectivity": {
        "name": "Lock Status"
      },
      "gateway_connectivity": {
        "name": "Gateway Status"
      }
    }
  }
}`,
  },
  {
    path: 'custom_components/welock/translations/es.json',
    name: 'translations/es.json',
    category: 'json',
    description: {
      de: 'Spanische Lokalisierung (Neu hinzugefügt auf Benutzerwunsch)',
      en: 'Spanish localization (Newly added per user request)',
      es: 'Localización en español (Añadida según la solicitud del usuario)',
      fr: 'Localisation espagnole (Nouvellement ajoutée selon la demande)',
    },
    content: `{
  "config": {
    "step": {
      "user": {
        "title": "Configuración de WeLock Smart Lock",
        "description": "Introduce tus credenciales de API obtenidas en la aplicación móvil de WeLock (Menú lateral -> Home Assistant).",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      },
      "reauth": {
        "title": "Volver a autenticar cuenta de WeLock",
        "description": "Actualiza tus credenciales para restablecer la conexión con tus dispositivos WeLock.",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      }
    },
    "error": {
      "cannot_connect": "No se pudo conectar a la nube de WeLock (api.welockglobal.com). Comprueba tu conexión de red.",
      "invalid_auth": "Client ID o Client Secret no válidos. Comprueba los datos en la aplicación WeLock.",
      "unknown": "Se ha producido un error inesperado. Inténtalo de nuevo."
    },
    "abort": {
      "already_configured": "Esta cuenta de WeLock ya está configurada en Home Assistant."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Opciones de integración de WeLock",
        "description": "Configura la frecuencia de actualización y el comportamiento de la cerradura.",
        "data": {
          "scan_interval": "Intervalo de sondeo de datos (segundos)",
          "auto_relock_delay": "Tiempo de restablecimiento del bloqueo mecánico (segundos)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "battery": {
        "name": "Batería"
      },
      "signal_strength": {
        "name": "Intensidad de señal"
      },
      "last_unlock_type": {
        "name": "Último método de desbloqueo"
      }
    },
    "binary_sensor": {
      "connectivity": {
        "name": "Estado de la cerradura"
      },
      "gateway_connectivity": {
        "name": "Estado del gateway"
      }
    }
  }
}`,
  },
  {
    path: 'custom_components/welock/translations/fr.json',
    name: 'translations/fr.json',
    category: 'json',
    description: {
      de: 'Französische Lokalisierung (Neu hinzugefügt auf Benutzerwunsch)',
      en: 'French localization (Newly added per user request)',
      es: 'Localización en francés (Añadida según la solicitud del usuario)',
      fr: 'Localisation française (Nouvellement ajoutée selon la demande)',
    },
    content: `{
  "config": {
    "step": {
      "user": {
        "title": "Configuration de WeLock Smart Lock",
        "description": "Entrez vos identifiants d'API WeLock obtenus dans l'application mobile WeLock (Menu latéral -> Home Assistant).",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      },
      "reauth": {
        "title": "Réauthentifier le compte WeLock",
        "description": "Veuillez mettre à jour vos identifiants pour rétablir la connexion à vos appareils WeLock.",
        "data": {
          "client_id": "Client ID",
          "client_secret": "Client Secret"
        }
      }
    },
    "error": {
      "cannot_connect": "Impossible de se connecter au Cloud WeLock (api.welockglobal.com). Veuillez vérifier votre connexion réseau.",
      "invalid_auth": "Client ID ou Client Secret invalide. Veuillez vérifier dans l'application WeLock.",
      "unknown": "Une erreur inattendue est survenue. Veuillez réessayer."
    },
    "abort": {
      "already_configured": "Ce compte WeLock est déjà configuré dans Home Assistant."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Options de l'intégration WeLock",
        "description": "Configurez l'intervalle d'actualisation et le comportement de la serrure.",
        "data": {
          "scan_interval": "Intervalle d'interrogation (secondes)",
          "auto_relock_delay": "Délai de reverrouillage mécanique (secondes)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "battery": {
        "name": "Batterie"
      },
      "signal_strength": {
        "name": "Puissance du signal"
      },
      "last_unlock_type": {
        "name": "Dernière méthode de déverrouillage"
      }
    },
    "binary_sensor": {
      "connectivity": {
        "name": "État de la serrure"
      },
      "gateway_connectivity": {
        "name": "État de la passerelle"
      }
    }
  }
}`,
  },
  {
    path: 'hacs.json',
    name: 'hacs.json',
    category: 'json',
    description: {
      de: 'HACS / Home Assistant Marketplace Metadaten und Mindestanforderung',
      en: 'HACS / Home Assistant Marketplace metadata and requirements',
      es: 'Metadatos y requisitos de HACS / Home Assistant Marketplace',
      fr: 'Métadonnées et prérequis HACS / Marketplace Home Assistant',
    },
    content: `{
  "name": "WeLock Smart Lock",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}`,
  },
  {
    path: 'README.md',
    name: 'README.md',
    category: 'markdown',
    description: {
      de: 'Vollständige Dokumentation mit HACS-Installationsanleitung, Automationsbeispielen & Abzeichen',
      en: 'Complete documentation with HACS setup guide, automation examples & badges',
      es: 'Documentación completa con guía de instalación en HACS, automatizaciones y distintivos',
      fr: 'Documentation complète avec guide HACS, exemples d’automatisations et badges',
    },
    content: `# WeLock Smart Lock — Home Assistant HACS Integration & BLE Diagnose-Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/version-v1.2.0-blue.svg?style=for-the-badge)](https://github.com/Ebenhoeh80/welock-aistudio/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-languages--sprachen--idiomas--langues)

Integration for **WeLock Smart Door Locks** (Touch41, SECBN51, PCB41) and the **WeLock WiFiBox Gateway** into **Home Assistant** via **HACS**, sowie lokale BLE- und Cloud-Diagnose-Tools unter tools/.`,
  },
  {
    path: 'tools/README.md',
    name: 'tools/README.md',
    category: 'markdown',
    description: {
      de: 'Vollständige Dokumentation aller Python- und Startskripte unter tools/ (Architektur, Bleak, Aufrufe, Troubleshooting)',
      en: 'Complete documentation of all Python and launcher scripts in tools/ (Architecture, Bleak, usage, troubleshooting)',
      es: 'Documentación completa de los scripts de Python y lanzadores en tools/ (Arquitectura, Bleak, uso, solución de problemas)',
      fr: 'Documentation complète des scripts Python et lanceurs dans tools/ (Architecture, Bleak, utilisation, dépannage)',
    },
    content: `# WeLock BLE & Cloud Diagnose- und Experimentier-Werkzeuge

Dokumentation, Architektur und Anleitungen für alle Skripte unter tools/. Siehe tools/README.md im Projektverzeichnis.`,
  },
  {
    path: 'tools/requirements-ble.txt',
    name: 'tools/requirements-ble.txt',
    category: 'json',
    description: {
      de: 'Python-Abhängigkeiten für BLE-Tools (bleak>=0.22,<3)',
      en: 'Python dependencies for BLE tools (bleak>=0.22,<3)',
      es: 'Dependencias de Python para herramientas BLE (bleak>=0.22,<3)',
      fr: 'Dépendances Python pour les outils BLE (bleak>=0.22,<3)',
    },
    content: `bleak>=0.22.0,<3.0.0`,
  },
  {
    path: 'tools/ble_scan.py',
    name: 'tools/ble_scan.py',
    category: 'python',
    description: {
      de: 'BLE-Gerätesuche & WeLock-Erkennung (Scan mit RSSI, MAC-Adresse und Identifikation)',
      en: 'BLE device scanner & WeLock lock detection (scan with RSSI, MAC address, and identification)',
      es: 'Escáner BLE y detección de cerraduras WeLock (con RSSI, dirección MAC e identificación)',
      fr: 'Scanner BLE et détection de serrures WeLock (avec RSSI, adresse MAC et identification)',
    },
    content: `"""Suche nach Bluetooth Low Energy (BLE) Geräten und WeLock Smart Locks in Reichweite."""
# Vollständiger Quellcode siehe tools/ble_scan.py`,
  },
  {
    path: 'tools/ble_battery.py',
    name: 'tools/ble_battery.py',
    category: 'python',
    description: {
      de: 'Akkustand (%) und Challenge-Faktor per BLE direkt vom Schloss auslesen',
      en: 'Read battery percentage and challenge factor via BLE directly from the lock',
      es: 'Lectura de batería (%) y factor de desafío por BLE directamente desde la cerradura',
      fr: 'Lecture du niveau de batterie (%) et du défi par BLE directement depuis la serrure',
    },
    content: `"""Liest den Akkustand und Challenge-Faktor eines WeLock-Schlosses direkt über BLE aus."""
# Vollständiger Quellcode siehe tools/ble_battery.py`,
  },
  {
    path: 'tools/ble_probe.py',
    name: 'tools/ble_probe.py',
    category: 'python',
    description: {
      de: 'Inspektion eines BLE-Geräts (Erreichbarkeit, GATT-Services & Characteristics) ohne Schreibzugriff',
      en: 'Inspect a BLE device (availability, GATT services & characteristics) without sending write commands',
      es: 'Inspección de un dispositivo BLE (disponibilidad, servicios GATT y características) sin escritura',
      fr: 'Inspection d’un appareil BLE (disponibilité, services GATT et caractéristiques) sans écriture',
    },
    content: `"""Inspect a known BLE device without sending application commands."""

import argparse
import asyncio
import math
import sys

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


async def inspect_device(address: str, timeout: float, connect: bool) -> int:
    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device is None:
        print("Device not found during scan; it may be out of range or using a different address.", file=sys.stderr)
        return 1

    print("Device found during scan.")
    if not connect:
        return 0

    async with BleakClient(device, timeout=timeout) as client:
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            print("The expected service was not found.", file=sys.stderr)
            return 1

        characteristics = {characteristic.uuid.lower(): characteristic for characteristic in service.characteristics}
        missing = {WRITE_UUID, NOTIFY_UUID} - characteristics.keys()
        if missing:
            print(f"Expected characteristics not found: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

        print(f"Service: {SERVICE_UUID}")
        for uuid in (WRITE_UUID, NOTIFY_UUID):
            print(f"Characteristic: {uuid}; properties: {', '.join(characteristics[uuid].properties)}")
        print("Inspection complete; no application commands were sent.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True, help="BLE address to inspect; use only your own device.")
    parser.add_argument("--timeout", type=float, default=15, help="Scan and connection timeout in seconds.")
    parser.add_argument("--connect", action="store_true", help="Connect and inspect GATT services without writing.")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a positive finite number")
    try:
        return asyncio.run(inspect_device(args.address, args.timeout, args.connect))
    except (BleakError, OSError, TimeoutError) as exc:
        print(f"Bluetooth inspection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())`,
  },
  {
    path: 'tools/welock_cloud_login.py',
    name: 'tools/welock_cloud_login.py',
    category: 'python',
    description: {
      de: 'WeLock Cloud-Login Probe: Prüft Konto, listet Geräte, Schlosscodes und BLE-Namen auf (ohne Token-Speicherung)',
      en: 'WeLock cloud login probe: Tests account, lists devices, lock numbers, and BLE names (without saving tokens)',
      es: 'Sonda de inicio de sesión WeLock Cloud: Comprueba cuenta, lista dispositivos, códigos y nombres BLE',
      fr: 'Sonde de connexion Cloud WeLock : Vérifie le compte, liste les appareils, numéros et noms BLE',
    },
    content: `"""Experimental WELOCK cloud-login probe; it does not unlock a lock."""
# Vollständiger Quellcode siehe tools/welock_cloud_login.py`,
  },
  {
    path: 'tools/welock_command_probe.py',
    name: 'tools/welock_command_probe.py',
    category: 'python',
    description: {
      de: 'Hybrid-Probe: Liest BLE-Batterie & Challenge, holt 15-Byte-Befehl von der Cloud (ohne Entriegelungs-Write)',
      en: 'Hybrid probe: Reads BLE battery & challenge, requests 15-byte command from cloud (no unlock write)',
      es: 'Sonda híbrida: Lee batería y desafío BLE, solicita comando de 15 bytes a la nube (sin desbloqueo)',
      fr: 'Sonde hybride : Lit batterie et défi BLE, demande la commande de 15 octets au cloud (sans déverrouillage)',
    },
    content: `"""Request one experimental cloud command using a fresh BLE battery response."""
# Vollständiger Quellcode siehe tools/welock_command_probe.py`,
  },
  {
    path: 'tools/welock_unlock.py',
    name: 'tools/welock_unlock.py',
    category: 'python',
    description: {
      de: 'Autorisierter Vor-Ort Entriegelungstest über BLE (sendet 15-Byte-Befehl nach doppelter Bestätigung)',
      en: 'Authorized on-site unlock test via BLE (sends 15-byte command upon double confirmation)',
      es: 'Test de desbloqueo autorizado in situ por BLE (envía comando de 15 bytes tras doble confirmación)',
      fr: 'Test de déverrouillage autorisé sur site via BLE (envoie la commande de 15 octets après confirmation)',
    },
    content: `"""Autorisierter Vor-Ort Entriegelungstest via BLE und WeLock Cloud API."""
# Vollständiger Quellcode siehe tools/welock_unlock.py`,
  },
  {
    path: 'tools/welock_tools.sh',
    name: 'tools/welock_tools.sh',
    category: 'shell',
    description: {
      de: 'Interaktives Hauptmenü für alle WeLock-Werkzeuge unter Linux und macOS (inkl. venv-Setup)',
      en: 'Interactive main menu for all WeLock tools on Linux and macOS (incl. venv setup)',
      es: 'Menú principal interactivo para todas las herramientas WeLock en Linux y macOS',
      fr: 'Menu principal interactif pour tous les outils WeLock sous Linux et macOS',
    },
    content: `#!/usr/bin/env bash
# Interaktives WeLock Hauptmenü für Linux & macOS`,
  },
  {
    path: 'tools/welock_tools.ps1',
    name: 'tools/welock_tools.ps1',
    category: 'shell',
    description: {
      de: 'Interaktives Hauptmenü für alle WeLock-Werkzeuge unter Windows PowerShell',
      en: 'Interactive main menu for all WeLock tools on Windows PowerShell',
      es: 'Menú principal interactivo para todas las herramientas WeLock en Windows PowerShell',
      fr: 'Menu principal interactif pour tous les outils WeLock sous Windows PowerShell',
    },
    content: `<#
.SYNOPSIS
    WeLock Diagnostic Tools - Interaktives Hauptmenue (Windows PowerShell)
#>`,
  },
];
