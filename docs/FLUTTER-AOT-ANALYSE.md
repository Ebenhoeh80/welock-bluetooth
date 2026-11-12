# WELOCK Flutter-AOT: gezielte BLE-Analyse

## Fortschreibung: Blutter und REA-Funktionsanalyse

Der nachfolgende ältere Bericht beschreibt den Stand **vor** der erfolgreichen
Blutter-Analyse. Dessen Aussagen über fehlende Funktionszuordnungen und
Aufrufketten gelten für den damaligen REA-Standardlauf, nicht für die neue
Analyse. Die generierten Dateien sind annotierte Assemblies, keine
rekonstruierten Original-Dartquellen.

### Methode und Koordinaten

Nach Installation der erforderlichen WSL-Buildwerkzeuge konnte Blutter mit
Dart 3.7.2 `libapp.so` analysieren. Die folgenden Blutter-Adressen entsprechen
für die hier betrachteten ausführbaren Adressen auch Datei-Offsets: Das ELF-
`LOAD`-Segment hat Offset und virtuelle Startadresse jeweils `0x480000`.
Ghidra importiert mit Image-Base `0x100000`; die Ghidra-Adresse ist daher
hier die Blutter-Adresse plus `0x100000`. Dies wurde anhand der ELF-Programm-
Header und der REA-Segmentübersicht geprüft.

Ein REA/Ghidra-Lauf mit neun explizit vorgegebenen Funktions-Seeds
(`Seedliste`) schlug fehl: null Funktionen
erstellt, neun fehlgeschlagen,
Evidence-ID `ev_1329ac114b11676abf52edda1d9f41de6c50b4e8d4784bd4d3b328ab19cf4641`.
Daraufhin wurden die `0x3ec` Bytes ab Datei-Offset `0x7afb24` als separater
ARM64-Rohbereich extrahiert und mit Lade-/Einstiegsadresse `0x7afb24`
untersucht. REA erkannte eine Funktion
(`ev_af18cc09c5743e397144a27e82ee8d9e7e6ca6a109ffcdbeb02421cadfe05cfe`).
REA `instructions` bestätigte direkt `bl 0x7aff10` bei `0x7afc44`,
`bl 0x7a7244` bei `0x7afdc4` und `bl 0x7a5cf0` bei `0x7afdd8`
(`ev_98456ce0460cc898290789269249b533ceab3659ca73f07b126409d8f007f6ed`).
Der Funktionsname und die Dart-Zielnamen stammen aus Blutter, nicht aus
REA. Der isolierte Ausschnitt enthält keine externen Ziel-Funktionskörper;
Ghidras erfasster Funktionskörper ist zudem nicht zusammenhängend. Diese
Gegenprüfung beweist deshalb weder vollständigen Call Graph noch die
Interpretation aller Dart-Objekte.

### Rekonstruierter Öffnungspfad

