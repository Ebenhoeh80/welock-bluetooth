# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
