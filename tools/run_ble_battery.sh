#!/usr/bin/env bash
# ==============================================================================
# WeLock Battery & Status Reader (Linux / macOS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}:${SCRIPT_DIR}:${PYTHONPATH:-}"

PYTHON_BIN=""
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "FEHLER: Kein Python-Interpreter gefunden." >&2
    echo "Bitte installieren Sie Python 3.10 oder neuer." >&2
    exit 1
fi

"$PYTHON_BIN" -c '
import sys
if sys.version_info < (3, 10):
    sys.exit(1)
' 2>/dev/null || {
    echo "FEHLER: Python 3.10 oder neuer ist erforderlich." >&2
    echo "Gefundener Interpreter: $("$PYTHON_BIN" --version 2>&1)" >&2
    exit 1
}

if ! "$PYTHON_BIN" -c 'import bleak' 2>/dev/null; then
    echo "======================================================================" >&2
    echo "FEHLER: Das erforderliche Python-Paket 'bleak' ist nicht installiert!" >&2
    echo "======================================================================" >&2
    echo "Installation via pip:" >&2
    echo "  pip install -r \"${SCRIPT_DIR}/requirements-ble.txt\"" >&2
    echo "======================================================================" >&2
    exit 1
fi

exec "$PYTHON_BIN" "${SCRIPT_DIR}/ble_battery.py" "$@"
