# WeLock Smart Lock — Home Assistant HACS Integration & BLE Diagnose-Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/version-v2.0.0-blue.svg?style=for-the-badge)](https://github.com/Ebenhoeh80/welock-aistudio/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-sprachen--languages)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

Suite für **WeLock Smart Door Locks** (z. B. Touch41, SECBN51, PCB41, SECBREBL01):

1. 🏠 **Home Assistant HACS Integration** (`custom_components/welock`): Entriegeln per Bluetooth über den Home-Assistant-Bluetooth-Stack (lokaler Adapter oder ESPHome-Bluetooth-Proxy). Die WeLock-Cloud liefert dabei nur den einmaligen Entriegelungsbefehl. Mit geführter Einrichtung, Bluetooth-Discovery, Akku-, Signal- und Erreichbarkeitssensoren.
2. 🔬 **BLE & Cloud Diagnose-Tools** ([`tools/`](tools/README.md)): Python-Werkzeuge für BLE-Suche, Akkustand/Challenge, GATT-Inspektion, Cloud-Login und Entriegelungstests.

> ⚠️ **Version 2.0.0 ist ein Breaking Change.** Einträge aus 1.x müssen gelöscht und neu angelegt werden. Siehe [Upgrade von 1.x](#-upgrade-von-1x).

---

## 📑 Inhalt

- [So funktioniert es](#-so-funktioniert-es)
- [Voraussetzungen](#-voraussetzungen)
- [Installation](#-installation)
- [Einrichtung in Home Assistant](#-einrichtung-in-home-assistant)
- [Entitäten](#-entitäten)
- [Optionen](#-optionen)
- [Betrieb & Verhalten](#-betrieb--verhalten)
- [Fehlerbehebung](#-fehlerbehebung)
- [Upgrade von 1.x](#-upgrade-von-1x)
- [Datenschutz & Sicherheit](#-datenschutz--sicherheit)
- [Diagnose-Tools](#-diagnose-tools-tools)
- [Entwicklung & Tests](#-entwicklung--tests)
- [Lovelace- & Automations-Beispiele](#-lovelace---automations-beispiele)
- [Repository-Architektur](#-repository-architektur)

---

## 🔐 So funktioniert es

WeLock-Zylinder werden lokal per **Bluetooth Low Energy** (Nordic UART Service) geschaltet. Den Entriegelungsbefehl berechnet die **WeLock-Cloud** für eine frische Challenge des Schlosses:

```text
Home Assistant                          Schloss (BLE)              WeLock-Cloud
     │  1. Statusanfrage 55 30 00…  ───────▶│                            │
     │◀─────── 55 30 <random> <akku>  ──────│                            │
     │  2. Login + /Command/UnLock (deviceNumber, deviceName, random, akku) ─▶│
     │◀──────────────────────────── 15-Byte-Befehl "U1…" ──────────────────────│
     │  3. Befehl schreiben  ───────────────▶│  Knauf kuppelt ~7 s ein   │
```

* Die Cloud wird **nur** bei Einrichtung, erneuter Anmeldung und beim Entriegeln kontaktiert. Es gibt **kein Cloud-Polling**.
* Erreichbarkeit und Signalstärke kommen aus dem Home-Assistant-Bluetooth-Stack, der Akkustand direkt vom Schloss.
* Jeder Befehl gilt nur für eine Challenge. Ein abgefangener Befehl lässt sich nicht wiederverwenden.

---

## 📋 Voraussetzungen

### Für die Home-Assistant-Integration
* **Home Assistant 2024.11.0** oder neuer, mit **HACS** oder Dateizugriff auf `/config/custom_components/`.
* **Bluetooth in Reichweite der Tür:** ein Bluetooth-Adapter am HA-Host oder ein **ESPHome-Bluetooth-Proxy** mit aktiven Verbindungen (`bluetooth_proxy: active: true`). Die Integration braucht eine *verbindungsfähige* Strecke zum Schloss, passives Mithören reicht nicht.
* **WeLock-Konto:** E-Mail und Passwort der WeLock-App (iOS/Android). Eine separate Client-ID oder eine WiFiBox wird **nicht** benötigt.
* Das Schloss muss in der WeLock-App eingerichtet sein. Die Integration liest Schlossnummer (`deviceNumber`) und BLE-Modul (`ble[].deviceName`, `ble[].deviceMac`) aus dem Konto.

### Für die Diagnose-Tools
* Python **3.10+**, Bluetooth-4.0-LE-Adapter, Python-Paket `bleak` (`pip install -r tools/requirements-ble.txt`).
* Betriebssystem-Berechtigungen: Linux mit BlueZ (`rfkill list`, Gruppe `bluetooth`), macOS 12+ mit Bluetooth-Freigabe für das Terminal, Windows 10 (1809+) oder 11 mit aktivem Bluetooth.

### Funk & Hardware
* Optimal sind **unter 3–5 m** zwischen Schloss und Adapter/Proxy. Metalltüren, Beschläge und dicke Wände dämpfen 2,4 GHz stark.
* Das Schloss akzeptiert **nur eine BLE-Verbindung gleichzeitig**. Ist die WeLock-App im Vordergrund verbunden, lehnt es weitere Verbindungen ab.
* Bei schwachen Batterien (< 20 %) verweigert die Firmware oft Funkbefehle. Verwende frische AAA-Batterien.

---

## 📦 Installation

### Über HACS (empfohlen)
1. **HACS** öffnen → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**.
2. URL `https://github.com/Ebenhoeh80/welock-aistudio` eingeben, Kategorie **Integration**, **Hinzufügen**.
3. **WeLock Smart Lock** suchen → **Herunterladen** → Home Assistant **neu starten**.

### Manuell
1. Neuestes [Release](https://github.com/Ebenhoeh80/welock-aistudio/releases) herunterladen.
2. Ordner `custom_components/welock` nach `/config/custom_components/welock/` kopieren.
3. Home Assistant neu starten.

---

## 🚀 Einrichtung in Home Assistant

Die Einrichtung folgt dem WeLock-Workflow und **prüft jeden Schritt, bevor es weitergeht**. Ein Eintrag entspricht einem BLE-Modul eines Schlosses. Für mehrere Schlösser legst du mehrere Einträge an.

| Schritt | Was passiert | Bedingung zum Weitergehen |
| :--- | :--- | :--- |
| **0. Start** | HA erkennt `WeLock*`-Module per Bluetooth und zeigt sie unter *Entdeckt* an. Alternativ: **Einstellungen → Geräte & Dienste → Integration hinzufügen → WeLock Smart Lock**. | – |
| **1. Cloud-Anmeldung** | E-Mail und Passwort der WeLock-App. ⚠️ Die Anmeldung **beendet andere Sitzungen** des Kontos, z. B. die App. Die App sollte dabei nicht benutzt werden. | Login erfolgreich, Konto enthält mindestens ein Schloss mit BLE-Modul. Bei Discovery: Das gefundene Modul gehört zum Konto. |
| **2. Schloss auswählen** | Liste aus der Cloud: BLE-Name, MAC-Adresse, Schlossnummer, Akkustand laut Cloud und ob HA das Modul **gerade in Reichweite** hat. Ein Modul in Reichweite ist vorausgewählt. | Modul ist noch nicht eingerichtet. |
| **3. Bluetooth-Prüfung** | HA verbindet sich mit dem Schloss und fragt Akkustand und Challenge ab (`55 30`). **Es wird nicht entriegelt.** | Ein Adapter oder Proxy erreicht das Schloss **und** das Schloss antwortet. Sonst erscheint ein Fehler und du kannst es erneut versuchen. |

Nach Schritt 3 legt HA das Gerät mit allen Entitäten an.

**Erneute Anmeldung:** Lehnt die Cloud später das Passwort ab (z. B. nach einer Passwortänderung), startet HA automatisch die erneute Anmeldung. Dort gibst du nur das Passwort ein. HA prüft dabei, ob das Schloss noch zum Konto gehört.

---

## 🧩 Entitäten

| Entität | Typ | Beschreibung |
| :--- | :--- | :--- |
| `lock.<name>` | Lock | Entriegeln per BLE + Cloud-Befehl. Der Zustand ist *angenommen* (siehe unten). Nicht verfügbar, wenn kein Adapter/Proxy das Schloss erreicht. |
| `sensor.<name>_batterie` | Sensor (Diagnose) | Akkustand in %, direkt vom Schloss gelesen. |
| `sensor.<name>_signalstarke` | Sensor (Diagnose, standardmäßig deaktiviert) | RSSI der letzten Bluetooth-Advertisements in dBm. |
| `binary_sensor.<name>_bluetooth_erreichbar` | Binärsensor (Diagnose) | An, solange ein verbindungsfähiger Adapter oder Proxy das Schloss sieht. |
| `sensor.<name>_gelernte_offline_befehle` | Sensor (Diagnose, standardmäßig deaktiviert) | Anzahl der lokal gelernten Entriegelungsbefehle (von 256) samt Abdeckung. Siehe [Lokaler Offline-Unlock](#-lokaler-offline-unlock-experimentell). |
| `sensor.<name>_letzter_zugriff` | Sensor (Diagnose, standardmäßig deaktiviert) | Letzter Eintrag des Zutrittsprotokolls (wer, wann, wie). Wird nur durch den Dienst `welock.fetch_access_log` gefüllt. |

Die genauen Entity-IDs hängen vom BLE-Namen und von der HA-Sprache ab.

---

## ⚙️ Optionen

**Einstellungen → Geräte & Dienste → WeLock → Konfigurieren**

| Option | Standard | Bereich | Bedeutung |
| :--- | :---: | :---: | :--- |
| Als entriegelt anzeigen für | 7 s | 3–60 s | So lange zeigt das Lock nach dem Entriegeln „entriegelt“. Danach wieder „verriegelt“. |
| Akkustand per Bluetooth lesen alle | 24 h | 0–168 h | Regelmäßige BLE-Statusabfrage. `0` = nur beim Entriegeln (schont die Schlossbatterie). |
| Bluetooth-Erreichbarkeit prüfen alle | 60 s | 10–600 s | Wie oft Erreichbarkeit und RSSI aus dem HA-Bluetooth-Cache aktualisiert werden. Erzeugt **keinen** Funkverkehr. |
| Lokalen Befehls-Cache aufbauen und nutzen | aus | an/aus | **Experimentell.** Entriegelt bei bekanntem Challenge-Wert lokal ohne Cloud. Siehe unten. |

---

## 🔓 Lokaler Offline-Unlock (experimentell)

Der Cloud-Entriegelungsbefehl hängt **allein vom `randomFactor`-Byte** der
BLE-Challenge ab (nicht von Akkustand oder BLE-Schlüssel). Es gibt daher höchstens
**256 verschiedene Befehle** pro Schloss. Die Integration **lernt** jeden von der
Cloud gelieferten Befehl und speichert ihn pro Konfigurationseintrag.

* Die Tabelle füllt sich **im normalen Betrieb von selbst** – auch wenn die Option
  aus ist (die Cloud wird dann weiter genutzt, aber jeder Befehl mitgelernt). Der
  Sensor *Gelernte Offline-Befehle* zeigt den Fortschritt (x/256).
* Mit aktivierter Option wird ein **bekannter** Challenge-Wert **lokal ohne
  Cloud-Login** beantwortet – schneller und ohne Abmeldung der WeLock-App.
* Ein gespeicherter Befehl ist **byte-identisch** zu dem, den die Cloud liefern
  würde (kein selbst erzeugter Payload), und wird vor jeder Nutzung erneut geprüft.

> ⚠️ **Noch nicht am Schloss mechanisch verifiziert.** Deshalb ist die Option
> standardmäßig **aus** und die Cloud bleibt der Standardpfad. Schalte sie erst
> ein, wenn du einen lokal erzeugten Befehl vor Ort erfolgreich getestet hast.

> 📚 **Wie das herausgefunden wurde:** Die vollständige Reverse-Engineering-
> Methodik (BLE-Protokoll, Cloud-API, differenzielle Analyse, Rechtsgrundlage
> § 69e UrhG) ist unter [`docs/`](docs/README.md) dokumentiert.

## 📜 Zutrittsprotokoll (Dienst)

Der Dienst **`welock.fetch_access_log`** holt das Zutrittsprotokoll (wer, wann,
mit welcher Methode) aus der Cloud und schreibt es in den Sensor *Letzter
Zugriff* (Attribute inkl. der letzten Einträge).

> ⚠️ Jeder Abruf **meldet andere Sitzungen des Kontos ab** (z. B. die WeLock-App),
> da ein Cloud-Login nötig ist. Deshalb wird **nur auf Abruf** geladen, nicht
> automatisch. Die Telefonnummer aus dem Rohdatensatz wird bewusst **nicht**
> übernommen.

---

## 🔄 Betrieb & Verhalten

* **Entriegeln über die Cloud meldet die WeLock-App ab.** Für den Befehl ist dann ein frischer Cloud-Login nötig – eine Eigenschaft der WeLock-Cloud. Bei einem Treffer im [lokalen Befehls-Cache](#-lokaler-offline-unlock-experimentell) entfällt der Cloud-Login (und damit die Abmeldung).
* **Mindestens 30 s zwischen zwei Entriegelungen.** Ein früherer Versuch wird mit einer Meldung abgelehnt.
* **Angenommener Zustand:** Das Schloss meldet seinen Zustand nicht. Der Zylinder kuppelt den Außenknauf ca. 7 s ein und verriegelt danach mechanisch von selbst. „Verriegeln“ in HA setzt nur die Anzeige zurück.
* **Ohne Bluetooth-Reichweite** ist das Lock *nicht verfügbar*. Die Cloud allein kann nicht entriegeln.
* Alle BLE-Zugriffe auf ein Schloss laufen nacheinander, damit Akkuabfrage und Entriegeln nicht kollidieren.

---

## 🩺 Fehlerbehebung

| Meldung / Symptom | Ursache & Lösung |
| :--- | :--- |
| *E-Mail-Adresse oder Passwort ist falsch* | Zugangsdaten der WeLock-App prüfen. Mit den [Tools](#-diagnose-tools-tools) gegenprüfen: `tools/run_cloud_login.*`. |
| *In diesem Konto wurde kein Schloss mit Bluetooth-Modul gefunden* | Das Schloss ist in der App nicht oder ohne BLE-Modul eingerichtet. |
| *Das gefundene Schloss gehört nicht zu diesem WeLock-Konto* | Die Discovery hat ein fremdes oder anders zugeordnetes Modul gefunden. Mit dem richtigen Konto anmelden oder die Einrichtung manuell starten. |
| *Kein Bluetooth-Adapter oder -Proxy erreicht das Schloss* | Proxy näher an die Tür stellen, beim ESPHome-Proxy `active: true` setzen, App schließen (nur eine BLE-Verbindung gleichzeitig). |
| *Das Schloss hat nicht auf die Statusabfrage geantwortet* | Schloss wecken (Knauf berühren), Batterien prüfen, erneut versuchen. |
| Lock dauerhaft *nicht verfügbar* | Binärsensor „Bluetooth erreichbar“ prüfen. HA sieht das Schloss nicht, Ursachen wie oben. |
| *Bitte … s warten* | Die 30-Sekunden-Sperre zwischen zwei Entriegelungen ist noch aktiv. |
| Einrichtung meldet *Migrationsfehler* | Eintrag aus 1.x, siehe [Upgrade von 1.x](#-upgrade-von-1x). |

**Debug-Logs** (`configuration.yaml`):
```yaml
logger:
  logs:
    custom_components.welock: debug
```
Die **Diagnosedaten** (Gerät → Diagnose herunterladen) enthalten weder Konto noch Passwort.

---

## ⬆️ Upgrade von 1.x

Version 2.0.0 ersetzt das alte Modell (Cloud-Polling, WiFiBox) durch den BLE-Workflow. Bestehende Einträge haben keine Schlossauswahl und lassen sich nicht automatisch migrieren.

1. Integration per HACS auf 2.0.0 aktualisieren und HA neu starten.
2. Den alten WeLock-Eintrag unter **Geräte & Dienste** **löschen**. Er zeigt einen Migrationsfehler.
3. Integration neu hinzufügen und die [Einrichtung](#-einrichtung-in-home-assistant) durchlaufen.
4. Automationen und Dashboards auf die neuen Entity-IDs anpassen. Entfallen sind der WiFiBox-Gateway-Sensor und „Letzte Entriegelungsmethode“.

---

## 🛡 Datenschutz & Sicherheit

* E-Mail und Passwort liegen ausschließlich im Config-Entry von Home Assistant. Der Cloud-Token wird nur im Speicher gehalten und nach jeder Anfrage verworfen.
* Logs und Fehlermeldungen enthalten weder Passwort noch Token. Die Diagnosedaten schwärzen Konto und Passwort.
* Die Cloud-Kommunikation läuft ausschließlich per HTTPS zu `clientapi.welock.com.cn`, ohne Redirects.
* Sicherheitslücken bitte vertraulich melden, siehe [SECURITY.md](SECURITY.md).

---

## 🛠 Diagnose-Tools (`tools/`)

Für Analyse und Fehlersuche außerhalb von Home Assistant:

```bash
pip install -r tools/requirements-ble.txt

./tools/welock_tools.sh                    # Interaktives Menü (Windows: .\tools\welock_tools.ps1)
./tools/run_ble_scan.sh                    # BLE-Geräte & Schlösser suchen
./tools/run_ble_battery.sh "AA:BB:CC:..."  # Akkustand & Challenge abfragen
./tools/run_ble_probe.sh --address "AA:BB:..." --connect
./tools/run_cloud_login.sh                 # Cloud-Konto & Geräte prüfen
./tools/run_command_probe.sh               # Challenge + Cloud-Befehl, ohne Entriegeln
./tools/run_unlock.sh                      # Autorisierter Entriegelungstest
```

Zu jedem `.sh` gibt es ein gleichnamiges `.ps1` für Windows. Alle Parameter, Protokolldetails und Workflows stehen in der [**tools/README.md**](tools/README.md).

---

## 🧪 Entwicklung & Tests

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install pytest aiohttp ruff black
pytest                       # Unit-Tests; Live-Test wird übersprungen
ruff check custom_components/ tools/ tests/
black --check custom_components/ tools/ tests/
```

### Optionaler Live-Smoke-Test gegen die echte Cloud
`tests/test_live_smoke.py` (Marker `live`) prüft **nur lesend** Cloud-Login und Schlossliste, optional zusätzlich den HA-Bluetooth-Cache. Unlock- und BLE-Schreibpfade sind im Test aktiv gesperrt. Er läuft **nie in CI** und nur mit ausdrücklichem Opt-in:

```powershell
# Variablen nur in der aktuellen Shell setzen – keine .env-Datei anlegen!
$env:WELOCK_LIVE_TEST = "1"
$env:WELOCK_USER      = "<konto>"
$env:WELOCK_PASSWORD  = Read-Host -MaskAsPlainText "WELOCK-Passwort"
# optional: $env:WELOCK_LOCK_ID, $env:WELOCK_HA_BT_CACHE = "<config>\.storage\bluetooth.remote_scanners"
pytest -m live -s
Remove-Item Env:WELOCK_PASSWORD
```

⚠️ Der Login beendet die Sitzung der WeLock-App. Die App sollte dabei nicht benutzt werden. Die Ausgabe enthält weder Passwort noch Token.

Weitere Hinweise stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 💡 Lovelace- & Automations-Beispiele

### Kachel-Karte
```yaml
type: tile
entity: lock.welock_haustur
name: Haustür
features:
  - type: lock-commands
```

### Warnung bei schwacher Batterie (< 20 %)
```yaml
alias: "WeLock: Batterie schwach"
triggers:
  - trigger: numeric_state
    entity_id: sensor.welock_haustur_batterie
    below: 20
actions:
  - action: notify.notify
    data:
      title: "⚠️ WeLock-Batterie fast leer"
      message: "Akkustand: {{ states('sensor.welock_haustur_batterie') }} %. Bitte AAA-Batterien wechseln."
mode: single
```

### Haustür per NFC-Tag öffnen
```yaml
alias: "WeLock: Haustür per NFC entriegeln"
triggers:
  - trigger: tag
    tag_id: haustuer-nfc
actions:
  - action: lock.unlock
    target:
      entity_id: lock.welock_haustur
mode: single
```

> Jedes Entriegeln meldet die WeLock-App ab, und zwischen zwei Entriegelungen liegen mindestens 30 s.

---

## 🌍 Sprachen / Languages

Einrichtung, Optionen und Entitäten sind lokalisiert: 🇩🇪 Deutsch · 🇬🇧 English · 🇪🇸 Español · 🇫🇷 Français.

---

## 🏗 Repository-Architektur

```text
welock-aistudio/
├── custom_components/welock/      # Home Assistant HACS Integration
│   ├── __init__.py                # Setup/Unload, Migration (1.x → Neuanlage)
│   ├── manifest.json              # Manifest inkl. Bluetooth-Matcher "WeLock*"
│   ├── config_flow.py             # Einrichtung: Discovery → Login → Auswahl → BLE-Prüfung; Reauth; Optionen
│   ├── api.py                     # WeLock-Cloud-Client (Login, Geräteliste, Unlock-Befehl)
│   ├── ble.py                     # BLE-Transport über HA-Bluetooth (Challenge, Befehl schreiben)
│   ├── protocol.py                # Nordic-UART-UUIDs, Status-/Befehlsformate (ohne I/O)
│   ├── coordinator.py             # Erreichbarkeit, RSSI, Akku; serialisiert BLE-Zugriffe
│   ├── entity.py                  # Gemeinsame Geräteinfo
│   ├── lock.py                    # Lock-Entität (angenommener Zustand, Auto-Relock-Anzeige)
│   ├── sensor.py                  # Batterie, Signalstärke
│   ├── binary_sensor.py           # Bluetooth erreichbar
│   ├── diagnostics.py             # Diagnosedaten (geschwärzt)
│   ├── strings.json               # Basistexte (EN)
│   └── translations/              # de, en, es, fr
├── docs/                          # Reverse-Engineering-Methodik (anonymisiert, § 69e UrhG)
├── tools/                         # BLE- & Cloud-Diagnosetools (siehe tools/README.md)
├── tests/                         # Unit-Tests + optionaler Live-Smoke-Test (Marker "live")
├── archiv/                        # Archivierte Entwicklungsstände
├── src/, index.html, package.json # Begleitende Web-App (AI Studio)
├── hacs.json · info.md            # HACS-Metadaten & Store-Beschreibung
├── CHANGELOG.md · CONTRIBUTING.md · SECURITY.md
└── LICENSE                        # MIT
```

---

## 📄 Lizenz

Lizenziert unter der MIT-Lizenz, siehe [LICENSE](LICENSE).
