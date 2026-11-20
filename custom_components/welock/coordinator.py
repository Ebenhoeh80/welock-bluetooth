"""Local coordinator: Bluetooth presence, RSSI and battery. Never polls the cloud."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    CannotConnect,
    InvalidAuth,
    LockUnavailable,
    WeLockAccessRecord,
    WeLockApiClient,
    WeLockApiError,
)
from .ble import ExchangeReport, LockNotInRange, WeLockBleError, async_exchange
from .cache import CommandCache
from .const import (
    CONF_ADDRESS,
    CONF_BATTERY_INTERVAL,
    CONF_BLE_NAME,
    CONF_DEVICE_NUMBER,
    CONF_LOCAL_UNLOCK,
    CONF_SCAN_INTERVAL,
    DEFAULT_BATTERY_INTERVAL,
    DEFAULT_LOCAL_UNLOCK,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_UNLOCK_INTERVAL,
    PATH_CLOUD,
    PATH_NONE,
    PATH_OFFLINE,
    RESULT_CONFIRMED,
    RESULT_FAILED,
    RESULT_UNCONFIRMED,
)
from .health import QualityReport, connection_quality
from .issues import WeLockIssues
from .protocol import BatteryResponse
from .stats import PhaseTimes, UnlockAttempt, UnlockStats

_LOGGER = logging.getLogger(__name__)

# After a failed Bluetooth battery read, retry soon instead of waiting a full
# battery interval (which may be several hours).
BATTERY_RETRY_INTERVAL = 300

WeLockConfigEntry = ConfigEntry["WeLockCoordinator"]


def static_options(options: Mapping[str, Any]) -> dict[str, Any]:
    """Return the options that are only read at setup (all but the offline switch)."""
    return {key: value for key, value in options.items() if key != CONF_LOCAL_UNLOCK}


@dataclass(frozen=True)
class _UnlockOutcome:
    """The facts of one unlock attempt that are needed to record it afterwards."""

    path: str
    random_factor: int | None
    report: ExchangeReport
    duration_ms: int
    rssi: int | None


def _phase_times(report: ExchangeReport) -> PhaseTimes:
    """Return the per-phase times of an exchange for an unlock attempt."""
    return {
        "connect_ms": report.connect_ms,
        "status_ms": report.status_ms,
        "command_ms": report.command_ms,
        "confirm_ms": report.confirm_ms,
        "teardown_ms": report.teardown_ms,
        "adv_age_ms": report.adv_age_ms,
        "connect_attempts": report.connect_attempts,
    }


async def choose_unlock_command(
    *,
    local_unlock: bool,
    cache: CommandCache,
    request_cloud: Callable[[BatteryResponse], Awaitable[bytes]],
    state: BatteryResponse,
) -> tuple[str, bytes]:
    """Pick the unlock command for a challenge and say where it came from.

    With the offline switch on and a stored command for exactly this challenge
    value, that command is used (no cloud request, no app logout). In every other
    case - switch off, unknown challenge value, damaged entry - the cloud is asked,
    and what it returns is stored (shadow filling, even while the switch is off).
    Nothing is ever sent that was not either returned by the cloud or validated
    when it was read back from the table.
    """
    if local_unlock:
        cached = cache.get(state.random_factor)
        if cached is not None:
            _LOGGER.debug(
                "Local unlock command for randomFactor=%d (cache hit)", state.random_factor
            )
            return PATH_OFFLINE, cached
    command = await request_cloud(state)
    await cache.async_put(state.random_factor, command)
    return PATH_CLOUD, command


def options_change_is_live(applied: Mapping[str, Any], options: Mapping[str, Any]) -> bool:
    """Return True if only the offline switch differs, so no reload is needed."""
    return static_options(options) == dict(applied)


class WeLockCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Tracks one WeLock BLE module and serialises all BLE access to it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WeLockConfigEntry,
        api: WeLockApiClient,
        cache: CommandCache,
        stats: UnlockStats,
    ) -> None:
        """Initialize the coordinator."""
        scan = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_ADDRESS]}",
            update_interval=timedelta(seconds=scan),
        )
        self.api = api
        self.cache = cache
        self.stats = stats
        self._entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.device_number: str = entry.data[CONF_DEVICE_NUMBER]
        self.ble_name: str = entry.data[CONF_BLE_NAME]
        self._local_unlock: bool = entry.options.get(CONF_LOCAL_UNLOCK, DEFAULT_LOCAL_UNLOCK)
        # Every option except the offline-unlock switch needs a reload to take effect.
        self._applied_options = static_options(entry.options)
        self._unlock_listeners: list[Callable[[UnlockAttempt], None]] = []
        hours = entry.options.get(CONF_BATTERY_INTERVAL, DEFAULT_BATTERY_INTERVAL)
        self._battery_interval = hours * 3600
        self._ble_lock = asyncio.Lock()
        self._last_unlock = 0.0
        self.issues = WeLockIssues(hass, entry.entry_id, entry.title)
        # Connections that are being closed in the background after an unlock.
        self._teardown_tasks: set[asyncio.Task[None]] = set()
        # First battery read a minute after start, so setup is not blocked by BLE.
        self._next_battery_read = time.monotonic() + 60
        self.battery: int | None = None
        # Access log, filled on demand by the fetch_access_log service (never polled).
        self.access_records: list[WeLockAccessRecord] = []

    @property
    def local_unlock(self) -> bool:
        """Whether a learned command may be used instead of asking the cloud."""
        return self._local_unlock

    def apply_options(self, options: Mapping[str, Any]) -> bool:
        """Apply a changed offline-unlock setting without reloading the entry.

        Returns ``False`` when any other option changed; the entry must then be
        reloaded for the change to take effect.
        """
        if not options_change_is_live(self._applied_options, options):
            return False
        self._local_unlock = bool(options.get(CONF_LOCAL_UNLOCK, DEFAULT_LOCAL_UNLOCK))
        self.async_update_listeners()
        return True

    async def async_set_local_unlock(self, enabled: bool) -> None:
        """Switch offline unlocking on or off and remember it across restarts."""
        self._local_unlock = enabled
        self.hass.config_entries.async_update_entry(
            self._entry, options={**self._entry.options, CONF_LOCAL_UNLOCK: enabled}
        )
        self.async_update_listeners()

    def async_add_unlock_listener(
        self, listener: Callable[[UnlockAttempt], None]
    ) -> Callable[[], None]:
        """Call ``listener`` for every recorded unlock attempt; returns the remover."""
        self._unlock_listeners.append(listener)

        def _remove() -> None:
            if listener in self._unlock_listeners:
                self._unlock_listeners.remove(listener)

        return _remove

    async def _async_record_unlock(self, attempt: UnlockAttempt) -> None:
        """Store an attempt and tell the statistics entities about it."""
        await self.stats.async_record(attempt)
        for listener in list(self._unlock_listeners):
            listener(attempt)
        self.issues.update_quality(self.quality_report)
        self.async_update_listeners()

    @property
    def quality_report(self) -> QualityReport:
        """How well Home Assistant reaches the lock, from the latest unlock attempts."""
        return connection_quality(list(self.stats.history), (self.data or {}).get("rssi"))

    def _run_teardown_in_background(
        self, teardown: Awaitable[None], report: ExchangeReport, recorded: asyncio.Event
    ) -> None:
        """Close the connection after the unlock was reported; hold the BLE lock until done.

        The lock stays reserved so no other exchange starts while the connection is
        still closing. The teardown time is added to the recorded attempt afterwards.
        """

        async def _run() -> None:
            try:
                await teardown
            finally:
                self._ble_lock.release()
            try:
                await asyncio.wait_for(recorded.wait(), 10)
            except asyncio.TimeoutError:
                return
            attempt = self.stats.latest
            if (
                attempt is not None
                and attempt.teardown_ms is None
                and await self.stats.async_update_latest(attempt, teardown_ms=report.teardown_ms)
            ):
                self.async_update_listeners()

        task = self.hass.async_create_background_task(_run(), f"welock teardown {self.address}")
        self._teardown_tasks.add(task)
        task.add_done_callback(self._teardown_tasks.discard)

    async def async_shutdown(self) -> None:
        """Let connections that are still closing finish, then shut down."""
        if self._teardown_tasks:
            await asyncio.wait(self._teardown_tasks, timeout=10)
        await super().async_shutdown()

    def _map_unlock_error(self, err: Exception) -> HomeAssistantError | None:
        """Translate an unlock error for the user; ``None`` if it is not one of ours."""
        if isinstance(err, LockNotInRange):
            return HomeAssistantError(
                translation_domain=DOMAIN, translation_key="lock_not_in_range"
            )
        if isinstance(err, InvalidAuth):
            self._entry.async_start_reauth(self.hass)
            return HomeAssistantError(translation_domain=DOMAIN, translation_key="reauth_required")
        if isinstance(err, CannotConnect | LockUnavailable):
            return HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_error",
                translation_placeholders={"error": str(err)},
            )
        if isinstance(err, WeLockBleError):
            return HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bluetooth_error",
                translation_placeholders={"error": str(err)},
            )
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        info = bluetooth.async_last_service_info(self.hass, self.address, connectable=False)
        present = bluetooth.async_address_present(self.hass, self.address, connectable=True)
        if (
            present
            and self._battery_interval > 0
            and time.monotonic() >= self._next_battery_read
            and not self._ble_lock.locked()
        ):
            self._next_battery_read = time.monotonic() + self._battery_interval
            try:
                async with self._ble_lock:
                    state = await async_exchange(self.hass, self.address)
                self.battery = state.battery
            except WeLockBleError as err:
                # Do not leave the battery unknown for a whole interval (hours):
                # retry after a short delay instead.
                self._next_battery_read = time.monotonic() + min(
                    BATTERY_RETRY_INTERVAL, self._battery_interval
                )
                _LOGGER.debug("Battery read from %s failed: %s", self.address, err)
        self.issues.update_presence(present)
        self.issues.update_battery(self.battery)
        return {
            "present": present,
            "rssi": info.rssi if info else None,
            "battery": self.battery,
        }

    def _ensure_unlock_possible(self) -> None:
        """Refuse an unlock that is too soon after the last one or while the lock is busy."""
        wait = MIN_UNLOCK_INTERVAL - (time.monotonic() - self._last_unlock)
        if wait > 0:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unlock_too_soon",
                translation_placeholders={
                    "wait": str(int(wait) + 1),
                    "min_interval": str(MIN_UNLOCK_INTERVAL),
                },
            )
        if self._ble_lock.locked():
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="lock_busy")

    async def async_unlock(self) -> None:
        """Challenge -> cloud command -> BLE write. Raises HomeAssistantError."""
        self._ensure_unlock_possible()

        started = time.monotonic()
        report = ExchangeReport()
        path = PATH_NONE
        random_factor: int | None = None

        async def _cloud(state: BatteryResponse) -> bytes:
            nonlocal path
            path = PATH_CLOUD  # recorded even if the cloud request itself fails
            return await self.api.async_request_unlock_command(
                self.device_number, self.ble_name, state.random_factor, state.battery
            )

        async def _command(state: BatteryResponse) -> bytes:
            nonlocal path, random_factor
            random_factor = state.random_factor
            path, command = await choose_unlock_command(
                local_unlock=self._local_unlock,
                cache=self.cache,
                request_cloud=_cloud,
                state=state,
            )
            return command

        error: Exception | None = None
        recorded = asyncio.Event()
        handed_off = False

        def _hand_off(teardown: Awaitable[None]) -> None:
            nonlocal handed_off
            handed_off = True
            self._run_teardown_in_background(teardown, report, recorded)

        await self._ble_lock.acquire()
        try:
            state = await async_exchange(
                self.hass, self.address, _command, report=report, teardown_runner=_hand_off
            )
        except Exception as err:  # noqa: BLE001 - recorded, then re-raised below
            error = err
        finally:
            if not handed_off:
                self._ble_lock.release()

        outcome = _UnlockOutcome(
            path=path,
            random_factor=random_factor,
            report=report,
            duration_ms=round((time.monotonic() - started) * 1000),
            # The signal strength when the connection started beats the polled value,
            # which can be up to a minute old.
            rssi=report.rssi if report.rssi is not None else (self.data or {}).get("rssi"),
        )
        if error is not None:
            await self._async_record_failed_unlock(error, outcome)
            mapped = self._map_unlock_error(error)
            if mapped is None:
                raise error
            raise mapped from error

        await self._async_record_successful_unlock(state, outcome)
        recorded.set()
        self.async_set_updated_data({**(self.data or {}), "battery": state.battery})

    async def _async_record_failed_unlock(self, error: Exception, outcome: _UnlockOutcome) -> None:
        """Record a failed attempt; a stored command that failed while being written is dropped."""
        evicted = False
        if (
            outcome.path == PATH_OFFLINE
            and outcome.report.command_written
            and outcome.random_factor is not None
        ):
            # It is not trusted again; the next attempt for this challenge asks the cloud.
            evicted = await self.cache.async_discard(outcome.random_factor)
            _LOGGER.warning(
                "Offline unlock for randomFactor=%d failed; the stored command was dropped",
                outcome.random_factor,
            )
        await self._async_record_unlock(
            UnlockAttempt(
                time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                path=outcome.path,
                result=RESULT_FAILED,
                duration_ms=outcome.duration_ms,
                random_factor=outcome.random_factor,
                error=type(error).__name__,
                rssi=outcome.rssi,
                evicted=evicted,
                **_phase_times(outcome.report),
            )
        )

    async def _async_record_successful_unlock(
        self, state: BatteryResponse, outcome: _UnlockOutcome
    ) -> None:
        """Record a completed unlock and take over the battery level the lock reported."""
        self._last_unlock = time.monotonic()
        self.battery = state.battery
        self.issues.update_battery(self.battery)
        await self._async_record_unlock(
            UnlockAttempt(
                time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                path=outcome.path,
                result=RESULT_CONFIRMED if outcome.report.confirmed else RESULT_UNCONFIRMED,
                duration_ms=outcome.duration_ms,
                random_factor=outcome.random_factor,
                rssi=outcome.rssi,
                **_phase_times(outcome.report),
            )
        )

    async def async_fetch_access_log(self, page_size: int) -> int:
        """Fetch the lock's access log from the cloud (on demand only).

        Returns the number of records fetched. Logs in and therefore ends other
        sessions of the account, so this runs only when the user triggers it.
        """
        try:
            records = await self.api.async_get_access_log(self.device_number, page_size=page_size)
        except InvalidAuth as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="reauth_required"
            ) from err
        except (CannotConnect, WeLockApiError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_error",
                translation_placeholders={"error": str(err)},
            ) from err

        self.access_records = records
        self.async_update_listeners()
        return len(records)
