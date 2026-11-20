"""Switch platform for WeLock: turn offline unlocking on or off."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_SPACE
from .coordinator import WeLockConfigEntry, WeLockCoordinator
from .entity import WeLockEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: WeLockConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the offline-unlock switch."""
    async_add_entities([WeLockOfflineUnlockSwitch(entry.runtime_data, entry)])


class WeLockOfflineUnlockSwitch(WeLockEntity, SwitchEntity):
    """Use locally learned unlock commands instead of asking the cloud.

    On: when the lock's challenge value is already known, the stored command is
    sent without a cloud round-trip. Off: every unlock asks the cloud (the table
    keeps learning). The switch takes effect immediately and is remembered across
    restarts; it is the same setting as the option in the integration's dialog.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:lock-clock"
    _attr_translation_key = "offline_unlock"

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, "offline_unlock")

    @property
    def available(self) -> bool:
        """Always available: it only changes a local setting."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether offline unlocking is enabled."""
        return self.coordinator.local_unlock

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Show how many commands are known, i.e. how often the switch can help."""
        cache = self.coordinator.cache
        return {
            "learned_commands": cache.count,
            "total": COMMAND_SPACE,
            "coverage_percent": cache.coverage,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable offline unlocking."""
        await self.coordinator.async_set_local_unlock(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable offline unlocking; every unlock asks the cloud again."""
        await self.coordinator.async_set_local_unlock(False)
