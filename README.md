# WeLock Smart Lock — Home Assistant HACS Integration & BLE Diagnose-Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/version-v1.3.0-blue.svg?style=for-the-badge)](https://github.com/Ebenhoeh80/welock-aistudio/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-languages--sprachen--idiomas--langues)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

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
│   ├── ble_scan.py               # BLE-Gerätesuche & WeLock-Erkennung (RSSI, Mac, Name)
│   ├── ble_battery.py            # Akkustand (%) & Challenge per BLE auslesen
│   ├── ble_probe.py              # BLE-Inspektion (Adresse & GATT-Services/Nordic UART)
│   ├── welock_cloud_login.py     # WeLock Cloud-Login & Geräteübersicht (deviceNumber)
│   ├── welock_command_probe.py   # Hybrid-Probe (BLE Challenge + Cloud-Command, kein Unlock)
│   ├── welock_unlock.py          # Autorisierter Entriegelungstest via BLE + Cloud
│   ├── welock_tools.py           # Interaktives Python-Hauptmenü für alle Werkzeuge
│   ├── dependency_check.py       # System- & Abhängigkeitsprüfung (Python, Bleak, Bluetooth)
│   ├── welock_protocol.py        # Protokolldefinition & UUID-Konstanten
│   ├── requirements-ble.txt      # Python-Abhängigkeit: bleak>=0.22.0,<3.0.0
│   ├── run_ble_scan.sh / .ps1    # Startskripte für BLE-Suche (Linux/macOS / Windows)
│   ├── run_ble_battery.sh / .ps1 # Startskripte für Akku-Abfrage
│   ├── run_ble_probe.sh / .ps1   # Startskripte für ble_probe
│   ├── run_cloud_login.sh / .ps1 # Startskripte für cloud_login
│   ├── run_command_probe.sh / .ps1 # Startskripte für command_probe
│   ├── run_unlock.sh / .ps1      # Startskripte für autorisierten Unlock-Test
│   ├── welock_tools.sh / .ps1    # Interaktives Hauptmenü für alle Tools
│   └── README.md                 # Umfassende Werkzeug-Dokumentation
│
├── archiv/                       # Revisionssicher archivierte Entwicklungsstände
├── hacs.json                     # HACS / Marketplace Metadaten
├── info.md                       # HACS Store-Beschreibung
├── README.md                     # Hauptdokumentation (diese Datei)
└── LICENSE                       # MIT-Lizenz
```

---

## 📋 Voraussetzungen (Prerequisites)

Damit Sie sowohl die **Home Assistant Integration** als auch die **BLE-Diagnosetools** erfolgreich einsetzen können, beachten Sie bitte folgende System-, Hardware- und Softwarevoraussetzungen:

### 1. 📡 Bluetooth-Hardware & Reichweite (für BLE-Tools)
* **Bluetooth-Empfänger:** Ein Rechner oder Bluetooth-Adapter mit Unterstützung für mindestens **Bluetooth 4.0 Low Energy (BLE)** (integriertes Modul oder USB-BLE-Dongle).
* **Funkreichweite:** Das Schloss muss sich in direkter Funkreichweite des BLE-Empfängers befinden (optimal **unter 3 bis 5 Metern**). Massive Brandschutztüren, Stahlarmierungen oder dicke Außenmauern dämpfen das 2.4-GHz-BLE-Signal stark.
* **📡 Kontinuierliches BLE-Advertising & Verbindungsverhalten:**
  WeLock Smart Locks senden kontinuierlich standardkonforme BLE-Advertising-Pakete aus und sind **jederzeit ohne physische Interaktion, Tastendruck oder Berührung** ansprechbar.
  Sollte eine Verbindung oder Erkennung fehlschlagen, liegt dies an folgenden technischen Ursachen:
  - **Advertising-Intervall & Timing:** Das Schloss sendet Pakete in Intervallen. Ein kurzer Scan (unter 5–10 s) kann das Zeitfenster verfehlen. Erhöhen Sie den Scan-Timeout mit `--timeout 15` oder `20`.
  - **Single-Client-Limitierung:** Der BLE-Chip des Schlosses akzeptiert nur **eine einzige aktive Verbindung gleichzeitig**. Ist ein Smartphone (WeLock-App im Vordergrund) oder eine aktive WeLock WiFiBox verbunden, lehnt das Schloss neue Verbindungen ab.
  - **Signaldämpfung & Hindernisse:** Brandschutztüren, Metallbeschläge oder dicke Wände dämpfen 2.4-GHz-Funk; der Empfänger sollte in 3–5 m Reichweite stehen.
  - **Betriebssystem- & Adapterberechtigungen:** Host-Adapter muss aktiv sein (z. B. `rfkill unblock bluetooth` unter Linux, Terminal-Berechtigungen unter macOS/Windows).
* **🔋 Batteriezustand:** Mindestens 3 frische AAA Alkaline- oder Lithium-Batterien (1.5V). Bei niedrigem Batteriestand (< 20%) deaktiviert die Firmware oft Funkbefehle.

### 2. 🌐 WeLock WiFiBox Gateway (für Home Assistant)
* Für die dauerhafte, zuverlässige Steuerung in Home Assistant (auch wenn der Home Assistant Host nicht in BLE-Reichweite der Haustür steht) wird das offizielle **WeLock WiFiBox Gateway (2.4 GHz WLAN)** benötigt.
* Das Schloss muss in der offiziellen WeLock Smartphone-App mit dieser WiFiBox gekoppelt sein.

### 3. 🐍 Software- & Betriebssystem-Voraussetzungen
* **Python-Version:** Mindestens **Python 3.10** oder neuer (getestet unter Python 3.10, 3.11 und 3.12).
* **Python-Bibliothek `bleak`:** Für die Ausführung aller BLE-Werkzeuge (`pip install -r tools/requirements-ble.txt` bzw. `pip install bleak>=0.22.0,<3.0.0`).
* **Betriebssystemspezifische Berechtigungen:**
  * **Linux:** Installierter und aktiver BlueZ-Stack (`systemctl status bluetooth`). Der ausführende Benutzer sollte Mitglied der Gruppe `bluetooth` oder `netdev` sein. Prüfen Sie mit `rfkill list`, dass Bluetooth nicht *soft-blocked* ist.
  * **macOS:** macOS 12+ mit Apple CoreBluetooth. Dem ausführenden Terminal (Terminal.app, iTerm2 oder IDE wie VS Code) muss in den Systemeinstellungen unter *Datenschutz & Sicherheit ➔ Bluetooth* die Erlaubnis für Bluetooth erteilt sein.
  * **Windows:** Windows 10 (ab Build 1809) oder Windows 11 mit aktiviertem Bluetooth und erteilten App-Berechtigungen für Bluetooth und Standortdienste.
* **Home Assistant:** Version **2024.1.0** oder neuer mit installiertem **HACS** (Home Assistant Community Store) oder Dateizugriff auf `/config/custom_components/`.

### 4. 🔑 WeLock-Konto & API-Schlüssel
* Ein aktives Benutzerkonto in der offiziellen **WeLock App** (iOS / Android).
* Ihre persönliche **Client-ID** und Ihr **Client-Secret** (abrufbar in der WeLock App unter: *Menü ➔ Home Assistant*).

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
./tools/run_ble_scan.sh                     # BLE-Geräte & Schlösser suchen
./tools/run_ble_battery.sh "AA:BB:CC:..."   # Akkustand & Challenge abfragen
./tools/run_ble_probe.sh --address "AA:BB:..." --connect
./tools/run_cloud_login.sh                  # Cloud-Konto & Geräte prüfen
./tools/run_command_probe.sh                # Test Challenge + Cloud-Befehl
./tools/run_unlock.sh                       # Autorisierter Entriegelungstest
```

