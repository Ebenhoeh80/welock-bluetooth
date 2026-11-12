"""Persistent per-lock cache of learned unlock commands (randomFactor -> command).

The WeLock cloud turns a BLE challenge into a 15-byte unlock command. Analysis of
the real lock showed the command is a deterministic function of the single
``randomFactor`` byte of the challenge alone: ``battery`` and the BLE
``devicePassword`` do not change it. There are therefore at most 256 distinct
commands per lock.

This cache stores each command the cloud returns under its ``randomFactor``. Over
normal use the table fills itself up; once a value is known, the integration can
build the very same command locally without a cloud round-trip. A cached command
is byte-identical to what the cloud would return - it is a stored real command,
not a self-generated payload - and it is re-validated before every use.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import COMMAND_SPACE, DOMAIN, STORAGE_VERSION
from .protocol import validate_unlock_command

_LOGGER = logging.getLogger(__name__)


def _storage_key(entry_id: str) -> str:
    """Return the HA storage key for one config entry's command table."""
    return f"{DOMAIN}.{entry_id}.commands"


class CommandCache:
    """A ``randomFactor -> command`` table backed by Home Assistant storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the cache for one config entry."""
        self._store: Store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))
        self._map: dict[int, str] = {}  # randomFactor -> command as hex string
        self._loaded = False

    async def async_load(self) -> None:
        """Load the persisted table. Invalid entries are dropped silently."""
        data = await self._store.async_load()
        table: dict[int, str] = {}
        if isinstance(data, dict):
            for key, value in (data.get("commands") or {}).items():
                try:
                    rf = int(key)
                except (TypeError, ValueError):
                    continue
                if 0 <= rf <= 255 and self._is_valid_hex(value):
                    table[rf] = value
        self._map = table
        self._loaded = True
        _LOGGER.debug("Loaded %d/%d learned unlock commands", len(table), COMMAND_SPACE)

    @staticmethod
    def _is_valid_hex(value: object) -> bool:
        if not isinstance(value, str):
            return False
        try:
            validate_unlock_command(bytes.fromhex(value))
        except ValueError:
            return False
        return True

    def get(self, random_factor: int) -> bytes | None:
        """Return the learned command for a challenge, or ``None`` if unknown.

        A stored entry that no longer validates is discarded and treated as a miss.
        """
        hex_value = self._map.get(random_factor)
        if hex_value is None:
            return None
        try:
            return validate_unlock_command(bytes.fromhex(hex_value))
        except ValueError:
            self._map.pop(random_factor, None)
            return None

    async def async_put(self, random_factor: int, command: bytes) -> None:
        """Store a command learned from the cloud; no-op if unchanged or invalid."""
        try:
            validate_unlock_command(command)
        except ValueError:
            return
        if not 0 <= random_factor <= 255:
            return
        hex_value = command.hex()
        if self._map.get(random_factor) == hex_value:
            return
        self._map[random_factor] = hex_value
        await self._store.async_save({"commands": self._map})
        _LOGGER.debug(
            "Learned unlock command for randomFactor=%d (%d/%d known)",
            random_factor,
            len(self._map),
            COMMAND_SPACE,
        )

    async def async_clear(self) -> None:
        """Forget all learned commands and remove the stored file."""
        self._map = {}
        await self._store.async_remove()

    @property
    def count(self) -> int:
        """Number of learned commands (0..256)."""
        return len(self._map)

    @property
    def coverage(self) -> int:
        """Share of the 256-value command space that is known, in percent."""
        return round(100 * len(self._map) / COMMAND_SPACE)

    @property
    def complete(self) -> bool:
        """True once every randomFactor value has been learned."""
        return len(self._map) >= COMMAND_SPACE