| Schritt | Fundstelle und Funktion | Aussage / Vertrauen |
|---|---|---|
| UI | simple_unlock_page.dart (lokaler Mitschnitt - nicht im Repo), `_BodyState::_handleUnlock` `0x7fccd0`, Aufruf `0x7fcd9c` | Direkter Aufruf von `lockOpen`; hoch für diese Codekante, nicht für die genaue beim Test sichtbare Oberfläche. |
| Operation | ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo), `lockOpen` `0xb86a00`, `_operationStart` `0x78cae4`, `_dispatchAction` `0x7a5688` | `lockOpen` setzt eine Aktionskennung; ein entsprechender Dispatch-Zweig ruft `_sendOpen`. Verbindender asynchroner Ablauf ist modell- und zustandsabhängig. |
| Batterieanforderung | Dieselbe Datei, `_sendBattery` `0x7b8bc4`; cmd_service.dart (lokaler Mitschnitt - nicht im Repo), `getBatteryBytes` `0x7b8c14` | 15 Bytes: `55 30` und 13 Nullbytes. Dart-Smi-Konstanten sind zu dekodieren. Identisch mit Android-Frames 8089, 10493 und 10965; hoch für diese Beobachtungen. |
| Empfang | `BleLockOperateFaceImpl::_setListenData` und dessen List-Closure `0x79c890`, Zweig `0x79d664` in ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo) | Für die beobachtete vierbyteige Antwort `55 30 rr bb` wird Byte 2 dem Feld `0x27` und Byte 3 Feld `0x2f` zugewiesen (`0x79d6c4`, `0x79d708`). Andere Längen und Gerätevarianten haben zusätzliche Zweige. |
| Serveranfrage | `_sendOpen` `0x7afb24` in ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo); `getOpenBytes` `0x7aff10` in cmd_service.dart (lokaler Mitschnitt - nicht im Repo) | Felder `0x27` und `0x2f` gelangen als `randomFactor` beziehungsweise `battery` in eine String-Map mit `deviceNumber`, `deviceName` und optional `randomFactorData`. `HttpUtils::postRequest` ruft `https://clientapi.welock.com.cn/api/Command/UnLock` auf. Hohe statische Evidenz; keine bewiesene kryptografische Bedeutung von `randomFactor`. |
| Antwort und BLE-Write | `RequestBleCmdModel.fromJson` `0x7a767c` in request_ble_cmd_model.dart (lokaler Mitschnitt - nicht im Repo); `_sendOpen`, `_sendCmd` `0x7a5cf0`, `_writeData` `0x7a5e38` in ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo) | Antwortfelder `serverID` und `command`; der `command`-String wird hex-dekodiert und geschrieben. Bestimmte Modell-/Zustandszweige können zuvor `01` oder `00` anhängen. Keine dynamische Korrelation zur Serverantwort oder zu Frame 8094. |
| HTTP-Autorisierung | `HttpUtils::getInstance` `0x5638e0` in http_utils.dart (lokaler Mitschnitt - nicht im Repo) | Ein übergebener Wert wird im Pfad mit dem Header `Authorization` verknüpft. Herkunft, genaues Format, Login und Erneuerung des Werts sind nicht vollständig aufgelöst. |

**Ergänzung zur HTTP-Konfiguration:** `HttpUtils::HttpUtils._` erstellt bei
`0x56498c` eine Dio-Optionsinstanz mit Content-Type
`application/x-www-form-urlencoded`; `HttpUtils::postRequest` übergibt die
Optionsinstanz in seinen `post`-Zweigen bei `0x54f348` und `0x54f3f8`.
Dies ist statische Evidenz für die beabsichtigte Codierung, keine
Aufzeichnung einer tatsächlich übermittelten Anfrage; Interceptors und
Serveranforderungen wurden nicht vollständig verifiziert.
`UserServices::login` (`0x54ecb8`) baut unter anderem Felder `account`,
`password`, `timeOffset`, `platform`, `model`, `language`, `Jpushid` und
`isIot`, siehe user_services.dart (lokaler Mitschnitt - nicht im Repo).
`UserInfo::fromJson` (`0x566580`) verarbeitet `access_token` und
`refresh_token`, siehe user_info.dart (lokaler Mitschnitt - nicht im Repo).
Dies beweist noch nicht, dass oder wie das Access-Token bei Unlock als
Authorization-Wert formatiert wird. Es wurden weder Anmeldedaten ausgelesen
noch Netzwerkanfragen an den Anbieter ausgeführt.

Der Parser [welock_protocol.py](../tools/welock_protocol.py) unterstützt bewusst
nur die beobachtete vierbyteige Batterieantwort. Er wurde mit synthetischen
Werten und lokal gegen drei Android-HCI-Sequenzen sowie die bereits vorhandene
Windows-Notification geprüft. Die Batterieeinheit ist nicht nachgewiesen.
Ein weiterer lokaler Vergleich fand unter 20 streng nach Handle, Paketformat
und zeitlicher Frame-Nachbarschaft ausgewählten Folgen 19 verschiedene
`randomFactor`-Werte; für den einen wiederholten Faktor war der beobachtete
Folge-Write identisch. Dies beweist weder einen deterministischen Algorithmus
noch, dass der Faktor allein den Befehl bestimmt. Es ist eine engere Auswahl
als der frühere Vergleich in der [HCI-Analyse](WELOCK-HCI-ANALYSE.md).
Der PC hat weiterhin **keinen** Unlock-Folge-Write gesendet. Eine
funktionierende unabhängige Entriegelung ist nicht nachgewiesen;
insbesondere fehlen gültige Befehlserzeugung, Authentifizierung,
Erfolgsprüfung und eine mechanisch bestätigte Wiederholung. Vor jedem
Unlock-Versuch sind laut Nutzer mehr als 30 Sekunden Pause einzuhalten.

