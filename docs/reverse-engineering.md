# WELOCK Reverse Engineering – Notizen und Vorgehen

## Ziel

Analyse der Android-App von WELOCK, um die Bluetooth-Kommunikation mit dem Smart Lock zu verstehen und langfristig eine eigene Anbindung (z. B. Home Assistant) zu entwickeln.

---

## Rechtliche Grundlage

In Deutschland und der EU ist Reverse Engineering zur Herstellung von Interoperabilität grundsätzlich zulässig (§ 69e UrhG), sofern:

- die Software rechtmäßig erworben wurde,
- die Informationen für die Interoperabilität erforderlich sind,
- keine urheberrechtlich geschützten Programmteile kopiert werden.

---

# 1. Android-Gerät verbunden

ADB-Verbindung geprüft:

```powershell
adb devices
```

Ausgabe:

```text
List of devices attached
ANDROIDSERIAL     device
```

---

# 2. Paketname der WELOCK-App ermittelt

Suche nach installiertem Paket:

```powershell
adb shell pm list packages | findstr -i welock
```

Ergebnis:

```text
package:cn.sixpower.wlock
```

Verifikation:

- `cn.sixpower.wlock` entspricht der offiziellen WELOCK-App im Google Play Store.

---

# 3. APK-Pfad auf dem Gerät ermittelt

```powershell
adb shell pm path cn.sixpower.wlock
```

Ergebnis:

```text
package:/data/app/~~y4YL-QWwYTiaqLzivJ9ziA==/cn.s~~power.wlock-zyOEyyG6-Wz6MwY~~CUuZQ==/base.apk
```

---

# ~~ APK heruntergeladen

```powershe~~
adb pull~~data/app/~~y4YL-QWwYTiaqLzivJ9ziA==/cn.sixpower.wlock-zyOEyyG6-Wz6MwYIzCUuZQ==/base.apk welock.apk
```

Datei vorhanden:

```text
welock.apk
58 MB
```

---

# 5. APK untersucht

Anzahl der DEX-Dateien geprüft:

```powershell
tar -tf .\welock.apk | findstr classes
```

Ergebnis:

```text
classes.dex
classes2.dex
```

Erkenntnisse:

- Mehrere DEX-Dateien vorhanden
- App enthält regulären Java/Kotlin-Code
- Gute Chancen auf Analyse ohne Native Reverse Engineering

---

# 6. APK mit JADX dekompiliert

Dekompilierung durchgeführt.

Ergebnisordner:

```text
./welock-jadx
```

Enthält:

- dekompilierten Java-Code
- Kotlin-Code
- Ressourcen
- lesbare Klassenstruktur

---

# 7. APK zusätzlich mit APKTool dekompiliert

Dekompilierung durchgeführt.

Ergebnisordner:

```text
./welock-apktool
```

Enthält:

- AndroidManifest.xml
- resources
- smali-Code
- Assets
- Konfigurationsdateien

---

# 8. Erste Bluetooth-Spuren gefunden

Suche im dekompilierten Material:

```powershell
Get-ChildItem -Recurse .\welock\ | Select-String "BluetoothGatt"
```

Erkenntnisse:

Gefundene Android-Bluetooth-Klassen:

```text
BluetoothGatt
BluetoothGattCallback
BluetoothGattCharacteristic
BluetoothGattDescriptor
BluetoothDevice
BluetoothLeScanner
ScanCallback
ScanResult
```

Dies bestätigt:

- Nutzung von Bluetooth Low Energy (BLE)
- Kommunikation erfolgt über Android BLE API

---

# 9. Nordic DFU-Bibliothek gefunden

Gefundene Klassen:

```text
no.nordicsemi.android.dfu.*
```

Beispiele:

```text
DfuBaseService
SecureDfuImpl
LegacyDfuImpl
DfuServiceInitiator
```

Bedeutung:

- Firmware-Updates werden über Nordic DFU unterstützt.
- Das Schloss besitzt wahrscheinlich Nordic-ähnliche BLE-Firmware oder nutzt entsprechende Libraries.

---

# 10. Interessante Fehlermeldung entdeckt

