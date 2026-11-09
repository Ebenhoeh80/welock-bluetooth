# WeLock Smart Lock — Home Assistant HACS Integration & BLE Diagnose-Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/version-v1.2.0-blue.svg?style=for-the-badge)](https://github.com/Ebenhoeh80/welock/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-languages--sprachen--idiomas--langues)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg?style=for-the-badge)](LICENSE)

Vollständige Suite für **WeLock Smart Door Locks** (Touch41, SECBN51, PCB41) und das **WeLock WiFiBox Gateway**:
1. 🏠 **Home Assistant HACS Integration** (`custom_components/welock`): Integration in Home Assistant mit grafischem ConfigFlow, Sensorwerten (Batterie, Signal, letzte Entriegelung) und 4-Sprachen-Lokalisierung.
2. 🔬 **BLE & Cloud Diagnose-Tools** ([`tools/`](tools/README.md)): Python-Werkzeuge zur lokalen BLE-Suche (MAC-Adresse, BLE-Name, GATT-Inspektion), Challenge-Response-Analyse und Cloud-Test-Entriegelungen ohne Gateway vor Ort.

---

## 🌍 Languages / Sprachen / Idiomas / Langues

Die Home Assistant Integration und Benutzeroberfläche sind vollständig in 4 Sprachen lokalisiert:
* 🇩🇪 **Deutsch** (Vollständige Benutzeroberfläche, Konfigurationsassistent & Sensorbeschriftung)
* 🇬🇧 **English** (Full UI, config flow, option flow, and sensor attributes)
* 🇪🇸 **Español** (Interfaz completa, asistente de configuración y entidades)
* 🇫🇷 **Français** (Interface complète, flux de configuration et entités)

---

## 🏗 Repository-Architektur

```text
welock/
├── custom_components/
│   └── welock/                   # Home Assistant HACS Integration
│       ├── __init__.py           # Coordinator & Integration Lifecycle
│       ├── manifest.json         # HA-Komponenten-Manifest
│       ├── const.py              # Konstanten & API-Endpunkte
│       ├── config_flow.py        # Grafische Einrichtung in Home Assistant
│       ├── api.py                # Asynchroner WeLock Cloud API-Client
│       ├── lock.py               # Schloss-Plattform (Entriegeln & Auto-Relock)
│       ├── sensor.py             # Batterie, Signalstärke, Entriegelungsmethode
│       ├── binary_sensor.py      # Verbindungsstatus für Schloss & WiFiBox
│       ├── strings.json          # Basisübersetzungen
│       └── translations/         # de.json, en.json, es.json, fr.json
│
├── tools/                        # Lokale BLE- & Cloud-Diagnosetools (Details: tools/README.md)
│   ├── ble_probe.py              # BLE-Inspektion (Adresse & GATT-Services)
│   ├── welock_cloud_login.py     # WeLock Cloud-Login & Geräteübersicht
│   ├── welock_command_probe.py   # Hybrid-Probe (BLE Challenge + Cloud-Command)
│   ├── welock_unlock_experiment.py # Autorisierter Entriegelungstest via BLE
│   ├── welock_protocol.py        # Protokolldefinition (Battery Request/Response)
│   ├── requirements-ble.txt      # Python-Abhängigkeit: bleak>=0.22,<3
│   ├── run_ble_probe.sh / .ps1   # Startskripte für ble_probe (Linux/macOS / Windows)
│   ├── run_cloud_login.sh / .ps1 # Startskripte für cloud_login
│   ├── run_command_probe.sh / .ps1 # Startskripte für command_probe
│   ├── run_unlock_experiment.sh / .ps1 # Startskripte für unlock_experiment
│   ├── welock_tools.sh / .ps1    # Interaktives Hauptmenü für alle Tools
│   └── README.md                 # Umfassende Werkzeug-Dokumentation
│
├── hacs.json                     # HACS / Marketplace Metadaten
├── info.md                       # HACS Store-Beschreibung
├── README.md                     # Hauptdokumentation (diese Datei)
└── LICENSE                       # Apache 2.0 Lizenz
```

---

## 🛠 Teil 1: BLE & Cloud Diagnose-Werkzeuge (`tools/`)

Wenn Sie die **BLE-MAC-Adresse**, den **BLE-Gerätenamen** oder den **Akkustand** Ihres Schlosses direkt über Bluetooth ermitteln oder Cloud-Befehle analysieren möchten:

### ⚠️ Wichtige Voraussetzung: Python-Modul `bleak`
Für die BLE-Skripte wird zwingend das Python-Modul **`bleak`** benötigt:
```bash
pip install -r tools/requirements-ble.txt
```

