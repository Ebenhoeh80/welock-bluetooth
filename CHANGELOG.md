# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Offline-unlock switch.** `switch.<name>_offline_unlock` turns the local
  command cache on or off from the UI or an automation. It takes effect
  immediately (no reload) and is remembered across restarts. It is the same
  setting as the option in the *Configure* dialog; the default stays off.
- **Unlock statistics.** Counters per path, `sensor.<name>_unlocks_via_cloud` and
  `sensor.<name>_unlocks_offline`, split into confirmed / unconfirmed / failed
  with the average duration. They survive restarts.
- **Unlock history.** An event entity fires one event per unlock attempt
  (`unlock_cloud`, `unlock_offline`, `unlock_failed`), visible in the logbook, and
  `sensor.<name>_last_unlock_attempt` keeps the last attempts. Both are also part
  of the diagnostics download. No commands, account data or addresses are stored.
- **Import a command table.** The service `welock.import_commands` adds unlock
  commands from a JSON table file in the Home Assistant configuration folder
  (default `welock-oracle-table.json`) to the local command cache of the lock the
  file belongs to (matched by device number). Every entry is validated, the whole
  file is rejected if any entry is invalid, existing commands are never
  overwritten (differences are reported as conflicts) and offline unlocking is
  not switched on. The result (added / unchanged / conflicts / known) is returned
  as the service response.
- **Where the unlock time goes.** Every unlock attempt now records the time of
  each phase in milliseconds (`connect_ms`, `status_ms`, `command_ms`,
  `confirm_ms`, `teardown_ms`): establishing the Bluetooth connection (including
  waiting for a busy adapter), the challenge answer, getting the command (cloud
  round-trip or cache), writing it and waiting for the lock's answer, and
  disconnecting. They are part of the unlock history event, the *Last unlock
  attempt* sensor and the diagnostics download.
- README (en/de): how to verify offline unlocking on your own lock, and a
  measurement table for how long the cylinder stays free after an unlock (not
  measured yet; the 7 s default of the display option is an assumption).

### Fixed
- **Last access sensor keeps its value across restarts.** The sensor is only
  filled by the on-demand `welock.fetch_access_log` service, so it used to fall
  back to `unknown` after every restart or reload of the entry. The last fetched
  entries are now restored from the previous state. It still stays `unknown`
  until the service has been run once (it is never polled, because a cloud login
  ends other sessions of the account).

### Changed
- **Faster unlock state.** After writing the unlock command the integration waited up
  to 15 s for a confirmation from the lock before showing "unlocked". The lock
  normally answers within about half a second, so the wait is now 3 s
  (`CONFIRM_TIMEOUT`). The lock itself already opens as soon as the command is
  written; only the displayed state is faster.
- A stored command that fails while being written to the lock is dropped from the
  cache, so the next unlock for that challenge value asks the cloud again.
- README (en/de): the *Last access* sensor and the access-log service now state
  clearly that the value is only refreshed on demand.

## [2.2.0] - 2026-11-16

### Changed
- **Modernised to `ConfigEntry.runtime_data`.** The coordinator is stored on the
  config entry instead of `hass.data[DOMAIN]`, and the access-log service is now
  registered in `async_setup` (the Home Assistant `action-setup` pattern).
- **Translated exceptions.** Unlock and service errors use `translation_key`
  entries (added to `strings.json` and all four languages) instead of hard-coded
  English strings.
- Synced the `pyproject.toml` version (was stuck at `2.0.0`) with the
  integration version.

### Fixed
- **Battery stays current after a failed read.** A failed Bluetooth battery read
  is now retried after 5 minutes instead of waiting a full battery interval
  (which can be hours).
- **A failing BLE `disconnect()` no longer masks the real error** during the
  exchange teardown.
- **Diagnostics now redact the lock identity** (BLE MAC, serial / device number
  and BLE name), not just the account credentials.
- Corrected the README security note: an intercepted command is **not**
  replay-proof, because the challenge is a single byte (256 possible values).

### Added
- Python 3.13 to the CI test matrix.

## [2.1.4] - 2026-11-15

### Fixed
- **Hassfest compliance for HACS Marketplace submission:** removed
  `aiohttp>=3.9.0` from the manifest requirements. `aiohttp` is a dependency of
  Home Assistant itself and must not be listed by a custom integration; it
  remains available at runtime. Added a hassfest GitHub Action workflow.

## [2.1.3] - 2026-11-13

