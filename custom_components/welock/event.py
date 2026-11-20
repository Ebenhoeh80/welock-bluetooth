"""Event platform for WeLock: one event per unlock attempt (the unlock history)."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PATH_OFFLINE, RESULT_FAILED
from .coordinator import WeLockConfigEntry, WeLockCoordinator
from .entity import WeLockEntity
from .stats import UnlockAttempt

EVENT_UNLOCK_CLOUD = "unlock_cloud"
EVENT_UNLOCK_OFFLINE = "unlock_offline"
EVENT_UNLOCK_FAILED = "unlock_failed"


def event_type_for(attempt: UnlockAttempt) -> str:
    """Return the event type of an attempt: failed, or the path that delivered it."""
    if attempt.result == RESULT_FAILED:
        return EVENT_UNLOCK_FAILED
    return EVENT_UNLOCK_OFFLINE if attempt.path == PATH_OFFLINE else EVENT_UNLOCK_CLOUD


# events are pushed by the coordinator
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: WeLockConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the unlock history event entity."""
    async_add_entities([WeLockUnlockEvent(entry.runtime_data, entry)])


class WeLockUnlockEvent(WeLockEntity, EventEntity):
    """Fires once per unlock attempt made through Home Assistant.

    The events appear in the logbook and history. Event attributes: ``path``
    (``cloud``/``offline``/``none``), ``result`` (``confirmed``/``unconfirmed``/
    ``failed``), ``duration_ms``, ``random_factor``, ``error`` (exception class
    only) and whether the stored command was dropped (``evicted``).
    """

    _attr_translation_key = "unlock"
    _attr_event_types = [EVENT_UNLOCK_CLOUD, EVENT_UNLOCK_OFFLINE, EVENT_UNLOCK_FAILED]

    def __init__(self, coordinator: WeLockCoordinator, entry: ConfigEntry) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, entry, "unlock")

    async def async_added_to_hass(self) -> None:
        """Subscribe to unlock attempts."""
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_unlock_listener(self._handle_attempt))

    @callback
    def _handle_attempt(self, attempt: UnlockAttempt) -> None:
        self._trigger_event(
            event_type_for(attempt),
            {
                "path": attempt.path,
                "result": attempt.result,
                "duration_ms": attempt.duration_ms,
                "random_factor": attempt.random_factor,
                "error": attempt.error,
                "evicted": attempt.evicted,
                "connect_ms": attempt.connect_ms,
                "status_ms": attempt.status_ms,
                "command_ms": attempt.command_ms,
                "confirm_ms": attempt.confirm_ms,
                "teardown_ms": attempt.teardown_ms,
                "adv_age_ms": attempt.adv_age_ms,
                "connect_attempts": attempt.connect_attempts,
                "rssi": attempt.rssi,
            },
        )
        self.async_write_ha_state()
