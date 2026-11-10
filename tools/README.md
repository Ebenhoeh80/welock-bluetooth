# WeLock BLE & Cloud Diagnose- und Experimentier-Werkzeuge

Dieses Verzeichnis enthält spezialisierte Python-Skripte und betriebssystemspezifische Startskripte (`.sh` für Linux/macOS, `.ps1` für Windows) für die direkte Kommunikation mit **WeLock Smart Locks** (z. B. Touch41, SECBN51, PCB41) über **Bluetooth Low Energy (BLE)** und die **WeLock Cloud API**.

Sie dienen insbesondere dazu:
1. Das Schloss über BLE zu suchen, die **BLE-MAC-Adresse** sowie den **BLE-Gerätenamen** (`SECBN...`, `Touch...`, `PCB...`) zu ermitteln.
2. Die GATT-Dienste (Nordic UART Service) und Eigenschaften zu inspizieren.
3. Den Batteriestand sowie den dynamischen Challenge-Faktor (`random_factor`) per BLE auszulesen.
4. Ein WeLock-Benutzerkonto zu testen und registrierte Schlosscodes (`deviceNumber`), Anzeigenamen und zugeordnete BLE-Namen abzufragen.
5. Das Zusammenspiel aus BLE-Challenge und Cloud-Entriegelungsbefehl (`15-Byte-Command`) kontrolliert zu analysieren und vor Ort ohne WiFiBox-Gateway zu testen.

---

## 📑 Inhaltsverzeichnis

