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
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import COMMAND_SPACE, DOMAIN, STORAGE_VERSION
from .protocol import validate_unlock_command

_LOGGER = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Outcome of importing a command table into the cache."""

    added: int = 0
    unchanged: int = 0
    # randomFactor values whose stored command differs from the imported one.
    # The stored command is kept; the values themselves are never reported.
    conflicts: list[int] = field(default_factory=list)


def parse_command_table(data: Any) -> tuple[str, dict[int, bytes]]:
    """Validate a command-table file and return ``(device_number, table)``.

    The file is a JSON object with ``device_number`` and ``table`` (a mapping of
    randomFactor ``"0"``..``"255"`` to a 15-byte ``U1...`` command). Anything
    that is not well-formed rejects the whole file with a ``ValueError`` that
    names the problem but never contains a command.
    """
    if not isinstance(data, dict):
        raise ValueError("The file must contain a JSON object")
    device_number = data.get("device_number")
    if not isinstance(device_number, str) or not device_number.strip():
        raise ValueError("The file has no device_number")
    raw_table = data.get("table")
    if not isinstance(raw_table, dict) or not raw_table:
        raise ValueError("The file has no table of commands")
    table: dict[int, bytes] = {}
    bad: list[str] = []
    for key, value in raw_table.items():
        try:
            random_factor = int(key)
        except (TypeError, ValueError):
            bad.append(str(key)[:12])
            continue
        if not 0 <= random_factor <= 255 or not isinstance(value, str):
            bad.append(str(key)[:12])
            continue
        try:
            table[random_factor] = validate_unlock_command(value.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            bad.append(str(random_factor))
    if bad:
        raise ValueError(f"{len(bad)} invalid table entries (randomFactor: {', '.join(bad[:10])})")
    return device_number.strip(), table


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

    async def async_import(self, table: dict[int, bytes]) -> ImportResult:
        """Add commands from an imported table; never overwrites a stored command.

        A stored command that differs from the imported one is reported as a
        conflict and kept, because it was learned from the cloud for this lock.
        """
        result = ImportResult()
        for random_factor, command in sorted(table.items()):
            hex_value = command.hex()
            existing = self._map.get(random_factor)
            if existing is None:
                self._map[random_factor] = hex_value
                result.added += 1
            elif existing == hex_value:
                result.unchanged += 1
            else:
                result.conflicts.append(random_factor)
        if result.added:
            await self._store.async_save({"commands": self._map})
        _LOGGER.info(
            "Imported unlock commands: %d added, %d unchanged, %d conflicts (%d/%d known)",
            result.added,
            result.unchanged,
            len(result.conflicts),
            len(self._map),
            COMMAND_SPACE,
        )
        return result

    async def async_discard(self, random_factor: int) -> bool:
        """Forget one learned command (e.g. after it failed); True if it existed."""
        if self._map.pop(random_factor, None) is None:
            return False
        await self._store.async_save({"commands": self._map})
        _LOGGER.debug("Discarded learned unlock command for randomFactor=%d", random_factor)
        return True

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
