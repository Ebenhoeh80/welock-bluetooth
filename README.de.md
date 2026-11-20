# WeLock Smart Lock BLE — Home Assistant HACS Integration & BLE Diagnose-Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Ebenhoeh80/welock-bluetooth?style=for-the-badge&color=blue)](https://github.com/Ebenhoeh80/welock-bluetooth/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-sprachen--languages)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Spenden via PayPal](https://img.shields.io/badge/❤%20Spenden-PayPal-00457C.svg?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/pool/9p84qTHCFr?sr=wccr)

**🌍 Sprache:** [🇬🇧 English](README.md) · **🇩🇪 Deutsch**

Suite für **WeLock Smart Door Locks** (z. B. Touch41, SECBN51, PCB41, SECBREBL01):

1. 🏠 **Home Assistant HACS Integration** (`custom_components/welock`): Entriegeln per Bluetooth über den Home-Assistant-Bluetooth-Stack (lokaler Adapter oder ESPHome-Bluetooth-Proxy). Die WeLock-Cloud liefert dabei nur den einmaligen Entriegelungsbefehl. Mit geführter Einrichtung, Bluetooth-Discovery, Akku-, Signal- und Erreichbarkeitssensoren.
2. 🔬 **BLE & Cloud Diagnose-Tools** ([`tools/`](tools/README.md)): Python-Werkzeuge für BLE-Suche, Akkustand/Challenge, GATT-Inspektion, Cloud-Login und Entriegelungstests.

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
     │  3. Befehl schreiben  ───────────────▶│  Knauf kuppelt ~10 s ein  │
```

* Die Cloud wird **nur** bei Einrichtung, erneuter Anmeldung und beim Entriegeln kontaktiert. Es gibt **kein Cloud-Polling**.
* Erreichbarkeit und Signalstärke kommen aus dem Home-Assistant-Bluetooth-Stack, der Akkustand direkt vom Schloss.
* Jeder Entriegelungsbefehl hängt am Ein-Byte-Challenge-Wert (`randomFactor`) des Schlosses, der nur **256** mögliche Werte hat. Ein abgefangener Befehl kann daher erneut funktionieren, wenn derselbe Wert wieder auftritt — der BLE-Verkehr ist **nicht** replay-sicher. Gelernte Befehle werden zudem lokal im Home-Assistant-Speicher zwischengespeichert.

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
2. URL `https://github.com/Ebenhoeh80/welock-bluetooth` eingeben, Kategorie **Integration**, **Hinzufügen**.
3. **WeLock Smart Lock** suchen → **Herunterladen** → Home Assistant **neu starten**.