### Startskripte für Windows (PowerShell):
```powershell
# Interaktives Menü starten:
.\tools\welock_tools.ps1

# Oder direkt ein bestimmtes Werkzeug starten:
.\tools\run_ble_scan.ps1                    # BLE-Geräte & Schlösser suchen
.\tools\run_ble_battery.ps1 "AA:BB:CC:..."  # Akkustand & Challenge abfragen
.\tools\run_ble_probe.ps1 --address "AA:BB:..." --connect
.\tools\run_cloud_login.ps1                 # Cloud-Konto & Geräte prüfen
.\tools\run_command_probe.ps1               # Test Challenge + Cloud-Befehl
.\tools\run_unlock.ps1                      # Autorisierter Entriegelungstest
```

> 📖 **Detaillierte Werkzeug-Dokumentation:** Eine vollständige Anleitung mit allen Parametern, Protokoll-Details und Fehlerbehebungen finden Sie in der [**tools/README.md**](tools/README.md).

---

## 🏠 Teil 2: Home Assistant HACS Installation

### Methode 1: Über HACS (Empfohlen)

1. Öffnen Sie **Home Assistant** und navigieren Sie zu **HACS** (bzw. Community Store / Marketplace).
2. Klicken Sie oben rechts auf das Drei-Punkte-Menü und wählen Sie **Benutzerdefinierte Repositories** (Custom repositories).
3. Geben Sie die Repository-URL ein:
   ```text
   https://github.com/Ebenhoeh80/welock-aistudio
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

Lizenziert unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.