Der direkte `btatt.value`-Vergleich lieferte für den Versuch einen leeren
Wert und war deshalb unbrauchbar; der Vergleich erfolgte anschließend anhand
der Btsnoop-Rohrecords, ohne Nutzwerte offenzulegen. Eine lokale Abfrage der
jüngsten Android-Logs lieferte keine Treffer für die API-Adresse,
`randomFactor` oder FlutterBluePlugin. Diese Negativbefunde schließen spätere
Laufzeitbeobachtung nicht aus.

## Geltungsbereich und Ergebnis

Untersucht wurde ausschließlich
`libapp.so`, ARM64, 12.190.624 Bytes,
SHA-256 `32f26edb675bd0c7e70d5cdd4d5f4513d97a67e92cf1b26b471cf62e9bf3a106`.
Die [README](reverse-engineering.md) und der frühere
[Analysebericht](BLE-ANALYSE.md) dienten als Kontext, nicht als weitere
Untersuchungsziele. Es wurde kein Gerät angesprochen und kein Mitschnitt
angefertigt.

**Ein Unlock-Kommandoflow, eine konkrete Payload und ein Authentifizierungs-
verfahren sind weiterhin nicht nachgewiesen.** Nach der statischen Analyse
wurde mit Zustimmung ein HCI-Mitschnitt untersucht. Die darin beobachteten
Service-, Write- und Notify-UUIDs sind separat in der
[HCI-Analyse](WELOCK-HCI-ANALYSE.md) dokumentiert; die Kandidatenbewertung
unten bezieht sich ausschließlich auf die AOT-Evidenz. Die hier gefundenen
Zeichenfolgen sind Beobachtungen in den Daten des Dart-Snapshots, keine
rekonstruierten ausführbaren Funktionen. Namen, räumliche Nähe und
gemeinsame Namensbestandteile allein beweisen weder Klassenzugehörigkeit noch
Aufrufe oder Datenfluss.

Vertrauensgrade in diesem Bericht:

* **Hoch:** Die konkreten Bytes und ihr Datei-Offset sind nachgewiesen.
  Dies gilt nicht automatisch für eine semantische Interpretation.
* **Niedrig:** Suchkandidat aufgrund seines Namens; Zugehörigkeit und Verhalten
  sind nicht nachgewiesen.
* **Offen:** Auch eine belastbare Zuordnung als Kandidat ist nicht möglich.

## REA, Analysepfad und Grenzen

1. `rea inspect-native-exports` bestätigte ARM64-ELF und fünf sichtbare
   Dart-Snapshot-Exporte, darunter Daten und Instruktionen. Das
   Exportverzeichnis erfasst keine versteckten oder lokalen Symbole und sagt
   nichts über deren Nichtexistenz aus.
2. `rea inspect-dart-aot` akzeptiert laut CLI nur einen APK-Container. Der
   direkte Aufruf mit `libapp.so` schlug mit `ZIP archive is malformed` fehl.
   Daraufhin wurde ein temporärer ZIP/APK-Container mit **nur dieser einen
   Datei** unter dem erwarteten ABI-Eintrag erstellt. REA bestätigte darin den
   oben genannten SHA-256 der Bibliothek. Der künstliche Container ist kein
   Original-APK und seine Prüfsumme ist für das Ziel irrelevant.
3. REA `inspect-dart-aot`, Evidence-ID
   `ev_bbfb3f53671cb67689f6583037b8f0fdd0bc57e5af10b1acf3e90d6b8095915e`,
   meldete den Snapshot-Hash `d91c0e6f35f0eb2e44124e8f42aa44a7`.
   Der Dart-Isolate-Datenbereich beginnt bei Datei-Offset `0x4280` und ist
   4.673.216 Bytes groß. Die Isolate-Instruktionen beginnen bei `0x496a40`
   und sind 7.343.072 Bytes groß. Der Snapshot-Kind-Wert ist `3`;
   daraus allein wird keine konkrete Dart-SDK-Version abgeleitet.
4. REAs String-Pool-Ausgabe war **teilweise**: mindestens 1.000 Paket-URIs,
   von denen 500 ausgegeben wurden, und mindestens 4.000 identifierartige
   Tokens, von denen 2.000 ausgegeben wurden. REA bezeichnet diese als
   Byte-Pattern-Beobachtungen, nicht als deserialisierte Cluster-Semantik.
   Die hier angegebenen zusätzlichen Offsets wurden anschließend durch
   gezielten lokalen Byte-Scan der einzelnen Bibliothek geprüft.