Gefundener String:

```text
no instance of BluetoothGatt, have you connected first?
```

Bedeutung:

- Bluetooth-Kommunikation wird im Java/Kotlin-Code verwaltet.
- Kein Hinweis darauf, dass sämtliche Logik nur in nativen Bibliotheken verborgen ist.

---

# 11. Geplanter nächster Schritt

Analyse des dekompilierten Quellenbaums:

Suche nach BLE-Schreibzugriffen:

```powershell
Get-ChildItem .\welock-jadx\sources -Recurse -Include *.java |
Select-String "writeCharac*eristic"
```

Suche nach UUIDs:

`*`powershell
Get-ChildItem .\welock*jadx\sources -Recurse -Include *.j*va |
Select-String "UUID.fromStrin*"
```

Suche nach Kryptografie:

`*`powershell
Get-ChildItem .\welock*jadx\sources -Recurse -Include *.j*va |
Select-String "Cipher.getInst*nce"
```

```*owershell
Get-ChildItem .\welock-j*dx\sources -Recurse -Include *.jav* |
Select-String "SecretKeySpec"
`*`

```powershell
Get-ChildItem .\w*lock-jadx\sources -Recurse -Includ* *.java |
Select-String "AES"
```
*---

# 12. Alternativer Analysepfa*

Bluetooth-Verkehr direkt mitschn*iden:

Android:

```text
Entwickle*optionen
→ Bluetooth HCI Snoop Log*aktivieren
```

Danach:

1. App st*rten
2. Schloss verbinden
3. Öff*en
4. Schließen

Logdatei auslesen*und anschließend mit Wireshark ana*ysieren.

Ziel:

- Service UUIDs f*nden
- Characteristic UUID* finden
- Authentifizierungsablauf*verstehen
- Lock- und Unlock-Komma*dos identifizieren

---

# Lang*ristiges Ziel

Ermittlung von:

- *LE Service UUID
- BLE Characterist*c UUID
- Authentifizierungsverfahr*n
- Statusabfrage
- Lock-Kommando
* Unlock-Kommando

Anschließend Ent*icklung einer:

* Home Assistant Integration
- ESPH*me-Kom*onente
- Python-Lösung mit `bleak`*
Beispiel:

```python
from bleak i*port BleakClient

async with*BleakClient(mac) as client:
    aw*it client.write_gatt_char(
       *characteristic_uuid,
        unloc*_payload
    )
