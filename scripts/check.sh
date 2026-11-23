#!/usr/bin/env bash
# Runs a local subset of the CI checks (the HA job needs Home Assistant and Python 3.14).
# Usage: scripts/check.sh      (from any folder; uses .venv if there is one)
set -u
cd "$(dirname "$0")/.."

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  PY=.venv/Scripts/python.exe
else
  PY=python3
fi

failed=()
step() {
  local name=$1
  shift
  echo
  echo "== $name"
  if ! "$@"; then
    failed+=("$name")
  fi
}

step "ruff" "$PY" -m ruff check custom_components/ tools/ tests/ tests_ha/
step "black" "$PY" -m black --check custom_components/ tools/ tests/ tests_ha/
if "$PY" -m xenon --help >/dev/null 2>&1; then
  step "xenon (complexity)" "$PY" -m xenon --max-absolute B --max-modules A --max-average A custom_components
else
  echo; echo "== xenon: not installed (pip install xenon), skipped; the CI runs it"
fi
if "$PY" -m mypy --version >/dev/null 2>&1 && "$PY" -c "import homeassistant" >/dev/null 2>&1; then
  step "mypy" "$PY" -m mypy custom_components/welock
else
  echo; echo "== mypy: needs mypy and Home Assistant (its types) in this environment, skipped; the CI runs it"
fi
step "pytest (unit tests, -m not live)" "$PY" -m pytest -m "not live"

echo
echo "NOTE: tests_ha/ (the integration inside a real Home Assistant core, job 'ha-tests') needs"
echo "      Python 3.14 and pytest-homeassistant-custom-component. It runs in the CI or in WSL/Linux:"
echo "      pip install -r requirements_test.txt && pytest -c tests_ha/pytest.ini tests_ha"

if [ ${#failed[@]} -gt 0 ]; then
  echo
  echo "FAILED: ${failed[*]}"
  exit 1
fi
echo
echo "All local checks passed."
