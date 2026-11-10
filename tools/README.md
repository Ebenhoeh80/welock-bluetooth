# WeLock BLE & Cloud Diagnose- und Test-Werkzeugkasten

Dieses Verzeichnis enthält die konsolidierte, produktionsreife Werkzeugsammlung für die direkte Kommunikation mit **WeLock Smart Locks** (z. B. Touch41, SECBN51, PCB41) über **Bluetooth Low Energy (BLE)** und die **WeLock Cloud API**.

Alle Werkzeuge sind plattformunabhängig geschrieben und verfügen über passende Shell-Startskripte (`.sh` für Linux/macOS, `.ps1` für Windows) sowie ein interaktives Python-Hauptmenü (`welock_tools.py`), das direkt ohne Shell-Skripte gestartet werden kann.

---

## 📑 Inhaltsverzeichnis

- [Architektur & Protokoll](#architektur--protokoll)
- [Werkzeug-Übersicht](#werkzeug-übersicht)
- [Voraussetzungen & Abhängigkeiten](#voraussetzungen--abhängigkeiten)
- [Schnellstart](#schnellstart)
- [Detaillierte Werkzeug-Dokumentation](#detaillierte-werkzeug-dokumentation)
  - [1. ble_scan.py — BLE-Gerätesuche & WeLock-Erkennung](#1-ble_scanpy--ble-gerätesuche--welock-erkennung)
  - [2. ble_battery.py — Akkustand & Challenge per BLE auslesen](#2-ble_batterypy--akkustand--challenge-per-ble-auslesen)
  - [3. ble_probe.py — GATT-Dienste & Characteristics inspizieren](#3-ble_probepy--gatt-dienste--characteristics-inspizieren)
  - [4. welock_cloud_login.py — Cloud-Konto & Geräteübersicht](#4-welock_cloud_loginpy--cloud-konto--geräteübersicht)
  - [5. welock_command_probe.py — Hybrid Command-Probe (ohne Unlock)](#5-welock_command_probepy--hybrid-command-probe-ohne-unlock)
  - [6. welock_unlock.py — Autorisierter Entriegelungstest](#6-welock_unlockpy--autorisierter-entriegelungstest)
  - [7. welock_tools.py — Interaktives Hauptmenü](#7-welock_toolspy--interaktives-hauptmenü)
  - [8. dependency_check.py — System- & Abhängigkeitsprüfung](#8-dependency_checkpy--system---abhängigkeitsprüfung)
  - [9. welock_protocol.py — Protokolldefinition & Konstanten](#9-welock_protocolpy--protokolldefinition--konstanten)
- [Plattform-Startskripte (Linux / macOS / Windows)](#plattform-startskripte-linux--macos--windows)
- [Typische Arbeitsabläufe (Workflows)](#typische-arbeitsabläufe-workflows)
- [Fehlerbehebung (Troubleshooting)](#fehlerbehebung-troubleshooting)
- [Archivierung alter Skripte](#archivierung-alter-skripte)

---

## 🏗 Architektur & Protokoll

WeLock Smart Locks nutzen für die lokale Kommunikation Bluetooth Low Energy (BLE) auf Basis des **Nordic UART Service (NUS)**:

| Eigenschaft | UUID | Beschreibung |
| :--- | :--- | :--- |
| **GATT Service** | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | Nordic UART Service |
| **Write Characteristic (TX)** | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | Befehlsausgabe an das Schloss (Write without response) |
| **Notify Characteristic (RX)** | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | Rückmeldungen vom Schloss (Notifications) |

### Challenge-Response Ablauf:
1. **Batterie- & Challenge-Anfrage**:
   Das Skript sendet 15 Bytes über `WRITE_UUID`: `0x55 0x30` gefolgt von 13 Nullbytes (`0x00`).
2. **Schloss-Antwort**:
   Das Schloss antwortet über `NOTIFY_UUID` mit exakt 4 Bytes:
   - Byte 0..1: `0x55 0x30` (Header)
   - Byte 2: `random_factor` (dynamischer Challenge-Faktor, 0–255)
   - Byte 3: `battery` (Batterieladestand in Prozent, 0–100)
3. **Cloud-Command-Generierung**:
   Der `random_factor` und der `battery`-Wert werden zusammen mit der `deviceNumber` und dem `deviceName` über HTTPS an die WeLock Cloud (`https://clientapi.welock.com.cn/api/Command/UnLock`) gesendet.
   Die Cloud berechnet unter Verwendung des Kontoschlüssels einen 15-Byte alphanumerischen Befehl (`U1...`).
4. **Entriegelung (Optional)**:
   Wird der 15-Byte-Befehl per BLE an `WRITE_UUID` gesendet, kuppelt der Zylinder den Außenknauf für ca. 7 Sekunden mechanisch ein, sodass die Tür geöffnet werden kann.

---

## 🧰 Werkzeug-Übersicht

| Python-Skript | Bash-Starter (`.sh`) | PowerShell-Starter (`.ps1`) | Zweck / Funktion |
| :--- | :--- | :--- | :--- |
| `ble_scan.py` | `run_ble_scan.sh` | `run_ble_scan.ps1` | Sucht alle BLE-Geräte, hebt WeLock-Schlösser hervor, zeigt RSSI und Adressen. |
| `ble_battery.py` | `run_ble_battery.sh` | `run_ble_battery.ps1` | Fragt Batteriestand (%) und Challenge-Faktor per BLE ab. |
| `ble_probe.py` | `run_ble_probe.sh` | `run_ble_probe.ps1` | Inspiziert GATT-Services und Characteristics des Schlosses. |
| `welock_cloud_login.py` | `run_cloud_login.sh` | `run_cloud_login.ps1` | Prüft Cloud-Konto, listet Schlosscodes (`deviceNumber`) und BLE-Namen. |
| `welock_command_probe.py` | `run_command_probe.sh` | `run_command_probe.ps1` | Hybrid-Test: BLE-Challenge + Cloud-Befehl anfordern (**ohne Unlock**). |
| `welock_unlock.py` | `run_unlock.sh` | `run_unlock.ps1` | Autorisierter Entriegelungstest (**sendet echten Unlock-Befehl per BLE**). |
| `welock_tools.py` | `welock_tools.sh` | `welock_tools.ps1` | Interaktives Konsolen-Hauptmenü mit allen Funktionen. |
| `dependency_check.py` | — | — | Prüft Python-Version, Bleak-Installation und Bluetooth-Stack. |
| `welock_protocol.py` | — | — | Gemeinsames Protokollmodul (Konstanten, UUIDs, Parser). |

---

## 📦 Voraussetzungen & Abhängigkeiten

### Hardware-Voraussetzungen:
- **Bluetooth-Empfänger:** Rechner oder USB-Dongle mit **Bluetooth 4.0 Low Energy (BLE)** oder neuer.
- **Funkreichweite:** Das Schloss muss sich in direkter Nähe befinden (optimal **< 3 bis 5 Meter**). Metalltüren dämpfen das Funksignal stark.
- **⚠️ Schloss aufwecken (Wake-Up-Prozedur):**
  WeLock-Schlösser gehen zur Schonung der AAA-Batterien in einen tiefen Ruhezustand (*Deep Sleep*). **Vor jedem BLE-Scan oder Verbindungsaufruf muss das Schloss manuell aufgeweckt werden**, indem Sie die Tastatur oder den Fingerabdrucksensor kurz berühren (Beleuchtung geht an).
- **Batterieladestand:** Mindestens 3x frische AAA-Batterien mit stabiler Spannung (bei < 20% verweigert die Firmware oft Funkbefehle).

### Systemvoraussetzungen & Berechtigungen:
- **Python:** Version **3.10** oder neuer (getestet mit Python 3.10, 3.11, 3.12).
- **Betriebssysteme:**
  - **Linux:** BlueZ Bluetooth-Stack (`bluetoothd`). Prüfen Sie mit `rfkill list`, ob Bluetooth aktiv ist. Führen Sie Skripte als Benutzer in der Gruppe `bluetooth` aus.
  - **macOS:** macOS 12+ (CoreBluetooth). Dem ausführenden Terminal muss in *Systemeinstellungen ➔ Datenschutz & Sicherheit ➔ Bluetooth* Zugriff gewährt sein.
  - **Windows:** Windows 10 (Build 1809+) oder Windows 11 mit WinRT-Bluetooth-Stack und aktiver Bluetooth-Schnittstelle.

### Python-Pakete (`requirements-ble.txt`):
- **`bleak`** (`>=0.22.0,<3.0.0`): Asynchrone, plattformübergreifende Bluetooth-Low-Energy-Bibliothek.
- `welock_cloud_login.py` und `dependency_check.py` benötigen **keine** externen Pakete (reine Python-Standardbibliothek).

---

## 🚀 Schnellstart

### 1. Abhängigkeiten installieren
```bash
# In virtueller Umgebung:
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1
pip install -r tools/requirements-ble.txt
```

### 2. Interaktives Menü starten
```bash
# Linux / macOS:
./tools/welock_tools.sh

# Oder plattformunabhängig mit Python:
python3 tools/welock_tools.py

# Windows (PowerShell):
.\tools\welock_tools.ps1
```

---

## 📖 Detaillierte Werkzeug-Dokumentation

### 1. `ble_scan.py` — BLE-Gerätesuche & WeLock-Erkennung
Sucht nach allen Bluetooth-Low-Energy-Geräten in Reichweite, hebt erkannte WeLock-Zylinder hervor und sortiert nach Signalstärke (RSSI).

* **Parameter:**
  * `[positional_filter]`: Optionaler Filterbegriff (z. B. `Touch` oder `C41`).
  * `--timeout`, `-t` (float, Standard `10.0`): Suchdauer in Sekunden.
  * `--filter`, `-f` (str): Filtert nach Name oder MAC-Adresse.
  * `--welock-only`, `-w`: Zeigt ausschließlich erkannte WeLock-Geräte an.
  * `--json`: Strukturierte JSON-Ausgabe.
* **Aufrufbeispiele (Linux / macOS & Windows):**
  ```bash
  # Linux / macOS:
  ./tools/run_ble_scan.sh --welock-only
  ./tools/run_ble_scan.sh Touch -t 15.0 --json

  # Windows (PowerShell):
  .\tools\run_ble_scan.ps1 --welock-only
  .\tools\run_ble_scan.ps1 Touch -t 15.0 --json
  ```

---

### 2. `ble_battery.py` — Akkustand & Challenge per BLE auslesen
Verbindet sich direkt über Bluetooth mit dem Schloss, sendet die WeLock-Statusanfrage und liest den exakten Batteriestand in % sowie den aktuellen Challenge-Faktor aus.

* **Parameter:**
  * `<MAC-Adresse>`: BLE-MAC-Adresse des Schlosses (z. B. `AA:BB:CC:DD:EE:FF`).
  * `--address`, `-a` (str): Alternative zur Positionsangabe.
  * `--timeout`, `-t` (float, Standard `15.0`): Verbindungs-Timeout.
  * `--json`: JSON-Ausgabe (`{"address": "...", "battery": 85, "random_factor": 114}`).
* **Aufrufbeispiele:**
  ```bash
  # Linux / macOS:
  ./tools/run_ble_battery.sh "AA:BB:CC:DD:EE:FF"
  ./tools/run_ble_battery.sh -a "AA:BB:CC:DD:EE:FF" -t 20.0 --json

  # Windows (PowerShell):
  .\tools\run_ble_battery.ps1 "AA:BB:CC:DD:EE:FF"
  .\tools\run_ble_battery.ps1 -a "AA:BB:CC:DD:EE:FF" -t 20.0 --json
  ```

---

### 3. `ble_probe.py` — GATT-Dienste & Characteristics inspizieren
Prüft, ob ein Gerät den WeLock Nordic UART Service (`6e400001-...`) sowie die TX/RX-Characteristics bereitstellt, ohne Applikationsbefehle zu senden.

* **Parameter:**
  * `<MAC-Adresse>`: Adresse des Schlosses.
  * `--address`, `-a` (str): Alternative zur Positionsangabe.
  * `--connect`, `-c`: Verbindet sich und liest die GATT-Dienste aus.
  * `--timeout`, `-t` (Standard `15.0`): Timeout in Sekunden.
  * `--json`: JSON-Ausgabe mit GATT-Struktur.
* **Aufrufbeispiele:**
  ```bash
  # Linux / macOS:
  ./tools/run_ble_probe.sh --address "AA:BB:CC:DD:EE:FF" --connect
  ./tools/run_ble_probe.sh "AA:BB:CC:DD:EE:FF" -c --json

  # Windows (PowerShell):
  .\tools\run_ble_probe.ps1 --address "AA:BB:CC:DD:EE:FF" --connect
  .\tools\run_ble_probe.ps1 "AA:BB:CC:DD:EE:FF" -c --json
  ```

---

### 4. `welock_cloud_login.py` — Cloud-Konto & Geräteübersicht
Authentifiziert sich gegen die offizielle WeLock Cloud API (`clientapi.welock.com.cn`), um die registrierten Schlösser, interne Schlosscodes (`deviceNumber`) und zugehörige BLE-Namen abzufragen. Es werden keine Passwörter oder Tokens im Dateisystem gespeichert.

* **Parameter:**
  * `[account]` / `--account`, `-u`: WeLock-Konto / E-Mail-Adresse.
  * `--list-devices`, `-l`: Schlösser nach dem Login abrufen und auflisten.
  * `--yes`, `-y`: Bestätigungsmeldung automatisch akzeptieren.
  * `--json`: JSON-Ausgabe der Kontodaten und Schlossliste.
* **Aufrufbeispiele:**
  ```bash
  # Interaktiv:
  ./tools/run_cloud_login.sh

  # Mit Parametern (Linux / Windows):
  ./tools/run_cloud_login.sh -u "user@example.com" -l
  .\tools\run_cloud_login.ps1 -u "user@example.com" -l --json
  ```

---

### 5. `welock_command_probe.py` — Hybrid Command-Probe (ohne Unlock)
Führt den kompletten kryptografischen Vor-Ort-Ablauf durch:
1. Liest per BLE den frischen Challenge-Faktor aus dem Schloss.
2. Fragt mit diesem Challenge-Faktor bei der WeLock Cloud API den 15-Byte-Hex-Befehl an.
3. Validiert den empfangenen Befehl.
4. **WICHTIG:** Der Befehl wird **nicht** an das Schloss gesendet. Ideal zur risikofreien Verifikation von Kontodaten und Cloud-Kommunikation.

* **Parameter:**
  * `<MAC-Adresse>` / `--address`, `-a`: BLE-Adresse des Schlosses.
  * `--account`, `-u`: WeLock E-Mail-Adresse.
  * `--number`, `-n`: Schloss-Gerätenummer (`deviceNumber`).
  * `--name`: Cloud-BLE-Gerätename.
  * `--timeout`, `-t` (float, Standard 15.0): Timeout.
  * `--yes`, `-y`: Bestätigungen automatisch mit JA beantworten.
  * `--show-command`: 15-Byte Hex-Command im Terminal anzeigen.
  * `--json`: Strukturierte JSON-Rückgabe.
* **Aufrufbeispiele:**
  ```bash
  ./tools/run_command_probe.sh
  ./tools/run_command_probe.sh -a "AA:BB:CC:DD:EE:FF" -u "user@example.com" -n "C41..."
  .\tools\run_command_probe.ps1 -a "AA:BB:CC:DD:EE:FF" --show-command
  ```

---

### 6. `welock_unlock.py` — Autorisierter Entriegelungstest
Führt den vollständigen Entriegelungsvorgang vor Ort durch: Holt die BLE-Challenge, generiert den Cloud-Befehl und schreibt den 15-Byte-Befehl per BLE an das Schloss.

* **Sicherheit:** Erfordert ausdrückliche Bestätigung mit `JA` und `ENTRIEGELN` (sofern nicht `--yes` übergeben wurde).
* **Parameter:** Unterstützt die gleichen Parameter wie `welock_command_probe.py`.
* **Aufrufbeispiele:**
  ```bash
  ./tools/run_unlock.sh
  .\tools\run_unlock.ps1 -a "AA:BB:CC:DD:EE:FF" -t 20.0
  ```

---

### 7. `dependency_check.py` — Systemprüfung
Prüft, ob Python >= 3.10 installiert ist, ob das Modul `bleak` importiert werden kann und welche Betriebssystem-Voraussetzungen gelten.

* **Aufruf:**
  ```bash
  python3 tools/dependency_check.py
  # Mit automatischer Installation von bleak:
  python3 tools/dependency_check.py --install
  ```

---

## 🔄 Typische Arbeitsabläufe (Workflows)

```
┌────────────────────────────────────────────────────────┐
│ 1. Schloss aufwecken & BLE-Scan                        │
│    ./run_ble_scan.sh --welock-only                     │
│    -> Liefert: BLE-MAC-Adresse & Signalstärke          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Batteriestatus & Funkverbindung prüfen              │
│    ./run_ble_battery.sh <MAC-Adresse>                  │
│    -> Liefert: Akkustand in % & Challenge-Faktor       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Cloud-Konto prüfen & Gerätenummer abrufen           │
│    ./run_cloud_login.sh                                │
│    -> Liefert: deviceNumber, deviceName, ble.deviceName│
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Hybrid-Probe durchführen (Ohne Entriegeln)          │
│    ./run_command_probe.sh                              │
│    -> Prüft das Zusammenspiel aus BLE + Cloud API      │
└────────────────────────────────────────────────────────┘
```

---

## 🗄 Archivierung alter Skripte

Frühere Entwicklungsstände aus `/toolsdev` sowie Vorversionen einzelner Skripte wurden revisionssicher in das Verzeichnis [`/archiv`](../archiv/README.md) überführt.