### Startskripte für Linux / macOS:
```bash
# Interaktives Menü starten:
./tools/welock_tools.sh

# Oder direkt ein bestimmtes Werkzeug starten:
./tools/run_ble_probe.sh --address "AA:BB:CC:DD:EE:FF" --connect
./tools/run_cloud_login.sh
./tools/run_command_probe.sh
./tools/run_unlock_experiment.sh
```

### Startskripte für Windows (PowerShell):
```powershell
# Interaktives Menü starten:
.\tools\welock_tools.ps1

# Oder direkt ein bestimmtes Werkzeug starten:
.\tools\run_ble_probe.ps1 --address "AA:BB:CC:DD:EE:FF" --connect
.\tools\run_cloud_login.ps1
.\tools\run_command_probe.ps1
.\tools\run_unlock_experiment.ps1
```

> 📖 **Detaillierte Werkzeug-Dokumentation:** Eine vollständige Anleitung mit allen Parametern, Protokoll-Details und Fehlerbehebungen finden Sie in der [**tools/README.md**](tools/README.md).

---

## 🏠 Teil 2: Home Assistant HACS Installation

### Methode 1: Über HACS (Empfohlen)

1. Öffnen Sie **Home Assistant** und navigieren Sie zu **HACS** (bzw. Community Store / Marketplace).
2. Klicken Sie oben rechts auf das Drei-Punkte-Menü und wählen Sie **Benutzerdefinierte Repositories** (Custom repositories).
3. Geben Sie die Repository-URL ein:
   ```text
   https://github.com/Ebenhoeh80/welock
   ```
4. Wählen Sie als Kategorie **Integration** und klicken Sie auf **Hinzufügen**.
5. Suchen Sie nach **WeLock Smart Lock**, klicken Sie auf **Herunterladen** und starten Sie Home Assistant neu.

### Methode 2: Manuelle Installation

1. Laden Sie das neueste Release-Archiv herunter oder klonen Sie dieses Repository.
2. Kopieren Sie den Ordner `custom_components/welock` in Ihr Home Assistant Konfigurationsverzeichnis:
   ```bash
   /config/custom_components/welock/__init__.py
   /config/custom_components/welock/manifest.json
   ...
   ```
3. Starten Sie Home Assistant neu.

---

## 🔑 Zugangsdaten aus der WeLock Mobile-App abrufen

Für die permanente Anbindung über Home Assistant benötigen Sie eine `Client-ID` und ein `Client-Secret`:

1. Öffnen Sie die offizielle **WeLock App** auf Ihrem Smartphone (iOS oder Android).
2. Stellen Sie sicher, dass Ihr Schloss mit einer **WeLock WiFiBox** verbunden ist.
3. Öffnen Sie das Seitenmenü (☰) in der App.
4. Tippen Sie auf das **Home Assistant** Symbol.
5. Kopieren Sie Ihre generierte **Client-ID** und das **Client-Secret**.

---

## 🚀 Einrichtung in Home Assistant

1. In Home Assistant öffnen Sie **Einstellungen** -> **Geräte & Dienste**.
2. Klicken Sie unten rechts auf **Integration hinzufügen**.
3. Suchen Sie nach **WeLock Smart Lock**.
4. Geben Sie Ihre `Client-ID` und Ihr `Client-Secret` ein.
5. Ihre WeLock-Schlösser und die WiFiBox werden automatisch erkannt und eingerichtet!

---

## 💡 Lovelace & Automations-Beispiele (YAML)

### 1. Kachel-Karte (Tile Card) für das Dashboard
```yaml
type: tile
entity: lock.welock_haustur
name: Haustür Schloss
features:
  - type: lock-commands
```

### 2. Warnung bei schwacher Batterie (< 20%)
```yaml
alias: "WeLock: Warnung bei schwacher Schloss-Batterie"
description: "Sendet eine Benachrichtigung, wenn die Batterien unter 20% fallen"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_haustur_battery
    below: 20
action:
  - action: notify.notify
    data:
      title: "⚠️ WeLock Batterie fast leer"
      message: "Batteriestand: {{ states('sensor.welock_haustur_battery') }}%. Bitte AAA-Batterien wechseln."
mode: single
```

### 3. Haustür mit NFC-Tag oder RFID-Chip öffnen
```yaml
alias: "WeLock: Haustür mit NFC-Tag entriegeln"
description: "Entriegelt das WeLock-Schloss beim Scannen eines authorisierten NFC-Chips"
trigger:
  - platform: tag
    tag_id: 84a7-9f20-haustuer-nfc
action:
  - action: lock.unlock
    target:
      entity_id: lock.welock_haustur
mode: restart
```

---

## 📄 Lizenz

Lizenziert unter der Apache License 2.0. Siehe [LICENSE](LICENSE) für Details.
