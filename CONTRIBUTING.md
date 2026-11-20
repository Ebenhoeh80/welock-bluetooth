# Contributing to WeLock Home Assistant & Tool Suite

Thank you for your interest in improving this project! We welcome contributions, bug reports, and enhancements.

## Development Workflow

1. Fork the repository on GitHub: `https://github.com/Ebenhoeh80/welock-bluetooth`
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/welock-bluetooth.git
   cd welock-bluetooth
   ```
3. Set up a Python 3.10+ virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r tools/requirements-ble.txt
   pip install ruff black mypy pytest
   ```

## Code Standards

- **Python Code**: Format with `black` and lint with `ruff`.
- **Type Annotations**: Provide complete type annotations for all new functions and classes.
- **Home Assistant Standards**: Follow the [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index).
- **Localization**: If you add new strings to `strings.json`, update the translations in `custom_components/welock/translations/` (`de.json`, `en.json`, `es.json`, `fr.json`).

## Pull Request Guidelines

- Ensure your branch is based on `main` and up to date.
- Write clear, descriptive commit messages.
- Run all local checks with one command (the same steps as the CI: ruff, black, complexity, mypy where
  possible, unit tests): `scripts/check.sh` (Linux, macOS, WSL, Git Bash) or
  `powershell -File scripts\check.ps1` (Windows). The tests in `tests_ha/` need Python 3.14 and
  `pip install -r requirements_test.txt`; they run in the CI (job `ha-tests`) or in WSL.
- Or run the steps by hand:
  ```bash
  pytest                                   # live test is skipped automatically
  ruff check custom_components/ tools/ tests/
  black --check custom_components/ tools/ tests/
  ```

## Live Smoke Test (optional, never in CI)

`tests/test_live_smoke.py` (marker `live`) logs in to the real WELOCK cloud and reads the lock list. It is read-only and blocks every unlock and BLE write path.

- Opt in with `WELOCK_LIVE_TEST=1`; it is skipped otherwise and always when `CI` / `GITHUB_ACTIONS` is set.
- Credentials come only from `WELOCK_USER` and `WELOCK_PASSWORD`, set in the current shell. **Never** create a `.env` file with them and never commit them. `.env.example` contains placeholders only.
- The login ends other sessions of the account (e.g. the WeLock app).
- Run: `pytest -m live -s`.
- Before every commit, check `git diff --cached` for passwords and tokens.

## Integration Architecture

- `api.py`: cloud client only (login, device list, unlock command). No polling.
- `ble.py` / `protocol.py`: BLE challenge exchange and command write via the HA Bluetooth stack.
- `coordinator.py`: local state (presence, RSSI, battery); serialises BLE access.
- `config_flow.py`: setup must keep the order discovery → login → selection → BLE check.
- Reference any relevant issues in your PR description.

## AI-assisted contributions

AI assistants are fine to use, with these rules:

- **Say so** in the pull request or issue (for example "prepared with an AI assistant"), so reviewers know to look closely.
- **You are responsible** for the contribution. Read, understand and test everything you submit; do not send unreviewed AI output.
- **Test on real hardware** where the change touches a device. Do not claim a test you did not run.
- **No secrets** in prompts, logs or examples (passwords, tokens, addresses, serial numbers, unlock commands).

The maintainer also works with AI tools. Every change is reviewed and tested by a human before it is released, and pull requests and issues created that way carry a note.
