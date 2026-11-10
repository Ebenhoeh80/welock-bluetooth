# Contributing to WeLock Home Assistant & Tool Suite

Thank you for your interest in improving this project! We welcome contributions, bug reports, and enhancements.

## Development Workflow

1. Fork the repository on GitHub: `https://github.com/Ebenhoeh80/welock-aistudio`
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/welock-aistudio.git
   cd welock-aistudio
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
- Run tests before opening a pull request:
  ```bash
  pytest tests/
  ruff check .
  ```
- Reference any relevant issues in your PR description.