### Added
- Brand icon for Home Assistant: the integration now ships
  `custom_components/welock/brand/icon.png`, so Home Assistant 2026.3+ shows the
  WeLock icon automatically. Local brand images take priority over the brands
  CDN, so no separate `home-assistant/brands` PR is needed.

### Removed
- Obsolete `archiv/` directory (historical/superseded scripts that were fully
  integrated into `tools/`), plus its references in the READMEs, `pyproject.toml`
  and `tools/README.md`.

## [2.1.2] - 2026-11-13

### Changed
- Renamed the repository from `welock-aistudio` to `welock-bluetooth`; all
  GitHub URLs (documentation, issue tracker, badges, clone paths) now point to
  the new name. GitHub redirects the old URL, so existing links keep working.
- Renamed the integration from "WeLock Smart Lock" to **"WeLock Smart Lock BLE"**
  (`manifest.json` and `hacs.json` `name`), so the local Bluetooth integration is
  distinguishable by name when adding it in Home Assistant and in the HACS store.
- Documentation: English is now the primary `README.md`; the German version moved
  to `README.de.md`, with a language switcher in both and a dynamic release badge.
- CI: bumped `actions/checkout` (v4) and `actions/setup-python` (v5) to v7, off
  the deprecated Node 20 runtime and onto the current major versions.

## [2.1.1] - 2026-11-12

### Fixed
- Corrected the manifest `iot_class` from `cloud_polling` to `local_polling`:
  the integration never polls the cloud; its entity states (Bluetooth presence,
  RSSI, battery) are polled locally over BLE.
- Unified the remaining user-facing runtime strings to English (unlock/access-log
  error messages and the lock-selection labels in the config flow), matching the
  English base language. German, Spanish and French stay available via the
  translation files.

## [2.1.0] - 2026-11-12

### Added
- **Local offline unlocking (experimental, opt-in).** The cloud unlock command
  depends only on the one-byte `randomFactor` of the BLE challenge, so there are
  at most 256 distinct commands per lock. Each command the cloud returns is now
  learned and persisted per config entry (`cache.py`); with the new
  **"Build and use the local command cache"** option enabled, a known challenge
  is answered locally without a cloud round-trip. A cached command is
  byte-identical to the cloud's and is re-validated before every use. The table
  fills itself during normal use even while the option is off (shadow filling).
- Diagnostic sensor **"Learned offline commands"** (count out of 256 and
  coverage), disabled by default.
- **Access log.** New service `welock.fetch_access_log` fetches who opened the
  lock, when and how, into a **"Last access"** diagnostic sensor
  (`/device/GetUnlockRecord`, read-only). Fetched on demand only, because each
  cloud login ends other sessions of the account; the phone number in the raw
  record is intentionally dropped.

### Notes
- Local unlocking is not yet mechanically verified on hardware; it is therefore
  opt-in and the cloud remains the default unlock path.

## [2.0.0] - 2026-11-11

> **Breaking change:** config entries from 1.x cannot be migrated. Remove them and add the integration again. Minimum Home Assistant version is now 2024.11.0.

### Added
- Bluetooth discovery for `WeLock*` BLE modules (`manifest.json` `bluetooth` matcher, dependency `bluetooth_adapters`).
- New modules `ble.py` (BLE transport via HA Bluetooth / `bleak-retry-connector`), `protocol.py` (Nordic UART protocol helpers), `coordinator.py`, `entity.py`.
- "Bluetooth reachable" binary sensor, RSSI sensor from HA Bluetooth advertisements, battery read directly from the lock.
- Options for the relock display time, the BLE battery read interval and the reachability check interval.
- Optional read-only live smoke test against the real WELOCK cloud (`tests/test_live_smoke.py`, marker `live`, opt-in via `WELOCK_LIVE_TEST=1`, never in CI).
- Documentation: setup workflow, entities, options, troubleshooting, upgrade guide, privacy notes and live test in `README.md`; updated `info.md`, `CONTRIBUTING.md`, `SECURITY.md`.

### Changed
- **Config flow follows the WeLock workflow**: cloud login (with warning that it ends app sessions) → lock/BLE module selection from `/Device/GetDevices` → Bluetooth reachability and status/challenge check (no unlock). One config entry per BLE module (unique id = BLE address). Bluetooth discovery for `WeLock*` devices. Proper reauth step.
- **Unlocking works via BLE**: challenge `55 30` → cloud `/Command/UnLock` with `deviceNumber`, `deviceName`, `randomFactor`, `battery` → 15-byte `U1…` command written over the Nordic UART service through the Home Assistant Bluetooth stack (adapters / ESPHome proxies). Minimum 30 s between unlocks.
- **No cloud polling**: presence and RSSI from HA Bluetooth, battery read over BLE (configurable interval). The cloud is only contacted during setup/reauth and for unlock.
- Password is no longer stored twice (`client_id`/`client_secret` aliases removed) and no longer stripped.
- Minimum Home Assistant version raised to 2024.11.0.
- CI runs `pytest -m "not live"`.

