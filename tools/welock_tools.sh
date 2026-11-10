#!/usr/bin/env bash
# ==============================================================================
# WeLock Diagnostic Tools - Interaktives Hauptmenü (Linux / macOS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}:${SCRIPT_DIR}:${PYTHONPATH:-}"

echo "======================================================================"
echo "          🔐 WeLock BLE & Cloud Diagnose-Werkzeugkasten             "
echo "======================================================================"
echo "Dieses Menü erleichtert die Ausführung der Testskripte unter /tools."
echo ""
echo "1) BLE-Gerätesuche & WeLock-Erkennung (run_ble_scan.sh)"
echo "   -> Sucht Geräte in Reichweite und hebt WeLock-Zylinder hervor"
echo ""
echo "2) Akkustand & Challenge per BLE auslesen (run_ble_battery.sh)"
echo "   -> Liest Batteriestand in % und Challenge-Faktor direkt aus"
echo ""
echo "3) BLE-Geräte-Inspektion (run_ble_probe.sh)"
echo "   -> Untersucht ein BLE-Gerät und prüft GATT-Services/Characteristics"
echo ""
echo "4) WeLock Cloud-Login & Geräteübersicht (run_cloud_login.sh)"
echo "   -> Prüft Zugangsdaten und listet Schlosscodes & BLE-Namen auf"
echo ""
echo "5) Hybrid Command-Probe (run_command_probe.sh)"
echo "   -> Liest Challenge/Batterie per BLE & holt Cloud-Befehl (KEIN Unlock)"
echo ""
echo "6) Autorisierter Entriegelungstest (run_unlock.sh)"
echo "   -> Sendet Cloud-Befehl per BLE an das Schloss (ECHTE Entriegelung!)"
echo ""
echo "7) System- & Abhängigkeitsprüfung (dependency_check.py)"
echo ""
echo "8) Virtuelle Python-Umgebung erstellen & bleak installieren"
echo ""
echo "0) Beenden"
echo "======================================================================"

read -rp "Bitte Option wählen [0-8]: " choice

case "$choice" in
    1)
        read -rp "Nur WeLock-Schlösser anzeigen? (j/N): " welock_only
        if [[ "$welock_only" =~ ^[jJyY]$ ]]; then
            bash "${SCRIPT_DIR}/run_ble_scan.sh" --welock-only
        else
            bash "${SCRIPT_DIR}/run_ble_scan.sh"
        fi
        ;;
    2)
        read -rp "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF): " addr
        bash "${SCRIPT_DIR}/run_ble_battery.sh" "$addr"
        ;;
    3)
        read -rp "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF): " addr
        read -rp "Verbindung und GATT-Services prüfen? (j/N): " do_connect
        if [[ "$do_connect" =~ ^[jJyY]$ ]]; then
            bash "${SCRIPT_DIR}/run_ble_probe.sh" --address "$addr" --connect
        else
            bash "${SCRIPT_DIR}/run_ble_probe.sh" --address "$addr"
        fi
        ;;
    4)
        bash "${SCRIPT_DIR}/run_cloud_login.sh"
        ;;
    5)
        bash "${SCRIPT_DIR}/run_command_probe.sh"
        ;;
    6)
        bash "${SCRIPT_DIR}/run_unlock.sh"
        ;;
    7)
        python3 "${SCRIPT_DIR}/dependency_check.py"
        ;;
    8)
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