5. Die frühere Windows-Ghidra-Einschränkung wurde durch REA mit
   Ghidra 12.1.2 in Ubuntu-WSL umgangen. REA `analyze` importierte die
   ARM64-ELF-Datei erfolgreich, Evidence-ID
   `ev_1c747ac4e74e443f27e171d7e61a83d60189de6595319c99a34f25a691fcf0af`.
   Die Ghidra-Standardanalyse meldete **0 erkannte Funktionen** und
   63 definierte Strings. Das ist keine Aussage, dass keine Funktionen oder
   weiteren Strings existieren: Die Dart-Snapshot-Daten werden ohne
   SDK-spezifische Analyse nicht automatisch zu Funktionen aufgelöst.
6. REA `xrefs` fragte exemplarisch die Ghidra-Adresse `0x15dc84` ab,
   entsprechend Datei-Offset `0x5dc84` beim geladenen Image-Base
   `0x100000`, also dem ersten Byte von `_sendCmdUint8List@1259428493`.
   Ergebnis: keine von Ghidra registrierten exakten Referenzen auf diese
   Adresse, Evidence-ID
   `ev_be7b2dd6a5c70c9a418189c7d62fee90d583fd726a3dc95a80c130e667a68018`.
   Dies erfasst weder Verweise auf das zugehörige Dart-String-Objekt noch
   indirekte Referenzen über Snapshot-Pools und beweist deshalb nicht, dass
   der Name oder die mögliche Funktion ungenutzt ist.
7. Für die Dart-Funktionen selbst konnte aus diesen REA-Ergebnissen weder ein
   Call Graph noch eine Def-Use-Kette erstellt werden. Ein String-Offset ist
   ausdrücklich **keine Funktionsadresse**. REAs Ausgabe kann weder alle
   Dart-Symbole noch die Nutzung eines Strings vollständig belegen.

## Die fünf angefragten Quellnamen

Jeder der folgenden vollständigen ASCII-Strings kommt an dem genannten
Datei-Offset vor. Die angezeigten Dart-Dateien liegen nicht als Quelltext vor.
Die Funktionen, eingehenden und ausgehenden Referenzen und Aufrufketten
konnten nicht zugeordnet werden.

| Quellname im Snapshot | Datei-Offset | Funktion / Aufrufkette | Vertrauen |
|---|---:|---|---|
| `package:welock_ui/pages/simple_unlock_page.dart` | `0x12d960` | unbekannt / unbekannt | Bytes hoch; UI-Zuordnung niedrig |
| `package:welock_common/service/ble_lock_face_impl.dart` | `0xd8f7d` | unbekannt / unbekannt | Bytes hoch; BLE-Rolle niedrig |
| `package:welock_common/service/lock_service.dart` | `0x91e1c` | unbekannt / unbekannt | Bytes hoch; Rolle niedrig |
| `package:welock_common/service/lock_operation_face.dart` | `0x80cac` | unbekannt / unbekannt | Bytes hoch; Rolle niedrig |
| `package:welock_common/models/request_ble_cmd_model.dart` | `0xb7aed` | unbekannt / unbekannt | Bytes hoch; Modellrolle niedrig |

Eine Suche nach dem Namen ist keine Referenzverfolgung. „Alle Referenzen“
zu diesen Strings konnten mit der bisherigen Snapshot-Analyse nicht
ermittelt werden.

## Zeichenfolgen für Unlock, Kommandos und GATT

In allen folgenden Zeilen ist der Bytefund selbst sicher, die Spalte
„Einordnung“ jedoch nur ein Suchansatz. Für **alle** Zeilen gilt:
ausführbare Funktion unbekannt, Aufrufkette unbekannt, keine Zuordnung zu den
fünf Quellnamen nachgewiesen.