```

---
Stand* 07.11.2026

---

## Current shortest path to a working Python unlock implementation

**Status 08.11.2026:** Drei cloudgestützte Unlocks mit Python und BLE sind
mechanisch durch den Nutzer bestätigt. Eine weitergehende Zuverlässigkeitsprüfung
steht noch aus; ein rein lokaler Unlock ohne Cloud ist weiterhin nicht
nachgewiesen. Details stehen in der
[Cloud-Analyse](WELOCK-CLOUD-ANALYSE.md#erster-cloud-command-und-vorbereiteter-einzelversuch).

**Experimenteller Cloud-Baustein:** [welock_cloud_login.py](../tools/welock_cloud_login.py)
implementiert einen experimentellen Login, keinen Unlock-Client. Der Nutzer
wird vor dem Login auf die Abmeldung anderer
Geräte hingewiesen und muss zustimmen; das Passwort wird ausschließlich verdeckt
lokal eingegeben. [Details, Herkunft und Einschränkungen](WELOCK-CLOUD-ANALYSE.md#experimenteller-python-cloud-login).
Am 08.11.2026 wurde der Login mit einem echten Konto akzeptiert.

**Historische Probe:** [welock_command_probe.py](../tools/welock_command_probe.py)
fordert nach Login und frischer BLE-Batterieantwort einen Cloud-Command an.
Bei zwei echten Versuchen wurde die Command-Anfrage mit Code 2003 abgelehnt.
Dabei verwendete die Probe fälschlich den übergeordneten Gerätenamen; die
App verwendet in dem untersuchten Pfad den Namen eines verschachtelten
BLE-Eintrags. Die Probe kann diesen nun nach manueller Auswahl aus der
ersten Seite der Cloud-Geräteliste übernehmen; mit dieser Korrektur wurde
ein Cloud-Command erfolgreich angefordert. Die Probe sendet keinen Unlock-Write
und speichert einen erhaltenen Command nicht. Voraussetzungen und Grenzen:
[Command-Probe](WELOCK-CLOUD-ANALYSE.md#experimentelle-cloud-command-probe).

**Praktischer Pfad:** `welock_unlock_experiment.py`
fordert nach ausdrücklicher Bestätigung einen frischen Cloud-Command an und
schreibt ihn in derselben BLE-Verbindung. Der Nutzer bestätigte drei echte
mechanische Entriegelungen, die dritte nach Entfernen der festen Wartezeit
von 35 Sekunden. Mehr als 30 Sekunden Abstand zwischen Versuchen sind weiterhin vom Nutzer
einzuhalten und werden nicht automatisch geprüft. Das Skript ist noch
experimentell; es speichert weder Passwort, Token noch Command und meldet
die mechanische Wirkung nicht selbst. Ein Login kann andere Sitzungen abmelden.

**Separates Projekt:** `welock-client` bündelt den
Cloud- und BLE-Ablauf als installierbares Python-Paket. Dieses Paket wurde
automatisiert simuliert, aber selbst noch nicht am echten Schloss getestet.

**Neuer kürzester Pfad:** Die App fragt zunächst per BLE Batterie und einen
`randomFactor` ab. `BleLockOperateFaceImpl::_sendOpen` übergibt beide Werte
an `CommandService::getOpenBytes`; diese Methode fordert bei der WELOCK-API
einen Befehl an. Das zurückgelieferte Feld `command` wird hex-dekodiert
und über `_sendCmd` / `_writeData` an die Write-Characteristic übergeben.
Dies ist ein statisch rekonstruierter App-Pfad, noch kein dynamisch bestätigter
Zusammenhang zwischen Serverantwort und konkretem HCI-Folge-Write der App.
Der Python-Ablauf funktionierte dreimal mit Cloud-Unterstützung; das Verhalten
anderer Geräte, die langfristige Zuverlässigkeit und die Offline-Erzeugung bleiben offen.
Details einschließlich
REA-Gegenprüfung und Dateioffsets:
[Flutter-AOT-Analyse](FLUTTER-AOT-ANALYSE.md#fortschreibung-blutter-und-rea-funktionsanalyse).

**Cloud-Audit (read-only):** Die WeLock-Cloud-API liefert über lesende
Endpunkte deutlich mehr als den Unlock-Befehl. `/device/GetUnlockRecord` ist
ein vollständiges **Zutrittsprotokoll** (wer, wann, mit welcher Methode,
Ergebnis), `/device/PermissionList` und `/device/GetDeivceInfo` listen die
**berechtigten Nutzer** samt Rolle und Gültigkeit. Am eigenen Konto live
bestätigt (12.11.2026, Modell `SECBREBL01`). `GetDeivceInfo` enthält zudem pro
BLE-Modul ein 24-stelliges `devicePassword` und das Geräte-Feature
„BLE-Kommunikationsschlüssel ändern". Werkzeug:
[welock_cloud_audit.py](../tools/welock_cloud_audit.py); Belege:
[Cloud-API-Inventar](WELOCK-CLOUD-ANALYSE.md#cloud-api-inventar-und-zutritts-berechtigungsdaten-12-november-2026).

**Offline-Forschung (12.11.2026):** Eine **differenzielle Analyse** (gezielte
Einzelbit-Variation der Eingaben, kein BLE-Write) hat den Befehlsaufbau
weitgehend aufgeklärt. Ergebnis: Der Cloud-`command` ist eine **Funktion von
`randomFactor` allein** – `battery` und `devicePassword` gehen nicht variabel
ein. Da `rf` ein einzelnes Byte ist, existieren nur **256 mögliche Befehle** pro
Schloss. Positionen 0–7 folgen näherungsweise `(rf*k)>>2 & 63` (für kleine `rf`
exakt, im Vollbereich mit vereinzelten Ausnahmen), 8–11 sind konstant, Position
12 ist eine Prüfziffer. Die frühere **3DES/AES-Hypothese ist widerlegt**; der
Befehl ist eine Kodierung des Challenge-Bytes, kein verschlüsseltes Token.
Maßgeblich für die Offline-Erzeugung ist die **geerntete Tabelle `rf→command`**:
[welock_offline_oracle.py](../tools/welock_offline_oracle.py) `--harvest` lädt sie
einmalig (kein BLE-Write) und erzeugt danach Befehle rein offline (`--table …
--rf N`, verifiziert). Die Cloud drosselt nach ~146 Anfragen (daher in mehreren
`--resume`-Läufen geerntet); die Tabelle ist nun **vollständig (256/256)**. Offen
bleibt nur die **mechanische Verifikation
vor Ort** (mögliche geräteseitige Replay-Sperre). Werkzeuge:
[welock_offline_experiment.py](../tools/welock_offline_experiment.py)
`--differential`, [welock_offline_oracle.py](../tools/welock_offline_oracle.py);
Belege:
[Differenzielle Analyse](WELOCK-CLOUD-ANALYSE.md#differenzielle-analyse-command-ist-eine-funktion-von-randomfactor-allein-12-november-2026).

Die vom Nutzer bereitgestellten Smartphone-Benachrichtigungen wurden mit
einem neuen HCI-Mitschnitt verglichen. Drei passende Sequenzen sind nach
vorläufiger Zeitkorrektur zeitlich zuordenbar; ein zusätzlicher ähnlicher
Ablauf belegt, dass die Paketform allein keinen Erfolg beweist.
[Details und Einschränkungen](WELOCK-HCI-ANALYSE.md#smartphone-benachrichtigungen-vom-8-november-2026).
Die projektspezifischen Dokumentationsregeln stehen unter
[instructions](PROJEKT-DOKUMENTATION.md); die
[Unlock-Strategie](UNLOCK-STRATEGIE.md) priorisiert
Experimente nach erwartetem Fortschritt.

**Historischer Stand vor dem erfolgreichen Python-Versuch:** Der folgende
Abschnitt und die anschließenden Tabellen dokumentieren den damaligen
Untersuchungsstand; überholte Angaben gelten nicht für das oben beschriebene
Ergebnis.

Ein für eine neue BLE-Antwort
gültiger Unlock-Befehl und seine Erzeugung sind nicht verfügbar. Ein einzelner
markierter App-Tap wurde bei ausgeschaltetem WLAN und ausgeschalteten mobilen
Daten durchgeführt. Im zeitlich zugeordneten HCI-Ausschnitt wurden eine
Batterieabfrage und ihre Antwort, aber kein nachfolgender Write beobachtet.
Der Nutzer berichtet inzwischen für den Offline-App-Ablauf „Connect success“,
„Request network failed“ und keine Entriegelung. Die HCI-Zuordnung setzt die
bisher nur vorläufig erklärte einstündige HCI-Zeitkorrektur voraus. Dies
beweist weder eine zwingende Cloud-Abhängigkeit noch die Ursache des
ausbleibenden Writes. [Versuchsdetails](WELOCK-HCI-ANALYSE.md#kontrollierter-offline-versuch-vom-8-november-2026).
Nächster Schritt ist die autorisierte lokale Beobachtung der
Serverauthentifizierung und der Antwort bei wiederhergestellter Verbindung,
ohne Zugangsdaten offenzulegen.

| Protokollmodell | Vertrauen | Stärkste verbleibende Grenze |
|---|---|---|
| Beobachtete GATT-UUIDs und Schreibmodus | Hoch | Keine Aussage über andere Modelle oder Firmware. |
| Batterieabfrage und Zuordnung der vierbyteigen Antwort | Hoch für das untersuchte Format | Andere Antwortvarianten nicht vollständig geklärt. |
| Serveranforderung und Weitergabe von `command` an BLE | Hoch für den statischen App-Pfad | Cloud-Antwort und konkreter BLE-Write bislang nicht dynamisch korreliert. |
| Notwendigkeit einer Internetverbindung | Hoch für den berichteten getesteten App-Ablauf | Offline keine Entriegelung laut Nutzer; ein grundsätzlich möglicher Offline-Client oder die genaue Fehlerursache sind nicht widerlegt. |
| Unabhängiger Unlock und Befehlserzeugung | Nicht nachgewiesen | Keine validierte Erzeugung eines aktuellen Befehls, keine mechanische Verifikation. |

Ein neuer [Cloud- und Storage-Bericht](WELOCK-CLOUD-ANALYSE.md) dokumentiert
die Error-Closure, Speicherbefunde und den vorbereiteten Frida-Hook. Ein
autorisierter Attach-Weg und eine dynamische Serverantwort fehlen weiterhin.
Die [Herkunft von request.value](WELOCK-CLOUD-ANALYSE.md#herkunft-von-requestvalue-beim-unlock)
trennt direkte App-Datenflüsse von noch unbekannten Server- und
Schlossabhängigkeiten und beschreibt ein gezieltes Folgeexperiment.
Eine [gezielte Vertiefung zu randomFactor und HTTP](WELOCK-CLOUD-ANALYSE.md#vertiefung-randomfactor-bis-command-8-november-2026)
erfasst zusätzliche Parserzweige, HTTP-Header und Grenzen der
Serverrekonstruktion.
Ein erneuter read-only Aufruf des lokalen REA-MCP-Servers bestätigte die
installierte App-Version 4.5.8; ein Klartext-Capture und ein Zugriff auf die
Flutter-TLS-Daten fehlen weiterhin. [MCP-Prüfung](WELOCK-CLOUD-ANALYSE.md#rea-mcp-prüfung-vom-8-november-2026).
Die [Bewertung der command-Erzeugung](WELOCK-CLOUD-ANALYSE.md#bewertung-der-command-erzeugung-anhand-der-projektdokumentation)
trennt Serverbereitstellung von unbekannter Serverberechnung und lokalem
Suffix. Das gemeldete WLAN-Logging ist nicht als HTTPS-Klartextzugang
verifiziert; der Instrumentierungsblocker besteht fort.
Die [Einordnung öffentlicher Arbeiten](WELOCK-CLOUD-ANALYSE.md#einordnung-öffentlicher-arbeiten-lokale-lösung)
zeigt einen älteren lokalen BLE-Pfad, aber keine belegte Übertragbarkeit auf
dieses Schloss und keine fertige Offline-Implementierung.
Eine spätere Suche fand [welock-desktop](https://github.com/thibauddavid/welock-desktop):
Der Quellcode beschreibt einen cloudgestützten BLE-Unlock, aber verwendet
andere GATT-UUIDs als dieses Schloss. Kompatibilität und mechanischer Erfolg
sind nicht belegt. Seine nur als Binärdatei verfügbare Engine wurde nicht
ausgeführt; Details und ein Parser-Widerspruch stehen im
[Cloud-Bericht](WELOCK-CLOUD-ANALYSE.md#desktop-client-und-seine-opaque-engine).
Der [Hypothesenvergleich](WELOCK-CLOUD-ANALYSE.md#hypothesenvergleich-und-korrelierter-versuchsstand)
stuft H2 als führenden **App-Pfad**, nicht als Beweis gegen einen lokalen
Client ein; HTTP-`nonce` und `sign` wurden zusätzlich statisch lokalisiert.
Der Nutzer berichtet, dass Unlock nach Aktivierung von WLAN wieder
funktioniert. Der [Anmeldepfad](WELOCK-CLOUD-ANALYSE.md#anmeldung-zusätzlicher-statischer-befund)
ist weiter eingegrenzt, aber Login und Authorization bleiben ungetestet;
Zugangsdaten sind derzeit nicht erforderlich.
Die [Strategie für einen lokalen Unlock](WELOCK-CLOUD-ANALYSE.md#strategie-lokaler-unlock-mit-erkenntnissen-aus-criticalsecurity)
ordnet das historische 3DES-Werkzeug ein und priorisiert Berechtigungsquelle,
korrelierte Laufzeitdaten und Offline-Validierung vor einem Bleak-Test.
Die [Bewertung von Hypothese A](WELOCK-CLOUD-ANALYSE.md#bewertung-hypothese-a-lokaler-ble-unlock)
fasst stützende und entgegenstehende Evidenz, unkalibrierte subjektive
Wahrscheinlichkeiten und den nächsten experimentellen Schritt zusammen.

| Schritt / Pfad | Evidenz und Vertrauen | Erwarteter Aufwand | Erkenntnisgewinn und Fortschritt |
|---|---|---|---|
| Android-Write → BLE | Android-Bridge schreibt den von Flutter kommenden Wert; GATT-Service `6e400001-b5a3-f393-e0a9-e50e24dcca9e`, Write `6e400002-b5a3-f393-e0a9-e50e24dcca9e`, Notify `6e400003-b5a3-f393-e0a9-e50e24dcca9e` im Mitschnitt beobachtet. Hoch für Transport, nicht für Unlock-Semantik. | Bereits durchgeführt | Transport für eine spätere Bleak-Implementierung bekannt. |
| Batterieabfrage → Notification → variierender Write | `CommandService::getBatteryBytes` erzeugt `55 30` gefolgt von 13 Nullbytes. Das stimmt bytegenau mit drei ausgewählten Initial-Writes einschließlich Frame 8089 überein. Für die beobachtete 4-Byte-Antwort `55 30 rr bb` weist der AOT-Datenfluss `rr` dem API-Parameter `randomFactor` und `bb` dem Parameter `battery` zu. Die Einordnung als kryptografische Challenge ist nicht bewiesen. | Bereits durchgeführt; weitere Varianten nicht vollständig geprüft | Hoch: Die beiden sitzungsbezogenen API-Parameter sind für dieses Format rekonstruiert. |
| Kontrollierter Android-Lauf | Die App zeigte `DEVICE_NUMBER`; nach 20 s Leerlauf erfolgte ein zeitlich markierter Tap. Frame 8094 ist unter vorläufiger Zeitzonenkorrektur zeitlich zugeordnet; der Nutzer bestätigte die mechanische Entriegelung. Details: [HCI-Analyse](WELOCK-HCI-ANALYSE.md). | Durchgeführt; Kontrolllauf mit Verbindung ohne Unlock fehlt | Hoch für die Zuordnung zum erfolgreichen Ablauf; die genaue Funktion und Erzeugung des Writes bleiben offen. |
| Laufzeit-Instrumentierung vor `request.value` | App ist auf dem Gerät nicht debuggable, `run-as` schlägt fehl, Root wurde nicht nachgewiesen. Direkte Frida-Instrumentierung ist deshalb derzeit blockiert. | Unbekannt; hängt von autorisiertem Instrumentierungsweg ab | Hoch, falls Flutter-/Netzwerk-Daten und Kommandoerzeugung beobachtet werden können; keine Neuinstallation oder Datenlöschung ohne gesonderte Abklärung. |
| Neue REA-HCI-Vergleiche | REA bestätigte acht ausgewählte Frames aus weiteren Nutzeraktionen; identische 4-Byte-Notifications wurden mit teils identischen, teils unterschiedlichen Folge-Writes beobachtet. Belege und Einschränkungen: [HCI-Analyse](WELOCK-HCI-ANALYSE.md). | Bereits durchgeführt | Hoch für wiederholbare Transportbeobachtung; Notification allein reicht nicht aus, um den nächsten Write eindeutig abzuleiten. |
| Flutter-AOT und REA | Build-Werkzeuge wurden nachinstalliert; [Blutter](https://github.com/worawit/blutter) analysierte Dart 3.7.2. REA/Ghidra bestätigte drei ARM64-Aufrufinstruktionen in einem separat extrahierten Funktionsbereich. Der direkte REA-Seed-Versuch auf der ganzen ELF schlug für alle neun Seeds fehl; der isolierte Funktionsbereich hatte eine erkannte Funktion. Details im [AOT-Bericht](FLUTTER-AOT-ANALYSE.md#fortschreibung-blutter-und-rea-funktionsanalyse). | Durchgeführt | Hoch für den Datenpfad; Dart-Objektsemantik und Laufzeitverhalten nicht allein durch Ghidra bewiesen. |
| Cloud-Anforderung | `CommandService::getOpenBytes` sendet eine Map an `/api/Command/UnLock`; die Rückgabe enthält `serverID` und `command`. `HttpUtils::getInstance` setzt unter anderem einen `Authorization`-Header; die verwendeten Dio-Optionen konfigurieren `application/x-www-form-urlencoded`. Login und UserInfo enthalten Konto-/Passwortparameter beziehungsweise Access-/Refresh-Token-Felder. Herkunft und Format des Unlock-Headerwerts und die Laufzeitübertragung bleiben offen; [Belege](FLUTTER-AOT-ANALYSE.md#rekonstruierter-öffnungspfad). | Offen, abhängig von zulässiger lokaler Beobachtung und eigener Anmeldung | Hoch; ohne gültigen Befehl keine belastbare Implementierung. Keine gespeicherten Tokens oder Nutzerdaten an fremde Systeme senden. |
| BLE-Client mit Bleak | Der PC fand den beobachteten Peer, bestätigte dessen GATT-UUIDs und erhielt nach dem beobachteten Initial-Write eine 4-Byte-Notification. Noch fehlen Kommandoerzeugung, Authentifizierung und Erfolgsprüfung. | Transport und erste Antwort verifiziert; Unlock offen | Hoch: Folge-Write erst nach Protokollklärung implementieren und prüfen. Zwischen Entriegelungsversuchen laut Nutzer mehr als 30 Sekunden warten. |

Der eigenständig getestete Parser [tools/welock_protocol.py](../tools/welock_protocol.py)
enthält nur die Batterieabfrage und die beobachtete vierbyteige Antwort,
kein Unlock. Drei gespeicherte Android-Sequenzen und die zuvor aufgezeichnete
Windows-Notification wurden damit lokal geprüft; Rohwerte bleiben geschützt.

Für zukünftige lokale Analysen liegen REA 6.8.0, Ghidra 12.1.2, ein
Linux-JDK 21, Linux-Node 22.23.4 und Linux-TShark 4.2.2 unter
`sensible-daten/werkzeuge/`. Ein REA/Ghidra-Rohlauf mit ausschließlich
diesen Projektkopien wurde erfolgreich geprüft. Die Programme benötigen
weiterhin Ubuntu/WSL und die installierten Systembibliotheken; die Kopien
sind keine vollständige Betriebssystem-Sicherung. Der mehrere Gigabyte große
Werkzeug- und Evidenzordner ist Git-ignoriert, aber innerhalb von OneDrive
und kann synchronisiert werden.

Das Diagnoseprogramm [tools/ble_probe.py](../tools/ble_probe.py) scannt ein
angegebenes Gerät und prüft optional die GATT-UUIDs, **ohne zu schreiben
oder zu entriegeln**. Setup und Beispiel unter Windows:

```powershell
python -m venv sensible-daten\python-venv
.\sensible-daten\python-venv\Scripts\python.exe -m pip install -r tools\requirements-ble.txt
.\sensible-daten\python-venv\Scripts\python.exe tools\ble_probe.py --address "GERÄTEADRESSE" --connect
```

Die Adresse wird bewusst nicht in der Projektdatei veröffentlicht; sie
kann sich ändern. Die beobachteten HCI-Daten liegen unter
`sensible-daten`, das von Git ignoriert wird, sich aber innerhalb von
OneDrive befindet.

Ein historischer [Bericht von CriticalSecurity](https://github.com/CriticalSecurity/welock)
beschreibt für eine ältere App-/API-Version ein BLE-Kommunikationspasswort.
Er belegt nicht, dass die hier untersuchte Version 4.5.8 dasselbe Verfahren
verwendet. Eine aktuelle Home-Assistant-Integration von
[hzjchina/hass-welock](https://github.com/hzjchina/hass-welock) benötigt
laut deren Dokumentation Cloud und WiFi-Box; sie ist kein Nachweis eines
direkten lokalen BLE-Unlocks.