- [Architektur & Protokoll](#architektur--protokoll)
- [Werkzeugkette & Workflow](#werkzeugkette--workflow)
- [Voraussetzungen & Python-Abhängigkeiten](#voraussetzungen--python-abhängigkeiten)
- [Schnellstart & Installation](#schnellstart--installation)
- [Übersicht aller Skripte](#übersicht-aller-skripte)
  - [1. ble_probe.py (GATT-Inspektion)](#1-ble_probepy-gatt-inspektion)
  - [2. welock_cloud_login.py (Cloud-Konto & Geräte)](#2-welock_cloud_loginpy-cloud-konto--geräte)
  - [3. welock_command_probe.py (Hybrid-Probe ohne Unlock)](#3-welock_command_probepy-hybrid-probe-ohne-unlock)
  - [4. welock_unlock_experiment.py (Autorisierter Unlock-Test)](#4-welock_unlock_experimentpy-autorisierter-unlock-test)
  - [5. welock_protocol.py (Protokollmodul)](#5-welock_protocolpy-protokollmodul)
  - [6. welock_tools.sh / welock_tools.ps1 (Interaktives Menü)](#6-welock_toolssh--welock_toolsps1-interaktives-menü)
- [Startskripte & Plattformnutzung](#startskripte--plattformnutzung)
  - [Linux / macOS (.sh)](#linux--macos-sh)
  - [Windows PowerShell (.ps1)](#windows-powershell-ps1)
- [Typische Anwendungsbeispiele](#typische-anwendungsbeispiele)
- [Troubleshooting & Fehlerbehebung](#troubleshooting--fehlerbehebung)
- [Sicherheits- & Entwicklerhinweise](#sicherheits--entwicklerhinweise)

---

## 🏗 Architektur & Protokoll

WeLock Smart Locks nutzen für die lokale Kommunikation Bluetooth Low Energy auf Basis des **Nordic UART Service (NUS)**:

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

## 🔄 Werkzeugkette & Workflow

Der empfohlene Ablauf zur Erforschung und Inbetriebnahme Ihres Schlosses gliedert sich in folgende Schritte:

```
┌────────────────────────────────────────────────────────┐
│ 1. BLE-Scan & Adresse ermitteln                        │
│    ./run_ble_probe.sh --address <MAC> [--connect]      │
│    (Findet MAC-Adresse, RSSI & prüft BLE-GATT Service) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Cloud-Konto prüfen & Gerätenummer abrufen           │
│    ./run_cloud_login.sh                                │
│    (Liefert: deviceNumber, deviceName, ble.deviceName) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Challenge-Response testen (Ohne Entriegeln)         │
│    ./run_command_probe.sh                              │
│    (Liest BLE-Challenge, holt 15-Byte Cloud-Command,   │
│     sendet ihn aber NICHT an das Schloss)              │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Vor-Ort Entriegelungstest (Optional / Autorisert)   │
│    ./run_unlock_experiment.sh                          │
│    (Sendet den 15-Byte Command per BLE -> Entriegelt)  │
└────────────────────────────────────────────────────────┘
```

---

## 📦 Voraussetzungen & Python-Abhängigkeiten

### Hardware-Voraussetzungen:
- **Bluetooth-Empfänger**: Rechner oder USB-Dongle mit **Bluetooth 4.0 Low Energy (BLE)** oder neuer.
- **Funkreichweite**: Das WeLock-Schloss muss sich in direkter Nähe befinden (optimal **< 3 bis 5 Meter**). Metalltüren oder dicke Wände reduzieren die Reichweite erheblich.
- **⚠️ Schloss aufwecken (Wake-Up-Prozedur)**:
  WeLock-Schlösser gehen zur Schonung der AAA-Batterien in einen tiefen Ruhezustand (*Deep Sleep*). **Vor jedem BLE-Scan oder Verbindungsaufruf muss das Schloss manuell aufgeweckt werden**, indem Sie die Tastatur oder den Fingerabdrucksensor kurz berühren.
- **Batterieladestand**: Mindestens 3x frische AAA-Batterien mit stabiler Spannung (bei < 20% verweigert die Firmware oft Funkbefehle).

### Systemvoraussetzungen & Berechtigungen:
- **Python**: Version **3.10** oder neuer (getestet mit 3.10, 3.11, 3.12).
- **Betriebssysteme**:
  - **Linux**: BlueZ Bluetooth-Stack (`bluetoothd`). Prüfen Sie mit `rfkill list`, ob Bluetooth aktiv ist. Führen Sie Skripte als Benutzer in der Gruppe `bluetooth` oder mit passenden Berechtigungen aus.
  - **macOS**: macOS 12+ (CoreBluetooth). Dem ausführenden Terminal muss in *Systemeinstellungen ➔ Datenschutz & Sicherheit ➔ Bluetooth* Zugriff gewährt sein.
  - **Windows**: Windows 10 (Build 1809+) oder Windows 11 mit WinRT-Bluetooth-Stack und aktiver Bluetooth-Schnittstelle.

### Python-Pakete (`requirements-ble.txt`):
- **`bleak`** (`>=0.22.0,<3.0.0`): Asynchrone, plattformübergreifende Bluetooth-Low-Energy-Bibliothek.
- `welock_cloud_login.py` benötigt **keine** externen Pakete (reine Standardbibliothek).
- `ble_probe.py`, `welock_command_probe.py` und `welock_unlock_experiment.py` benötigen zwingend **`bleak`**.

---

## 🚀 Schnellstart & Installation

### Linux / macOS:
```bash
# 1. In das Projektverzeichnis wechseln
cd welock

# 2. Virtuelle Python-Umgebung anlegen
python3 -m venv .venv

# 3. Virtuelle Umgebung aktivieren
source .venv/bin/activate

# 4. Bleak installieren
pip install -r tools/requirements-ble.txt

# 5. Startskripte ausführbar machen (falls noch nicht geschehen)
chmod +x tools/*.sh

# 6. Interaktives Menü starten
./tools/welock_tools.sh
```

### Windows (PowerShell):
```powershell
# 1. In das Projektverzeichnis wechseln
cd welock

# 2. Virtuelle Umgebung anlegen & aktivieren
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Bleak installieren
pip install -r tools\requirements-ble.txt

# 4. Interaktives Menü starten
.\tools\welock_tools.ps1
```

---

## 🛠 Übersicht aller Skripte

### 1. `ble_probe.py` (GATT-Inspektion)
Untersucht ein bekanntes BLE-Gerät anhand seiner Adresse ohne das Senden von Anwendungsbefehlen.

- **Aufrufparameter**:
  - `--address` *(Pflicht)*: BLE-Adresse (MAC-Adresse `AA:BB:CC:DD:EE:FF` oder macOS UUID).
  - `--timeout` *(Optional, Standard: 15)*: Timeout in Sekunden für Scan und Verbindung.
  - `--connect` *(Optional)*: Stellt Verbindung her und prüft Service- und Characteristic-UUIDs.
- **Startskripte**:
  - Linux/macOS: `./tools/run_ble_probe.sh --address "AA:BB:CC:DD:EE:FF" --connect`
  - Windows: `.\tools\run_ble_probe.ps1 --address "AA:BB:CC:DD:EE:FF" --connect`

### 2. `welock_cloud_login.py` (Cloud-Konto & Geräte)
Verbindet sich mit der offiziellen mobilen WeLock-API (`https://clientapi.welock.com.cn/api`), authentifiziert das Konto und listet alle registrierten Schlösser auf.

- **Besonderheiten**:
  - Reine Python-Standardbibliothek (kein `pip` erforderlich).
  - Fragt E-Mail und Passwort interaktiv ab (verdeckte Eingabe).
  - Speichert **keine** Zugangsdaten oder Tokens auf der Festplatte.
  - Zeigt Schlosscodes (`deviceNumber`), Anzeigenamen und zugehörige BLE-Namen (`ble[].deviceName`).
- **Startskripte**:
  - Linux/macOS: `./tools/run_cloud_login.sh`
  - Windows: `.\tools\run_cloud_login.ps1`

### 3. `welock_command_probe.py` (Hybrid-Probe ohne Unlock)
Führt die vollständige Challenge-Response-Kette durch, sendet jedoch **keinen** Entriegelungsbefehl an das Schloss.

- **Ablauf**:
  1. BLE-Gerät scannen (automatisch oder per Adresse).
  2. Akkustand und Challenge-Faktor (`random_factor`) per BLE abrufen.
  3. Cloud-Login durchführen.
  4. Dynamischen 15-Byte-Unlock-Befehl von der Cloud anfordern.
  5. Befehl analysieren (Länge/Hex) und verwerfen, ohne das Schloss zu öffnen.
- **Startskripte**:
  - Linux/macOS: `./tools/run_command_probe.sh`
  - Windows: `.\tools\run_command_probe.ps1`

### 4. `welock_unlock_experiment.py` (Autorisierter Unlock-Test)
Führt ein echtes, autorisiertes Vor-Ort-Entriegelungsexperiment über BLE durch.

- **Sicherheitsvorkehrungen**:
  - Verlangt zweifache Bestätigung (`JA` gefolgt von `ENTRIEGELN`).
  - Sendet den frischen 15-Byte-Befehl einmalig per BLE an das Schloss.
  - Warnhinweis: Mindestens 30 Sekunden Abstand zwischen Entriegelungsversuchen einhalten.
- **Startskripte**:
  - Linux/macOS: `./tools/run_unlock_experiment.sh`
  - Windows: `.\tools\run_unlock_experiment.ps1`

### 5. `welock_protocol.py` (Protokollmodul)
Reines Bibliotheksmodul ohne CLI-Einstiegspunkt. Definiert die Konstanten `BATTERY_REQUEST`, `BATTERY_RESPONSE_HEADER` und die Datenklasse `BatteryResponse` samt Parserfunktion `parse_battery_response`.

### 6. `welock_tools.sh` / `welock_tools.ps1` (Interaktives Menü)
Komfortables Auswahlmenü, das alle Einzelwerkzeuge auf Knopfdruck bereitstellt und optional direkt die virtuelle Umgebung einrichtet.

---

## 💻 Startskripte & Plattformnutzung

Die Startskripte wurden speziell so entwickelt, dass sie:
1. **Das Projektverzeichnis automatisch erkennen**, unabhängig davon, aus welchem Arbeitsverzeichnis heraus sie aufgerufen werden.
2. Den `PYTHONPATH` zwingend auf das Repository-Root setzen, damit modulübergreifende Importe (`from tools.ble_probe import ...`) fehlerfrei funktionieren.
3. Existierende virtuelle Umgebungen (`.venv` im Root oder im `tools/`-Ordner) automatisch priorisieren.
4. Bei fehlendem `bleak` sofort eine verständliche Anleitung zur Installation anzeigen.
5. Alle übergebenen Parameter (`"$@"` bzw. `$args`) transparent an das jeweilige Python-Skript durchreichen.

---

## 💡 Typische Anwendungsbeispiele

### Beispiel 1: Alle WeLock-Schlösser in der Nähe suchen
```bash
./tools/run_command_probe.sh
```
*Geben Sie bei der Adressabfrage einfach die Eingabetaste (Enter) ein. Das Skript startet einen 15-sekündigen BLE-Scan und listet alle gefundenen Geräte auf.*

### Beispiel 2: Bekanntes Schloss auf Erreichbarkeit prüfen
```bash
./tools/run_ble_probe.sh --address "DF:32:88:1A:BC:90" --connect --timeout 10
```

### Beispiel 3: Eigene Schlossnummer und Cloud-BLE-Name herausfinden
```bash
./tools/run_cloud_login.sh
```
*Geben Sie Ihre WeLock-E-Mail und Ihr Passwort ein. Das Skript listet alle in der App registrierten Schlösser mit Nummer und BLE-Namen auf.*

---

## ❓ Troubleshooting & Fehlerbehebung

### 1. `FEHLER: Das erforderliche Python-Paket 'bleak' ist nicht installiert!`
- **Ursache**: Das Python-Modul `bleak` fehlt im aktuellen Interpreter.
- **Lösung**:
  ```bash
  pip install -r tools/requirements-ble.txt
  ```

### 2. `ModuleNotFoundError: No module named 'tools'`
- **Ursache**: Das Python-Skript wurde direkt mit `python tools/welock_command_probe.py` ohne gesetzten `PYTHONPATH` aufgerufen.
- **Lösung**: Nutzen Sie stets die beigelegten Startskripte (`./tools/run_command_probe.sh` bzw. `.\tools\run_command_probe.ps1`), welche `PYTHONPATH` automatisch konfigurieren.

### 3. `BleakError: No Bluetooth adapter found` oder Berechtigungsfehler unter Linux
- **Ursache**: Der Bluetooth-Dienst (BlueZ) läuft nicht oder der Benutzer hat keine Zugriffsrechte auf `/dev/rfkill` bzw. `hci0`.
- **Lösung**:
  ```bash
  # Bluetooth-Status prüfen:
  sudo systemctl status bluetooth
  sudo systemctl start bluetooth

  # Benutzer zur Bluetooth-Gruppe hinzufügen:
  sudo usermod -aG bluetooth $USER
  ```

### 4. `Device not found during scan`
- **Ursache**: Das Schloss ist außer Reichweite (> 5–10 Meter), befindet sich im Energiesparmodus oder die Bluetooth-Schnittstelle ist blockiert.
- **Lösung**: Knauf am Schloss berühren/aufwecken, näher herantreten und Timeout auf `--timeout 25` erhöhen.

### 5. `Cloud-Login meldet die Smartphone-App ab`
- **Ursache**: WeLock erlaubt serverseitig in der Regel nur eine aktive Benutzersitzung pro Konto.
- **Hinweis**: Bei einer neuen Anmeldung über das Skript kann die mobile App abgemeldet werden. Nach Abschluss der Tests einfach in der App erneut einloggen.

### 6. Mindestabstand zwischen Entriegelungen (30 Sekunden)
- **Wichtig**: WeLock-Zylinder besitzen einen mechanischen und serverseitigen Schutz. Warten Sie nach jedem Entriegelungsvorgang mindestens 30 Sekunden, bevor Sie einen neuen Befehl anfordern.

---

## 🔒 Sicherheits- & Entwicklerhinweise

- **Keine Passwörter im Chat / Terminal**: Teilen Sie keine Passwörter, Client-Secrets, Tokens oder MAC-Adressen in öffentlichen Repositories oder Foren.
- **Keine Cloud-Token-Speicherung**: Die Skripte unter `/tools` speichern aus Sicherheitsgründen bewusst keine Anmeldetokens auf der Festplatte.
- **Home Assistant HACS Integration**: Wenn Sie die dauerhafte Steuerung über Home Assistant einrichten möchten, nutzen Sie die vollständige HACS-Integration unter [`custom_components/welock`](../custom_components/welock) in Verbindung mit einem WeLock WiFiBox Gateway. Weitere Details finden Sie in der [Haupt-Dokumentation](../README.md).