| String | Datei-Offset | Einordnung | Semantisches Vertrauen |
|---|---:|---|---|
| `SimpleUnlockPage` | `0x15d22a` | UI-/Klassenname als Unlock-Einstiegskandidat | niedrig |
| `_handleUnlock@1335509949` | `0x168788` | möglicher Methodenname; Kontext zur physischen Entriegelung unbekannt | niedrig |
| `https://clientapi.welock.com.cn/api/device/LocalUnLock` | `0xa262a` | vorhandene HTTP-URL, keine belegte BLE-Funktion | niedrig |
| `_sendCmdUint8List@1259428493` | `0x5dc84` | möglicher Name für Versand einer Byte-Liste | niedrig |
| `_sendCmd@1259428493` | `0x101b85` | möglicher Name für Kommando-Versand; gleicher Suffix wie vorheriger Fund ist keine belegte Aufrufkante | niedrig |
| `_sendCmd@1250360932` | `0x6efdd` | weiterer möglicher Kommando-Sender | niedrig |
| `_sendCmd@1305005210` | `0xe7ac6` | weiterer möglicher Kommando-Sender | niedrig |
| `RequestBleCmdModel` | `0x148e71` | möglicher Modellname; Felder unbekannt | niedrig |
| `RequestBleCmdModel.fromJson` | `0x168b92` | möglicher Deserialisierungsname; keine Feldzuordnung | niedrig |
| `FirstSendCmd` | `0x78597`, `0xd589c` | Name oder Schlüssel; Typ und Bedeutung unbekannt | niedrig |
| `cmd12` | `0x43abd` | Zeichenfolge; kein Nachweis eines Opcode-Werts `0x12` oder `12` | offen |
| `writeCharacteristic` | `0xc1130` | Name der MethodChannel-Operation bzw. ein entsprechender String; Aufrufer nicht belegt | niedrig |
| `setNotifyValue` | `0xd19d6` | möglicher Name einer Notify-Operation; Aufrufer und UUID unbekannt | niedrig |
| `setLockStatus` | `0x123daa` | möglicher Status-Setter; keine belegte BLE-Abfrage | niedrig |
| `LockStatus` | `0x11fb74`, `0x1339d0` | Statusnamen; Bedeutung und Herkunft unbekannt | niedrig |

Beobachtete Stichwortvorkommen im gesamten Binary: `unlock` 68, `open` 239,
`lock` 1.097, `authChallenge` 1, `challenge` 2, `nonce` 1, `session` 7,
`token` 107, `password` 279, `passcode` 0, `ble_cmd` 1 und `cmd` 193.
Die Suche ist case-insensitiv und umfasst Teilstrings, daher schließen
Zahlen andere Kontexte, Texte und Überlappungen ein. Null Treffer bedeutet
nicht, dass ein semantisches Konzept fehlt oder nicht anders kodiert ist.
Der URL-Fund belegt nicht, dass die App sie zur lokalen Entriegelung aufruft;
eine mögliche Abhängigkeit von einem Server ist bislang ungeklärt.

## Kryptografie-Kandidaten

Die Offsets zeigen lediglich die jeweils vorhandenen Bytes. Funktion,
Aufrufkette, Schlüssel, Protokollrolle und Nutzung durch BLE sind in jeder
Zeile unbekannt.

| String | Datei-Offset | Beobachtung | Semantisches Vertrauen |
|---|---:|---|---|
| `package:crypto/src/md5.dart` | `0x7502a` | MD5-bezogener Paketname | niedrig |
| `_MD5@578143612` | `0x138940` | identifierartige MD5-Zeichenfolge | niedrig |
| `package:crypto/src/sha256.dart` | `0xc90f4` | SHA-256-bezogener Paketname | niedrig |
| `_Sha256@579160809` | `0x8265a` | identifierartige SHA-256-Zeichenfolge | niedrig |
| `_decodeAes@567421569` | `0xa550a` | AES-bezogener Name; Algorithmus und Anwendungsfall nicht belegt | niedrig |
| `ZipAesHeader` | `0x58a71` | ZIP-bezogener Name; keine belegte Schlosskryptografie | niedrig |
| `authChallenge` | `0x78499` | einzelner Challenge-Name; keine BLE-Zuordnung | offen |
| `nonce` | `0x3cdd0` | einzelner String; kein nachgewiesener Nonce-Datenfluss | offen |

Eine ASCII-Suche fand keinen Treffer für `Cipher`, `SecretKey`, `HMAC`,
`SHA1` oder `passcode`. Diese Negativbefunde gelten nur für diese exakten
ASCII-Teilstrings, nicht für andere Schreibweisen, UTF-16, kompilierte
Algorithmen oder FFI. MD5, SHA-256 und AES sind damit nicht als Teil der
Schlossauthentifizierung bewiesen. Pairing, Challenge-Response,
Schlüsselerzeugung, Session-Aufbau und Verschlüsselung bleiben unbekannt.