### Removed
- WiFiBox gateway sensor, last-unlock-type sensor and the cloud-only unlock call (not supported by the WeLock cloud).
- Legacy `client_id` / `client_secret` configuration keys.

### Migration
- Config entries from 1.3.0 and earlier have no lock selection and must be removed and added again.

## [1.3.0] - 2026-11-11

### Changed
- **License Migration**: Converted the entire project license from Apache 2.0 to the **MIT License** for maximum compatibility with Home Assistant and the HACS open source ecosystem.
- **Eliminated Wake-Up / Manual Touch Assumptions**: Removed all outdated requirements and prompts assuming the lock needs to be manually touched or woken up. WeLock smart locks continuously broadcast standard BLE advertisements. Updated all error handling and documentation to focus on actual connection diagnostics (advertising intervals, single-client Nordic UART Service limitations, RF attenuation through metal doors, and OS Bluetooth permissions).
- **PowerShell Wrapper Argument Splatting**: Fixed all `.ps1` wrappers under `tools/` to transparently pass positional parameters, short options (`-a`, `-u`, `-t`), and long flags (`--address`, `--timeout`, `--json`) without PowerShell parameter binder errors.
- **HACS Action Validation**: Updated `.github/workflows/hacs.yml` to use `hacs/action@main` with `category: integration`.

### Added
- **Consolidated Tools Collection**: Unified `/toolsdev` and `/tools` into a cohesive, standardized CLI suite under `/tools/` with uniform parameter handling and dependency checking. Historical and superseded scripts safely archived under `/archiv/`.
- **Extended Cloud Diagnostics**: Enhanced `tools/welock_cloud_login.py` with `--show-data` (`-s`) and JSON `login_response_data` to inspect raw cloud server payloads without storing credentials.
- **CI Matrix Resiliency**: Added `strategy: fail-fast: false` to `.github/workflows/ci.yml` so that all Python versions (3.10, 3.11, 3.12) execute independently.
- **Diagnostic Tool Unit Tests**: Added unit test suite in `tests/test_tools.py` covering CLI argument parsing, Bluetooth system checks, and device identification heuristics.

### Fixed
- **Fatal NameError in `lock.py`**: Resolved `F821 Undefined name 'model'` in `custom_components/welock/lock.py`.
- **CI Linter & Formatter Compliance**: Fixed all Ruff (E402, F401, I001) and Black formatting checks across `custom_components/`, `tools/`, and `tests/`, strictly adhering to PEP 8 and 100-character line lengths.
- **Cleaned Up Dependencies**: Removed unused protocol imports from `tests/test_tools.py`.

## [1.2.0] - 2026-11-09

### Added
- Complete Home Assistant HACS integration under `custom_components/welock`.
- Config flow with setup UI (`config_flow.py`) and option flow for scan interval and auto-relock delay.
- Entity platforms for `lock`, `sensor` (battery, signal strength, last unlock method), and `binary_sensor` (lock & gateway connectivity).
- Full 4-language localization: German (`de`), English (`en`), Spanish (`es`), and French (`fr`).
- Diagnostics support (`diagnostics.py`) with automatic redaction of sensitive tokens and credentials.
- Local BLE and Cloud diagnostic tool suite under `tools/`:
  - `ble_probe.py`: Non-intrusive Nordic UART GATT inspection.
  - `welock_protocol.py`: Verified challenge-response parsing and battery request protocol.
  - `welock_cloud_login.py`: Zero-dependency cloud authentication and device mapper.
  - `welock_command_probe.py`: Hybrid BLE challenge reading with cloud command acquisition.
  - `welock_unlock_experiment.py`: Safe on-site physical unlock verification.
- Cross-platform launcher scripts:
  - Bash scripts (`run_*.sh`, `welock_tools.sh`) for Linux and macOS.
  - PowerShell scripts (`run_*.ps1`, `welock_tools.ps1`) for Windows.
- GitHub Actions CI workflow for linting (Ruff, Black) and unit tests (Pytest).
- Dependabot configuration and GitHub issue templates.

## [1.0.0] - Initial Release
- Basic prototype for WeLock communication.
