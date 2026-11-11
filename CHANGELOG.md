# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Config flow follows the WeLock workflow**: cloud login (with warning that it ends app sessions) → lock/BLE module selection from `/Device/GetDevices` → Bluetooth reachability and status/challenge check (no unlock). One config entry per BLE module (unique id = BLE address). Bluetooth discovery for `WeLock*` devices. Proper reauth step.
- **Unlocking works via BLE**: challenge `55 30` → cloud `/Command/UnLock` with `deviceNumber`, `deviceName`, `randomFactor`, `battery` → 15-byte `U1…` command written over the Nordic UART service through the Home Assistant Bluetooth stack (adapters / ESPHome proxies). Minimum 30 s between unlocks.
- **No cloud polling**: presence and RSSI from HA Bluetooth, battery read over BLE (configurable interval). The cloud is only contacted during setup/reauth and for unlock.
- Password is no longer stored twice (`client_id`/`client_secret` aliases removed) and no longer stripped.
- Minimum Home Assistant version raised to 2024.11.0.

### Removed
- WiFiBox gateway sensor, last-unlock-type sensor and the cloud-only unlock call (not supported by the WeLock cloud).

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