## UUID-Kandidaten

Die folgenden vollständigen UUID-Strings liegen in der Datei; ihre Funktion,
Aufrufkette, Service-/Characteristic-Zuordnung und tatsächliche Verwendung
am konkreten Schloss sind nicht rekonstruiert. Vertrauensgrad: **hoch für
den Bytefund, offen für die Protokollrolle**.

| UUID | Datei-Offset |
|---|---:|
| `0000fee0-0000-1000-8000-00805f9b34fb` | `0x9c278` |
| `0000fee1-0000-1000-8000-00805f9b34fb` | `0xe5f84` |
| `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | `0x14c9f3` |
| `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | `0x15700b` |
| `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | `0xe058c` |
| `00000001-0000-1000-8000-00805f9b34fb` | `0x15afe5` |
| `00000002-0000-1000-8000-00805f9b34fb` | `0x16c6fb` |
| `00000003-0000-1000-8000-00805f9b34fb` | `0x13bb62` |
| `00002902-0000-1000-8000-00805f9b34fb` | `0x16701e` |

Die Liste entsteht durch die Suche nach ASCII-UUIDs im vollständigen
36-Zeichen-Format und ist keine vollständige Liste aller kodierten UUIDs.
Der letzte Wert ist die bekannte CCCD-UUID; sein String-Vorkommen allein
belegt nicht, dass oder wo das Schloss damit Notifications aktiviert.

## Rekonstruktionsstatus

| Gewünschtes Ergebnis | Status |
|---|---|
| Kommandoerzeugung und Paketstruktur | unbekannt |
| Opcode-Struktur | unbekannt |
| UI-Ereignis bis BLE-Write | keine AOT-Aufrufkette belegt |
| Statusabfrage | unbekannt |
| Service, Write- und Notify-UUIDs des Schlosses | unbekannt; nur unzugeordnete Strings |
| Authentifizierung, Kryptografie und Session | unbekannt |
| Finale Unlock-Payload | unbekannt; Schlossnummer `DEVICE_NUMBER` reicht als Nachweis nicht aus |

## Priorisierte zusätzliche Informationen

Nach Abschluss der statischen Untersuchung hat der Nutzer die Auswertung
eines Mitschnitts und das lokale Erstellen eines Android-Bugreports
ausdrücklich freigegeben.

### Erster HCI-Versuch

* Das Samsung-Telefon mit Android 16 war über ADB erreichbar. Das direkte
  Lesen der Bluetooth-Logordner war mit den vorhandenen Shell-Rechten nicht
  möglich (`Permission denied`).
* `dumpsys bluetooth_manager` meldete `sSnoopLogSettingAtEnable = EMPTY`.
  Das ist der beim Aktivieren des Bluetooth-Dienstes beobachtete Wert, kein
  sicherer Nachweis für die aktuelle Einstellung in der Benutzeroberfläche.
* Ein mit Zustimmung lokal erstellter Bugreport enthielt keine separate
  Bluetooth-Snoop-Datei, aber einen `BTSNOOP_LOG_SUMMARY`-Abschnitt im
  Dumpstate-Text. Dessen Base64-Daten haben das AOSP-Btsnooz-Format Version 2
  und ließen sich nach dem 9-Byte-Header mit zlib entpacken.
* Der Abschnitt enthielt 6.990 Datensätze: 2.155 HCI-Kommandos (`0x20`)
  und 4.835 HCI-Ereignisse (`0x10`). Es wurden **keine** eingehenden oder
  ausgehenden ACL-Datensätze (`0x11` bzw. `0x21`) gefunden. Daher sind
  daraus weder ATT-Handles noch Characteristic-Writes oder Unlock-Payloads
  rekonstruierbar. Der Umfang dieser Zusammenfassung beweist nicht, dass
  anderswo auf dem Gerät kein vollständiges Log existiert.
* Ein erster Versuch, den Zeitbereich der Zusammenfassung direkt als
  Unix-Millisekunden darzustellen, scheiterte mit `OSError`; daher wird
  hier kein Zeitbereich behauptet. Die Pakettypzählung wurde anschließend
  unabhängig von der fehlgeschlagenen Zeitumrechnung am Bugreport wiederholt.

Für eine weitere Aufzeichnung sollte nach Prüfung der Einstellungen
Bluetooth bewusst durch den Nutzer neu gestartet werden. Anschließend kann
der Wert beim Aktivieren erneut geprüft werden, bevor zwei markierte
Unlock-Versuche wiederholt werden. Ein solcher Neustart trennt bestehende
Bluetooth-Verbindungen.

### Weiteres Vorgehen

1. **HCI-Snoop-Log:** Pro kontrolliertem Versuch den vollständigen
   Verbindungsaufbau und die Service Discovery erfassen, damit ATT-Handles
   UUIDs und Eigenschaften zugeordnet werden können. Danach mindestens zwei
   zeitlich markierte, erfolgreiche Unlock-Aktionen und nach Möglichkeit
   eine getrennte Statusabfrage erfassen; Ereignisse und Schlossreaktionen
   festhalten. Benötigt werden Write-Typ, Handle, Richtung, Payload-Länge,
   Write-Antworten, CCCD und Notifications sowie Verbindungs- und
   Pairing-Ereignisse. Mitschnitte können sensible IDs, Tokens oder
   Zugangsdaten enthalten und sollten lokal bleiben. App-seitige
   Verschlüsselung bleibt auch im HCI-Log verschlüsselt; Android-Version,
   Logging-Konfiguration und Geräteschutz können die Erfassung begrenzen.
2. **Frida-Instrumentierung:** Falls ein Snoop nicht ausreicht und eine
   instrumentierbare, autorisierte Testumgebung vorhanden ist, die auf dem
   jeweiligen Android vorhandenen Überladungen von
   `BluetoothGatt.writeCharacteristic` einschließlich Write-Typ, UUID und
   Wert sowie die Read-/Notify-Callbacks und Service-Discovery-Ereignisse
   beobachten. Alte APIs können den Wert im Characteristic-Objekt, neuere
   direkt als Methodenargument übergeben. Erforderlich sind Zeitstempel und
   Gegenüberstellung mit den kontrollierten Aktionen. Das erfasst die Bytes
   an der Android-Grenze, aber nicht automatisch ihren Dart-Erzeuger.
3. **Native Flutter-AOT-Dekompilierung:** Dart-SDK-Version passend zum
   Snapshot-Hash bestimmen und einen zu dieser Version und Architektur
   passenden Snapshot-Parser einsetzen. Benötigt werden deserialisierte
   Objekt-/String-Pool-Referenzen, Funktions- und Codeobjekte, Adress-zu-
   Datei-Offset-Zuordnung sowie überprüfbare AArch64-Xrefs und Call-/Def-Use-
   Graphen. Ein allgemeiner ELF-Disassembler allein ordnet die oben
   aufgelisteten Strings nicht automatisch Dart-Funktionen zu.
4. **Sonstige Methoden:** Strukturierte GATT-Discovery und Vergleich mehrerer
   Verbindungen, Beobachtung der ggf. erforderlichen Server-Anfragen in
   einer autorisierten Testumgebung und ein Vergleich mit weiteren eigenen
   Geräte-/Firmware-Versionen. Unterschiedliche Ergebnisse dürfen nicht
   ohne weitere Belege als allgemeingültiges WELOCK-Protokoll gelten.

## Kandidatentabelle

| Kandidat | Begründung | Vertrauensgrad |
|---|---|---|
| Unlock-Funktion: `_handleUnlock@1335509949` | passender Namensstring bei `0x168788`; UI-, Schloss- und Call-Zuordnung fehlen | niedrig |
| Lock-Funktion: keine belegte | kein String ist als ausführbare Lock-Funktion zugeordnet | offen |
| Authentifizierung: `authChallenge`, `nonce` | Strings bei `0x78499` und `0x3cdd0`; keine gemeinsame Kette und kein BLE-Bezug | spekulativ |
| Service UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`, `0000fee0-0000-1000-8000-00805f9b34fb` | UUID-Strings bei `0x14c9f3` bzw. `0x9c278`; Service-Rolle nicht nachgewiesen | spekulativ |
| Write Characteristic: `6e400002-b5a3-f393-e0a9-e50e24dcca9e`, `0000fee1-0000-1000-8000-00805f9b34fb` | UUID-Strings bei `0x15700b` bzw. `0xe5f84`; Write-Rolle nicht nachgewiesen | spekulativ |
| Notify Characteristic: `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | UUID-String bei `0xe058c`; Notify-Rolle nicht nachgewiesen | spekulativ |