### Manuell
1. Neuestes [Release](https://github.com/Ebenhoeh80/welock-bluetooth/releases) herunterladen.
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
| `switch.<name>_offline_entsperren` | Schalter (Konfiguration) | Schaltet das [Offline-Entsperren](#-lokaler-offline-unlock-experimentell) mit sofortiger Wirkung ein oder aus; die Einstellung bleibt über Neustarts erhalten. Standardmäßig aus. |
| `sensor.<name>_entsperrungen_uber_die_cloud` | Sensor | Anzahl der Entsperrungen, deren Befehl von der WeLock-Cloud kam. Attribute: `confirmed`, `unconfirmed`, `failed`, `average_duration_ms`. |
| `sensor.<name>_entsperrungen_offline` | Sensor | Anzahl der Entsperrungen, deren Befehl aus dem lokalen Cache kam (ohne Cloud-Kontakt). Gleiche Attribute. |
| `event.<name>_entsperr_verlauf` | Event | Ein Ereignis je Entsperrversuch (`unlock_cloud`, `unlock_offline`, `unlock_failed`) mit Pfad, Ergebnis, Dauer und Challenge-Wert. Erscheint im Logbuch und im Verlauf. |
| `sensor.<name>_letzter_entsperrversuch` | Sensor (Diagnose) | Zeitpunkt des letzten Entsperrversuchs; die Attribute enthalten Ergebnis und die zehn letzten Versuche. |
| `sensor.<name>_letzter_zugriff` | Sensor (Diagnose, standardmäßig deaktiviert) | Letzter Eintrag des Zutrittsprotokolls (wer, wann, wie). Bleibt `unbekannt`, bis der Dienst `welock.fetch_access_log` einmal ausgeführt wurde; die zuletzt abgerufenen Einträge bleiben über Neustarts erhalten. |

Die genauen Entity-IDs hängen vom BLE-Namen und von der HA-Sprache ab.

---

## ⚙️ Optionen

**Einstellungen → Geräte & Dienste → WeLock → Konfigurieren**

| Option | Standard | Bereich | Bedeutung |
| :--- | :---: | :---: | :--- |
| Als entriegelt anzeigen für | 10 s | 3–60 s | So lange zeigt das Lock nach dem Entriegeln „entriegelt“. Danach wieder „verriegelt“. |
| Akkustand per Bluetooth lesen alle | 24 h | 0–168 h | Regelmäßige BLE-Statusabfrage. `0` = nur beim Entriegeln (schont die Schlossbatterie). |
| Bluetooth-Erreichbarkeit prüfen alle | 60 s | 10–600 s | Wie oft Erreichbarkeit und RSSI aus dem HA-Bluetooth-Cache aktualisiert werden. Erzeugt **keinen** Funkverkehr. |
| Lokalen Befehls-Cache aufbauen und nutzen | aus | an/aus | **Experimentell.** Entriegelt bei bekanntem Challenge-Wert lokal ohne Cloud. Auch als Schalter-Entität verfügbar. Siehe unten. |

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

* **Schalter:** `switch.<name>_offline_entsperren` schaltet die Funktion jederzeit
  ein oder aus, per Oberfläche oder Automation. Die Änderung gilt sofort (ohne
  Neuladen), bleibt über Neustarts erhalten und ist dieselbe Einstellung wie die
  Option im Dialog *Konfigurieren* der Integration.
* **Statistik und Verlauf:** Jede Entsperrung über Home Assistant wird mit dem
  Pfad, der den Befehl geliefert hat (`cloud` oder `offline`), dem Ergebnis und
  der Dauer festgehalten. Die Zähler und die letzten 100 Versuche überstehen
  Neustarts und erscheinen als Sensoren *Entsperrungen über die Cloud* /
  *Entsperrungen offline*, als Event-Entität *Entsperr-Verlauf* (Logbuch) und im
  Diagnose-Download. *Confirmed* heißt: Das Schloss hat den Befehl mit einer
  Benachrichtigung beantwortet; *unconfirmed*: Der Befehl wurde geschrieben, aber
  keine Antwort gesehen (das Schloss sendet nicht immer eine); *failed*: Fehler
  vor oder beim Schreiben.
* **Sicherheitsnetz:** Schlägt das Schreiben eines **gespeicherten** Befehls fehl,
  wird dieser Befehl aus dem Cache entfernt; die nächste Entsperrung für diesen
  Challenge-Wert fragt wieder die Cloud.

### Befehlstabelle importieren

Wenn du die Befehle deines Schlosses schon hast (eine JSON-Datei mit
`device_number` und einer `table` mit randomFactor `"0"`..`"255"` auf Befehl, wie
sie `tools/welock_offline_oracle.py --harvest` schreibt), musst du nicht warten,
bis die Integration sie einzeln gelernt hat:

1. Kopiere die Datei in den Home-Assistant-Konfigurationsordner, zum Beispiel als
   `welock-oracle-table.json` (das File-Editor-Add-on oder Samba genügen).
2. **Entwicklerwerkzeuge → Aktionen → WeLock: Befehlstabelle importieren**,
   Dateinamen setzen (Standard ist `welock-oracle-table.json`) und ausführen. Die
   Antwort zeigt `added`, `unchanged`, `conflicts` und `known`.
3. Schalte den Schalter *Offline-Entsperren* ein, wenn du die Befehle nutzen
   willst.

Die Datei wird vollständig geprüft, bevor etwas gespeichert wird: Ein falsches
Format, ein ungültiger Befehl oder die Tabelle eines anderen Schlosses (die
`device_number` muss zum Schloss passen) lehnt sie ab. Ein bereits gespeicherter
Befehl wird nie überschrieben; weicht die Datei von einem aus der Cloud gelernten
Befehl ab, steht der randomFactor unter `conflicts` und der gelernte Befehl
bleibt. Der Dienst schaltet das Offline-Entsperren nicht ein und schreibt nichts
an das Schloss.

> ⚠️ Eine Befehlstabelle ist **sicherheitsrelevant**: Zusammen mit
> Bluetooth-Reichweite kann sie genügen, deine Tür zu entriegeln, falls das
> Schloss die Befehle erneut akzeptiert. Halte die Datei privat, lade sie nie in
> ein Repository und gib sie nicht weiter. Lösche sie nach dem Import aus dem
> Konfigurationsordner, wenn du sie nicht mehr brauchst.

### Offline-Entsperren am eigenen Schloss prüfen

Um zu prüfen (und zu dokumentieren), dass das Offline-Entsperren wirklich
funktioniert, führe eine Serie von Entsperrungen durch und lies die Zähler:

1. Lass die Tabelle sich füllen (normaler Betrieb bei **ausgeschaltetem**
   Schalter) oder prüfe `learned_commands` am Schalter.
2. Schalte den Schalter **ein**. Entsperre die Tür mehrmals im Abstand von
   mindestens 12 s und notiere jedes Mal per Augenschein, ob der Zylinder wirklich
   freigegeben hat.
3. Vergleiche *Entsperrungen offline* mit deinen Notizen: `confirmed` +
   `unconfirmed` ist das, was dem Schloss gesendet wurde, dein Augenschein ist die
   Wahrheit. Noch nicht gespeicherte Challenge-Werte beantwortet die Cloud; sie
   erscheinen stattdessen unter *Entsperrungen über die Cloud*.
4. Als Beleg, dass **keine Cloud nötig** ist, sperre den Internetzugang für Home
   Assistant (oder den WeLock-Cloud-Host) und wiederhole Schritt 2.
   Offline-Entsperrungen werden weiter gezählt; `unlock_failed`-Ereignisse mit
   `path: cloud` zeigen, dass die Cloud nicht erreichbar war.
5. Optional danach `welock.fetch_access_log` ausführen. Das eigene Protokoll des
   Schlosses sollte dieselben Entsperrungen auflisten (das meldet die WeLock-App
   einmal ab).

> ✅ **Bisher am Schloss des Maintainers verifiziert (20.11.2026):** Bei drei
> Offline-Entsperrungen, jeweils mit einem Befehl aus der lokalen Tabelle und ohne
> Cloud-Anfrage, gab der Zylinder jedes Mal frei (per Augenschein geprüft); das
> Schloss bestätigte außerdem alle bisher gezählten 15 Offline-Entsperrungen. Eine
> längere Serie (30+ Entsperrungen) und ein Test mit gesperrter Cloud sind noch zu
> dokumentieren. Die Option bleibt standardmäßig **aus**, die Cloud bleibt der
> Standardpfad; schalte sie ein, nachdem du es an deinem eigenen Schloss getestet
> hast (siehe oben).

> 📚 **Wie es funktioniert:** Eine kurze Beschreibung des Bluetooth-Austauschs und
> der Cloud-Anfrage steht in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## 📜 Zutrittsprotokoll (Dienst)

Der Dienst **`welock.fetch_access_log`** holt das Zutrittsprotokoll (wer, wann,
mit welcher Methode) aus der Cloud und schreibt es in den Sensor *Letzter
Zugriff* (Attribute inkl. der letzten Einträge).

Der Sensor zeigt deshalb `unbekannt`, bis du den Dienst einmal ausgeführt hast. Er
wird nie von selbst aktualisiert, die zuletzt abgerufenen Einträge werden aber
nach einem **Neustart oder Neuladen wiederhergestellt**. Führe den Dienst erneut
aus, wenn du frische Daten möchtest, z. B. per Skript oder per Automation, die
du selbst auslöst.

> ⚠️ Jeder Abruf **meldet andere Sitzungen des Kontos ab** (z. B. die WeLock-App),
> da ein Cloud-Login nötig ist. Deshalb wird **nur auf Abruf** geladen, nicht
> automatisch. Die Telefonnummer aus dem Rohdatensatz wird bewusst **nicht**
> übernommen.

---

## 🔄 Betrieb & Verhalten

* **Entriegeln über die Cloud meldet die WeLock-App ab.** Für den Befehl ist dann ein frischer Cloud-Login nötig – eine Eigenschaft der WeLock-Cloud. Bei einem Treffer im [lokalen Befehls-Cache](#-lokaler-offline-unlock-experimentell) entfällt der Cloud-Login (und damit die Abmeldung).
* **Mindestens 12 s zwischen zwei Entriegelungen.** Der Knauf bleibt 10 s eingekuppelt und das Schloss nimmt dabei keinen weiteren Befehl an; ein früherer Versuch wird mit einer Meldung abgelehnt.
* **Angenommener Zustand:** Das Schloss meldet seinen Zustand nicht. Der Zylinder kuppelt den Außenknauf 10 s (gemessen) ein und verriegelt danach mechanisch von selbst. „Verriegeln“ in HA setzt nur die Anzeige zurück.
* **Ohne Bluetooth-Reichweite** ist das Lock *nicht verfügbar*. Die Cloud allein kann nicht entriegeln.
* Alle BLE-Zugriffe auf ein Schloss laufen nacheinander, damit Akkuabfrage und Entriegeln nicht kollidieren.

### Wie lange ist der Zylinder frei?

Beim Schloss des Maintainers bleibt der Außenknauf nach dem Eintreffen des
Entsperrbefehls **10 Sekunden** eingekuppelt und verriegelt danach mechanisch von
selbst (das Schloss meldet keinen Zustand, der Wert wurde durch Ausprobieren
ermittelt: bei 10 s ließ sich der Knauf noch drehen). Deshalb ist *Als entriegelt
anzeigen für* standardmäßig 10 s, und deshalb nimmt das Schloss in dieser Zeit
**keinen zweiten Befehl** an (siehe die 12 s Mindestabstand zwischen zwei
Entriegelungen oben). *Als entriegelt anzeigen für* steuert nur, wie lange Home
Assistant „entriegelt“ *anzeigt*; am Schloss ändert es nichts.

Andere Schlossmodelle oder Firmware können abweichen. So prüfst du deines: Über
Home Assistant entriegeln, die Stoppuhr starten, sobald die Tür auf *entriegelt*
springt, und nach 5, 10 und 15 s versuchen, den Zylinder zu drehen (für jeden
Versuch neu entriegeln, mindestens 12 s Abstand). Dann *Als entriegelt anzeigen
für* etwas unter den Punkt setzen, an dem es nicht mehr geht.

Das Event *Entsperr-Verlauf* und der Sensor *Letzter Entsperrversuch* halten fest,
wann der Befehl geschrieben wurde; das hilft beim Vergleich mehrerer Versuche.

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
| *Bitte … s warten* | Die 12-Sekunden-Sperre zwischen zwei Entriegelungen ist noch aktiv. |

**Debug-Logs** (`configuration.yaml`):
```yaml
logger:
  logs:
    custom_components.welock: debug
```
Die **Diagnosedaten** (Gerät → Diagnose herunterladen) enthalten weder Konto noch Passwort.

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

> Jedes Entriegeln meldet die WeLock-App ab, und zwischen zwei Entriegelungen liegen mindestens 12 s.

---

## 🌍 Sprachen / Languages

Einrichtung, Optionen und Entitäten sind lokalisiert: 🇩🇪 Deutsch · 🇬🇧 English · 🇪🇸 Español · 🇫🇷 Français.

---

## 🏗 Repository-Architektur

```text
welock-bluetooth/
├── custom_components/welock/      # Home Assistant HACS Integration
│   ├── __init__.py                # Setup/Unload
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
├── docs/                          # Kurze Protokollbeschreibung
├── tools/                         # BLE- & Cloud-Diagnosetools (siehe tools/README.md)
├── tests/                         # Unit-Tests + optionaler Live-Smoke-Test (Marker "live")
├── src/, index.html, package.json # Begleitende Web-App (AI Studio)
├── hacs.json · info.md            # HACS-Metadaten & Store-Beschreibung
├── CHANGELOG.md · CONTRIBUTING.md · SECURITY.md
└── LICENSE                        # MIT
```

---

## 📄 Lizenz

Lizenziert unter der MIT-Lizenz, siehe [LICENSE](LICENSE).

---

## ❤️ Projekt unterstützen

<div align="center">

**Ich entwickle und pflege diese Integration in meiner Freizeit – und trage die laufenden Kosten aus eigener Tasche.**

Wenn sie dir Zeit oder Ärger erspart, hält eine kleine freiwillige Spende das Projekt am Leben und motiviert zu neuen Funktionen.
Jeder Beitrag, egal wie klein, freut mich riesig. Vielen Dank! 🙏

<a href="https://www.paypal.com/pool/9p84qTHCFr?sr=wccr">
  <img src="https://img.shields.io/badge/Spendier%20mir%20einen%20Kaffee-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Spenden via PayPal" height="42">
</a>

</div>
