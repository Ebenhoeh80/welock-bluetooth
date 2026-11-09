#!/usr/bin/env bash
# ==============================================================================
# WeLock Diagnostic Tools - Interaktives Hauptmenü (Linux / macOS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

echo "======================================================================"
echo "          🔐 WeLock BLE & Cloud Diagnose-Werkzeugkasten             "
echo "======================================================================"
echo "Dieses Menü erleichtert die Ausführung der Testskripte unter /tools."
echo ""
echo "1) BLE-Geräte-Inspektion (ble_probe.py)"
echo "   -> Untersucht ein BLE-Gerät und prüft GATT-Services/Characteristics"
echo ""
echo "2) WeLock Cloud-Login & Geräteübersicht (welock_cloud_login.py)"
echo "   -> Prüft Zugangsdaten und listet Schlosscodes & BLE-Namen auf"
echo ""
echo "3) Hybrid Command-Probe (welock_command_probe.py)"
echo "   -> Liest Challenge/Batterie per BLE & holt Cloud-Befehl (KEIN Unlock)"
echo ""
echo "4) Autorisierter Entriegelungstest (welock_unlock_experiment.py)"
echo "   -> Sendet Cloud-Befehl per BLE an das Schloss (ECHTE Entriegelung!)"
echo ""
echo "5) Virtuelle Python-Umgebung erstellen & Abhängigkeiten installieren"
echo ""
echo "0) Beenden"
echo "======================================================================"

read -rp "Bitte Option wählen [0-5]: " choice

case "$choice" in
    1)
        read -rp "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF): " addr
        read -rp "Verbindung und GATT-Services prüfen? (j/N): " do_connect
        if [[ "$do_connect" =~ ^[jJyY]$ ]]; then
            bash "${SCRIPT_DIR}/run_ble_probe.sh" --address "$addr" --connect
        else
            bash "${SCRIPT_DIR}/run_ble_probe.sh" --address "$addr"
        fi
        ;;
    2)
        bash "${SCRIPT_DIR}/run_cloud_login.sh"
        ;;
    3)
        bash "${SCRIPT_DIR}/run_command_probe.sh"
        ;;
    4)
        bash "${SCRIPT_DIR}/run_unlock_experiment.sh"
        ;;
    5)
        echo "Erstelle virtuelle Python-Umgebung unter ${REPO_ROOT}/.venv..."
        python3 -m venv "${REPO_ROOT}/.venv"
        echo "Installiere Abhängigkeiten aus ${SCRIPT_DIR}/requirements-ble.txt..."
        "${REPO_ROOT}/.venv/bin/pip" install --upgrade pip
        "${REPO_ROOT}/.venv/bin/pip" install -r "${SCRIPT_DIR}/requirements-ble.txt"
        echo "Virtuelle Umgebung erfolgreich eingerichtet!"
        ;;
    0)
        echo "Auf Wiedersehen!"
        exit 0
        ;;
    *)
        echo "Ungültige Auswahl." >&2
        exit 1
        ;;
esac
