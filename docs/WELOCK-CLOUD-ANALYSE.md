# WELOCK: Cloud-Anfrage, Speicherung und Laufzeitprüfung

Stand: 8. November 2026. Ziel ist ein unabhängiger Unlock; der hier
beschriebene Hook ist ein Entwurf, kein bereits erfolgreich ausgeführter
Mitschnitt. Statische Angaben beziehen sich auf App 4.5.8 und das analysierte
ARM64-`libapp.so`; die mit Blutter erzeugten Dart-Dateien sind annotiertes
Assembly, kein Originalquelltext. Für die genannten ausführbaren Bereiche
entsprechen die Adressen zugleich Datei-Offsets. Ergänzende Belege und Grenzen:
[Flutter-AOT-Analyse](FLUTTER-AOT-ANALYSE.md).

## Beobachtung und Schlussfolgerung

Der Nutzer berichtet, dass die App ohne WLAN und mobile Daten nach
„Connect success“ mit „Request network failed“ abbricht und das Schloss nicht
entriegelt. Dies ist ein Hinweis auf eine Abhängigkeit des getesteten
App-Ablaufs von einer Netzwerkanfrage, aber kein Beweis, welche Antwortwerte
oder kryptografischen Operationen die Schloss-Firmware voraussetzt. Der
frühere markierte Versuch und seine Grenzen stehen in der
[HCI-Analyse](WELOCK-HCI-ANALYSE.md#kontrollierter-offline-versuch-vom-8-november-2026).

## Rekonstruierter Request und Antwortpfad

| Evidenzstelle | Statischer Befund | Grenze |
|---|---|---|
| ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo), `BleLockOperateFaceImpl::_sendOpen` `0x7afb24`, Aufruf `0x7afc44` | Übergibt Schlossdaten und zuvor zugeordnete BLE-Antwortfelder an `CommandService::getOpenBytes`. | Keine Laufzeitkorrelation mit einer HTTP-Antwort. |
| cmd_service.dart (lokaler Mitschnitt - nicht im Repo), `CommandService::getOpenBytes` `0x7aff10`, Aufruf `0x7b00ac` | Baut eine Map mit `deviceNumber`, `deviceName`, `randomFactor`, `battery` und bei nicht-null optional `randomFactorData`; übergibt sie an `HttpUtils::postRequest` für `https://clientapi.welock.com.cn/api/Command/UnLock`. | Tatsächliche Werte und mögliche Interceptor-Änderungen sind nicht erfasst. |
| http_utils.dart (lokaler Mitschnitt - nicht im Repo), `HttpUtils::postRequest` `0x54efe8`, Dio-Aufruf `0x54f348`; `HttpUtils::HttpUtils._` `0x56498c` | Dio-`post`; konfigurierte Content-Type-Angabe `application/x-www-form-urlencoded`. `getInstance` `0x5638e0` verknüpft einen übergebenen Wert mit `Authorization`. | Exakte Wire-Codierung, Header und Herkunft/Format des Authorization-Werts sind nicht dynamisch bewiesen. |
| cmd_service.dart (lokaler Mitschnitt - nicht im Repo), Response-Closure `0x7b010c`, Parseraufruf `0x7b017c`; request_ble_cmd_model.dart (lokaler Mitschnitt - nicht im Repo), `RequestBleCmdModel::fromJson` `0x7a767c` | Für eine passende nicht-null `RequestResult` wird deren Daten-Map als `RequestBleCmdModel` verarbeitet; diese liest `serverID` und `command`. `_sendOpen` dekodiert `command` und schreibt den resultierenden Bytewert, teilweise mit zusätzlichem modell-/zustandsabhängigem Byte. | Äußeres JSON-Schema und konkrete Serverantwort nicht mitgeschnitten. `serverID` oder `command` nicht als Schlüssel, Signatur oder Token klassifizieren. |

Die `55 30 rr bb`-Antwort und die Zuordnung von `rr` und `bb` gelten für das
beobachtete Vierbyteformat. Eine kryptografische Challenge, ein TTL-Wert
oder die Wiederverwendbarkeit eines Befehls sind nicht nachgewiesen.

## Herkunft von `request.value` beim Unlock

Stand 8. November 2026. **Geltungsbereich:** der statisch rekonstruierte
Pfad `BleLockOperateFaceImpl::_sendOpen` der App 4.5.8; andere BLE-Writes
haben andere Quellen. Blutter-Ausgaben sind annotiertes ARM64-Assembly;
die angegebenen Adressen sind für diese Codebereiche zugleich Datei-Offsets.
Die drei zentralen Calls bei `0x7afc44`, `0x7afdc4` und `0x7afdd8` wurden
zuvor mit REA/Ghidra unabhängig als Instruktionen bestätigt, nicht als
vollständiger semantischer Datenfluss.

```text
request.value (ein einzelner BLE-Write)
  <- _sendCmd: vollständige dekodierte Liste oder ein Ausschnitt
     <- hexStr2Bytes(command + optionaler lokaler Suffix)
        <- command: RequestBleCmdModel aus RequestResult-Datenmap
           <- getOpenBytes / POST /api/Command/UnLock
              <- deviceNumber, deviceName      [App-Modell; Herkunft offen]
              <- randomFactor, battery        [BLE-Antwort im 4-Byte-Fall]
              <- randomFactorData             [optional; siehe Parserzweig unten]
              <- Authorization / HTTP-Kontext [Wert und Notwendigkeit offen]
              <- serverseitige Eingaben        [unbekannt]
        <- optional "01" oder "00"            [lokaler Modell-/Zustandszweig]
```

Diese Grafik zeigt tatsächliche **App-Datenflüsse**, keine bewiesene
mathematische Abhängigkeit des vom Server erzeugten `command` von jedem
übergebenen Parameter. Eine frische Netzwerkantwort ist nicht für jede
Ausführung dynamisch nachgewiesen; ein Cache-Treffer ebenfalls nicht. Die
äußere Antwortstruktur und die Werte sind nicht aufgezeichnet.

| Kandidat / Kategorie | Beleg und Klassifikation | Was fehlt |
|---|---|---|
| **Cloud response:** `command` | `CommandService::getOpenBytes` `0x7aff10` übergibt die Map bei `0x7b00ac` an POST; die Response-Closure `0x7b010c` ruft `RequestBleCmdModel.fromJson`, das `command` in `field_b` ablegt. `_sendOpen` dekodiert dieses Feld bei `0x7afdc4` und ruft `_sendCmd` bei `0x7afdd8`. Statische Evidenz hoch. | Keine synchronisierte konkrete Serverantwort und kein Bytevergleich mit `request.value`; `serverID` wird ebenfalls gelesen, eine direkte Byteabhängigkeit davon ist hier nicht belegt. |
| **Local storage / lokaler Zustand:** Gerätefelder, Modell und Suffix | `deviceNumber` und `deviceName` stammen aus dem in `_sendOpen` geladenen Modell. Bei bestimmten Modell-/Zustandszweigen wird `"01"` oder `"00"` ergänzt; andernfalls nicht. Statische Evidenz hoch für den Zweig. | Nicht bewiesen, ob Gerätefelder dauerhaft gespeichert, bei Laufzeit aus Cloud geladen oder anderweitig bezogen werden; der tatsächlich aktive Suffix-Zweig ist unbekannt. |
| **Challenge-response-Kandidat / Schlossantwort:** `randomFactor` und `battery` | Im beobachteten Format `55 30 rr bb` weist `_setListenData` die Bytes den Feldern `0x27`/`0x2f` zu; `getOpenBytes` übergibt sie als Parameter. Hohe Evidenz für den beobachteten Datenfluss. | Eine kryptografische Challenge, Responseberechnung oder Unverzichtbarkeit einzelner Parameter ist nicht belegt. Weitere Antwortformate und `randomFactorData` sind nur statisch teilweise rekonstruiert. |
| **Session token:** Authorization | `HttpUtils::getInstance` setzt einen übergebenen Wert im Header-Kontext; `UserInfo` liest Access-/Refresh-Token. Statische Evidenz für diese Einzelstellen. | Herkunft und Format des konkreten Unlock-Headers sowie seine Notwendigkeit für den Server sind nicht nachgewiesen. Kein Nachweis, dass ein Token Bestandteil der BLE-Nutzlast ist. |
| **Device secret:** Geräteschlüssel/Kommunikationspasswort | Für die aktuelle Payload-Erzeugung weder Ort noch Algorithmus belegt. Historische WELOCK-Arbeiten zeigen ein Kommunikationspasswort eines älteren Systems, nicht die Kompatibilität dieses Schlosses. | Existenz, Besitz, Herkunft und Rolle eines aktuellen schlossspezifischen Geheimnisses sowie serverseitige Verarbeitung unbekannt. |

ble_lock_face_impl.dart (lokaler Mitschnitt - nicht im Repo),
`_sendCmd` `0x7a5cf0`, schreibt bei bis zu 20 dekodierten Bytes die ganze
Liste; bei größeren Listen schreibt es die ersten 20 Bytes und übergibt
den Rest über die Timer-Closure `0x7a7188` erneut an `_sendCmd`. Das
konkrete Timerintervall und der erfolgreiche Ablauf langer Writes sind
nicht dynamisch validiert. `request.value` ist daher nicht generell die
gesamte dekodierte Zeichenkette. Der frühere 15-Byte-Folge-Write ist ein
zeitlich zugeordneter Kandidat, kein dynamischer Beweis für die
Serverantwortzuordnung.

**Minimale Information:** Um für den untersuchten App-Zweig die Bytefolge
nachzubilden, sind ein tatsächlich gültiger `command`-Hexstring, die
zutreffende Suffix-Entscheidung und gegebenenfalls die gültige Aufteilung
erforderlich. Die Frage, welche Eingaben ein gültiges `command` erzeugen,
ist offen; die vom App-Request übermittelten Werte sind Kandidaten, keine
bewiesene minimale Menge. Ein unabhängig erzeugtes lokales `command` könnte
andere Informationen benötigen. Weder ein BLE-Passwort noch ein frischer
Cloud-Token oder eine Challenge-Response-Berechnung sind bereits als
notwendige Bestandteile belegt.

### Ein einziges Experiment mit höchstem Erkenntnisgewinn

**Ziel:** In einer erfolgreichen Sitzung die tatsächliche Herkunft von
`request.value` bestimmen und den statisch angenommenen Bytefluss prüfen.
Voraussetzung ist ein autorisierter und nachweislich funktionierender
Laufzeit-Mitschnitt der Flutter-HTTP-Antwort und des BLE-Werts. Der vorhandene
Frida-Entwurf ist auf dem derzeit nicht debuggable Telefon noch nicht
einsatzfähig; seine TLS-Hooks sind für Flutter nicht bestätigt.

Nach Bereitstellung dieses Zugangs und bei nutzerkontrolliertem WLAN:
Zeitbasen und HCI-Snoop prüfen, nach mehr als 30 Sekunden seit dem letzten
Unlock genau einmal die App auslösen und im selben Lauf Requestparameter,
Response-`command`, lokales Suffix-/Modellverhalten, jedes BLE-Write-Stück
und das vom Eigentümer beobachtete mechanische Ergebnis erfassen. Daten
vertraulich halten; keine Zugangsdaten im Chat. Erfolg ist eine eindeutige
Sitzungszuordnung und bytegenaue Übereinstimmung von dekodiertem,
gegebenenfalls ergänzt und aufgeteiltem `command` mit `request.value`.
Fehlender Zugriff, fehlende Klartextantwort oder fehlende mechanische
Beobachtung machen das Ergebnis unvollständig.

Der erwartete Gewinn ist hoch für den Ursprung der App-Nutzlast; eine
einzelne Korrelation beweist weder, welche Servereingaben erforderlich
sind, noch wie man ein neues gültiges `command` lokal berechnet. Ein
funktionierender Offline-Client bleibt deshalb offen.

## Vertiefung: `randomFactor` bis `command` (8. November 2026)

### Quellen und Parsergrenzen

Im hier verfolgten `BleLockOperateFaceImpl` ist der an `getOpenBytes`
übergebene Faktor das unboxed Integer-Feld `field_27`, siehe
`_sendOpen` bei `0x7afc10` (lokaler Mitschnitt - nicht im Repo).
Der Konstruktor initialisiert es bei `0x5b3920` auf null; `onDestroy` setzt
es bei `0xb895a4` zurück. Die Listener-Closure `_setListenData` `0x79c890`
schreibt empfangene Werte hinein. Gleichnamige Offsets anderer Objekte sind
kein Beweis weiterer Quellen: etwa `modifyBlePwd` `0xb884dc` schreibt auf
das übergebene Modell, nicht auf den BLE-Operationszustand.

Für den am Eigentümerschloss beobachteten Ablauf:

1. `_sendBattery` / `CommandService::getBatteryBytes` erzeugt 15 Bytes:
   `55 30` gefolgt von 13 Nullbytes. Write-Characteristic
   `6e400002-b5a3-f393-e0a9-e50e24dcca9e`.
2. Der Antwortparser verarbeitet im Zweig für Opcode `0x30` die beobachtete
   vierbyteige Notification `55 30 rr bb` auf
   `6e400003-b5a3-f393-e0a9-e50e24dcca9e`: Byteindex 2 wird bei
   `0x79d6c4` zu `field_27` / `randomFactor`, Index 3 bei `0x79d708` zu
   `field_2f` / `battery`. Beide Offsets sind nullbasiert. Die GATT-Zuordnung
   und konkreten Handles der aufgezeichneten Sitzung stehen in der
   [HCI-Analyse](WELOCK-HCI-ANALYSE.md#gatt-im-mitschnitt-beobachtet).
3. Der Parser hat weitere Zweige: Bei Länge 5 und Byte 2 gleich null setzt
   er bei `0x79d798` den Faktor auf Byte 3 und zunächst die Batterie auf
   Byte 4. Bei gesetztem `field_b3` **oder** Länge 19 überschreibt er
   außerdem die Batterie mit Byte 2 und speichert die gesamte empfangene
   Bytefolge als Hexstring in `field_af` (`0x79d8ac`–`0x79d8b4`), später
   optional als `randomFactorData` übergeben. Die Bedeutung von `field_b3`
   und diese Varianten wurden am Eigentümerschloss nicht dynamisch geprüft.
4. Dieselbe Listener-Closure enthält weitere Zuweisungen an `field_27` aus
   Byteindex 3 für andere Opcode-Zweige: `0x79cb50`, `0x79d11c`,
   `0x79d3ac`, `0x79db58` und `0x79e560`. Ein konkreter Einfluss auf den
   markierten Unlock wurde nicht nachgewiesen; welcher zuletzt gültige Wert
   beim Aufruf vorliegt, hängt vom tatsächlich durchlaufenen Ablauf ab.

Dies ist eine gezielte Bestandsaufnahme der Zuweisungen im analysierten
Operationsobjekt, kein Beweis über andere App-Versionen oder jede mögliche
indirekte/native Datenquelle. `randomFactor` ist nicht mit dem getrennten,
lokal erzeugten HTTP-Header `nonce` gleichzusetzen. Eine kryptografische
Challenge-Rolle bleibt unbewiesen.

### HTTP-Request: statische Rekonstruktion

`CommandService::getOpenBytes` (lokaler Mitschnitt - nicht im Repo)
`0x7aff10` erstellt eine `Map<String, String?>`, ruft
`HttpUtils::getInstance` mit dem ersten Argument auf und übergibt die Map
bei `0x7b00ac` an `postRequest`. Der Code nennt explizit:

```text
POST https://clientapi.welock.com.cn/api/Command/UnLock
Konfigurierter Content-Type: application/x-www-form-urlencoded
Map:
  deviceNumber      <- übergebenes Modellfeld field_2b
  deviceName        <- übergebenes Modellfeld field_23
  randomFactor      <- Integer field_27, in String umgewandelt
  battery           <- Integer field_2f, in String umgewandelt
  randomFactorData  <- field_af, nur wenn nicht null
```

Die vom Eigentümer genannte Schlossnummer ist `DEVICE_NUMBER`; dass sie im
konkreten Unlock-Request tatsächlich genau als `deviceNumber` erscheint,
ist nicht dynamisch bestätigt. `deviceName`-Wert und mögliche Abweichungen
zwischen Modellnamen und sichtbarer BLE-Bezeichnung sind ebenfalls offen.
Ein separates MAC-Feld ist in dieser konkreten Map nicht belegt.

`HttpUtils::getInstance` (lokaler Mitschnitt - nicht im Repo)
`0x5638e0` konfiguriert die gemeinsame Options-Header-Map. Im Unlock-Pfad
kommt das erste Argument aus `field_7` des übergebenen Modells und wird im
Zusammenhang mit `Authorization` verarbeitet. Null- und Nicht-null-Zweige
unterscheiden sich; weder der wirkliche Wert noch sein Format, ein
`Bearer`-Präfix, seine Herkunft aus `access_token`, oder die serverseitige
Pflicht sind bewiesen. Weitere statisch gesetzte Header:

| Header | Statisch rekonstruierte Quelle |
|---|---|
| `identifierForVendor`, `isPhysicalDevice`, `deviceModel` | App-/Geräteinformationen; konkrete Werte unbekannt |
| `requestClientTimestamp`, `sign` | Zeitstempel und `StringUtil::sign` aus Zeitstempel und Identifier; exakte Laufzeitwerte und Wire-Format nicht beobachtet |
| `nonce` | Ergebnis von `StringUtil::randomDigits12`; nicht BLE-`randomFactor` |
| `operatingSystem` | `android` |
| `User-Agent` | `APP_CLIENT` |
| `appVersion` | bedingt, wenn Package-Info vorliegt; zwei Package-Info-Felder mit `-` verbunden |

Die Liste ist die hier statisch gefundene Optionskonfiguration, kein
vollständiger beweiskräftiger HTTPS-Mitschnitt: Dio, Interceptors oder der
Transport können Header und Serialisierung beeinflussen.
Die exakte HTTP-Anfrage und die äußere Response-Hülle sind noch unbekannt.

### `command` und lokale Möglichkeit

Die `getOpenBytes`-Response-Closure `0x7b010c` akzeptiert ein nicht null
`RequestResult`, prüft dessen Statusfeld auf null und übergibt seine
Datenmap bei `0x7b017c` an
`RequestBleCmdModel.fromJson` (lokaler Mitschnitt - nicht im Repo).
Diese Funktion liest `command` und `serverID`; nur `command` ist in diesem
Pfad als Payload-Quelle nachgewiesen. Die Erzeugung **innerhalb des
Backends** ist nicht sichtbar: Der Server könnte den Wert berechnen,
nachschlagen oder weitere Zustände verwenden. A) serverseitige Bereitstellung
des Kernwerts: statisch hoch; vollständig serverseitige Erzeugung: offen.
B) lokaler Anteil: optionaler Suffix abhängig von Modell/Zustand. C) lokale
Transformation: Hexdekodierung und bei über 20 Bytes Aufteilung. Eine
Korrelation mit der konkreten HTTP-Antwort steht aus.

Ein lokal betriebener Unlock bleibt **plausibel, aber nicht belegt**. Das
Scheitern der offiziellen App ohne WLAN/mobiles Netz betrifft nur den
getesteten App-Ablauf. Ein unabhängiger Client benötigt mindestens eine
validierte Regel zur Erzeugung für den aktuellen Schlosszustand gültiger
Bytes, einschließlich Protokollformat und Suffix-/Chunkregeln. Für die
Serveremulation sind Funktion, Eingabekodierung und alle tatsächlich
abhängigen Zustände/Geheimnisse erforderlich; welche davon existieren,
ist unbekannt. Für cloudgestützte Erzeugung wären stattdessen eine gültige
autorisierte Sitzung, die korrekten Requestwerte und die akzeptierte
Antwortverarbeitung nötig. Weder ein aufgezeichnetes `command` noch die
Schlossnummer allein beweist wiederverwendbare Offline-Fähigkeit.

**Stärkster Blocker:** Es gibt keinen Klartextvergleich von Request,
Response und BLE-Payload und keinen belegten Backend-Algorithmus. Das
einzige priorisierte Folgeexperiment bleibt die oben beschriebene
korrelierte Online-Sitzung mit funktionierendem autorisiertem
Laufzeit-Mitschnitt; die Durchführung ist derzeit durch den fehlenden
Attach-/Klartextzugang blockiert. Dieses Experiment identifiziert den
App-Bytefluss, rekonstruiert für sich allein aber noch nicht die
Serverfunktion.

## Bewertung der `command`-Erzeugung anhand der Projektdokumentation

### REA-MCP-Prüfung vom 8. November 2026

Nach erneuter Sichtung der Projektberichte wurde der lokal vorhandene
`rea-agents`-MCP-Server 6.8.0 über stdio gestartet und über MCP
`initialize`, `tools/list` sowie `tools/call` verwendet. Das read-only
Werkzeug `inspect_adb_package` meldete für die installierte WELOCK-App
Version `4.5.8`, VersionCode `9988`, Evidence-ID
`ev_93937b96eb68b8cd43d3b8a1ee4e87a7492cee6ae0602a8cb890d04f3f856181`.
Dies bestätigt die Versionsnummer, nicht die Byteidentität der
installierten `libapp.so`. Der MCP-Server war nicht als direkt aufrufbares
Werkzeug in dieser Sitzung registriert; er wurde lokal mit seinem
installierten Node-Paket als MCP-Client angesprochen.

REA bietet unter anderem die Offline-Analyse vorhandener HAR-/Proxy-Captures
und bestehender Packet-Captures an. Ein passender Klartext-Capture und ein
verifizierter Zugriff auf die Flutter-TLS-Daten sind weiterhin nicht
verfügbar; das MCP-Werkzeug entschlüsselt HTTPS nicht von selbst. Auf dem
Gerät waren bei read-only Prüfung kein `tcpdump` und kein `su` im normalen
Shell-Suchpfad sichtbar; dies ist kein Beweis, dass andere
Instrumentierungswege ausgeschlossen sind. Es wurden weder neue Daten
erfasst noch Schlossbefehle gesendet. Der bisherige Blocker und das
nachstehend beschriebene Einzel-Experiment bleiben unverändert.

Stand 8. November 2026: Die vorhandenen projektverfassten Markdown-Berichte
und Regeln wurden für diese Bewertung ausgewertet; die 716 zusätzlichen
Markdown-Dateien mitgelieferter Werkzeuge und Abhängigkeiten wurden
eingelesen und gezielt nach den WELOCK-Command-Begriffen durchsucht. Es wurde
keine erneute APK-Analyse und kein Unlock-Versuch durchgeführt.

| Möglichkeit | Evidenz | Vertrauen / Grenze |
|---|---|---|
| A: Serveralgorithmus erzeugt `command` | Der untersuchte App-Pfad erwartet das Feld aus der `RequestResult`-Datenmap nach `POST /api/Command/UnLock`. | Hoch für Bereitstellung im App-Datenpfad, **offen für die interne Erzeugung**; Servercode oder Klartextantwort fehlen. |
| B: Server liest gespeicherte Berechtigung oder berechnete Werte | Kein direkter Einblick in den Server. Historische Forschung nennt ein Kommunikationspasswort eines älteren Systems. | Offen; die historische Beobachtung belegt keinen Lookup in diesem Backend und keine Kompatibilität. |
| C: Aus lokalem Geheimnis abgeleitet | App-Modell und HTTP-Header fließen in den Request; das historische Passwort ist ein Kandidat für eine andere Version. | Für den Kernwert nicht nachgewiesen; `Authorization` und HTTP-`sign` sind keine nachgewiesenen BLE-Schlüssel. |
| D: Teilweise lokal erzeugt / transformiert | `_sendOpen` kann `01` oder `00` anhängen; Hexdekodierung und Aufteilung erfolgen auf dem Client. | Hoch für statische Zweige; welcher Zweig beim konkreten Schloss ausgeführt wird, ist offen. |

Ein Token oder eine Berechtigung ist im Graphen **nicht** als erwiesene
mathematische Eingabe des Commands einzuzeichnen: Herkunft des tatsächlichen
Authorization-Werts und die Serverlogik sind unklar. `randomFactor` und
`battery` sind Request-Eingaben, ihre Notwendigkeit für den Backendwert ist
nicht belegt. Die bekannte direkte Unlock-URL ist `/api/Command/UnLock`;
als vorgeschalteter Anmeldepfad ist `/api/Account/token/welock` statisch
rekonstruiert, ohne Nachweis eines Login-Requests bei jedem Unlock oder
der Übergabe seines Tokens an Unlock. Der String `/api/device/LocalUnLock`
ist lediglich ein älterer Suchkandidat, kein nachgewiesener Bestandteil
dieses Unlock-Pfads. Eine vollständige Liste tatsächlich ausgeführter
Endpunkte ist noch nicht verfügbar.

Die verfügbaren Belege zu `UserInfo`, Speicher-Cache, SharedPreferences und
der historischen 3DES-Arbeit stehen oben beziehungsweise in
[Einordnung öffentlicher Arbeiten](#einordnung-öffentlicher-arbeiten-lokale-lösung).
Keiner davon demonstriert einen aktuellen lokal ableitbaren BLE-Schlüssel,
ein wiederverwendbares Unlock-Cache-Objekt oder einen nachgebildeten
Algorithmus. Das kleinste derzeit **konkret beobachtbare** fehlende
Artefakt ist eine demselben erfolgreichen Lauf zugeordnete Klartext-
Serverantwort mit `command` und Requestkontext, zusammen mit dem BLE-Write.
Zur lokalen Generierung selbst benötigt man darüber hinaus eine
validierte Abbildung und gegebenenfalls ihren Schlüssel/Zustand; ob ein
einzelnes Artefakt hierfür genügt, ist unbekannt.

Der Nutzer meldete inzwischen aktiviertes WLAN-Logging. Am 8. November
wurde das per ADB erreichbare Telefon nur lesend geprüft:
`wifi_verbose_logging_enabled` lieferte `null`, `ro.debuggable` den Wert
`0`, und `run-as cn.sixpower.wlock id` scheiterte mit `package not
debuggable`. Der konkrete Logging-Typ und sein Inhalt sind damit nicht
bestimmt; `null` beweist nicht, dass die vom Nutzer aktivierte Funktion aus
ist. WLAN-Diagnose oder verschlüsselter Paketmitschnitt allein zeigen
HTTPS-Request-/Response-Bodies normalerweise nicht. Ohne verifizierten
Klartextzugang ist das oben definierte einzelne korrelierte Experiment
weiterhin blockiert. Im Vergleich zu einem erneuten Offline-App-Tap hat es
hohen erwarteten Gewinn für den App-Datenfluss und mittleren, nicht
garantierten Gewinn für eine lokale Python-Lösung; zur Erklärung der
Backend-Generierung allein ist der Gewinn unsicher. Keine zusätzlichen
Messungen wurden behauptet.

## Netzwerkfehler: konkrete Code-Stellen

In http_utils.dart (lokaler Mitschnitt - nicht im Repo)
registriert ein `postRequest`-Zweig bei `0x54f398` eine `catchError`-Closure
`0x5635cc`; diese prüft `DioException`, verzweigt nach deren Typ und ruft
`_getMessage` bei `0x563704`. Der andere POST-Zweig muss separat betrachtet
werden. In request_error_code.dart (lokaler Mitschnitt - nicht im Repo)
wird bei der Initialisierung `key_-1000` mit dem lokalisierten Standardtext
belegt; l10n.dart (lokaler Mitschnitt - nicht im Repo),
`S::net_request_default` `0x54c7f0`, liefert „Request network failed“.
Ein Aufruf dieses Getters kann schon bei der Initialisierung erfolgen und
beweist keinen gerade aufgetretenen Fehler. Auch ein Treffer der
`catchError`-Closure allein beweist weder, dass es der Unlock-Request ist,
noch welchen Dio-Fehlertyp oder welches fehlende Antwortfeld er betrifft.

## Speicherbefunde

* user_info.dart (lokaler Mitschnitt - nicht im Repo),
  `UserInfo::fromJson` `0x566580`, liest unter anderem `access_token` und
  `refresh_token`. Das weist Felder im App-Datenmodell nach, nicht deren
  Speicherdauer oder Verwendung für Unlock.
* application_storage.dart (lokaler Mitschnitt - nicht im Repo),
  `saveUserInfo` `0x54ebcc` und `getUserInfo` `0x5692f4`, verwenden
  `put`/`get` auf der statischen Map `_cache`. Dieser Pfad ist im Speicher;
  er belegt für sich keine persistente Speicherung.
* http_cache.dart (lokaler Mitschnitt - nicht im Repo),
  Closure `0x563198`, verwendet UTF-8 und Base64 vor
  `SharedPreferences::setString`; Base64 ist keine Verschlüsselung.
  Welche konkreten Requests oder Tokeninhalte dort landen, ist nicht
  bewiesen. device_identity.dart (lokaler Mitschnitt - nicht im Repo),
  `DeviceIdentity::installId` `0x565e7c`, liest den Preferences-Schlüssel
  `device_install_id`; das ist kein nachgewiesener Schloss-Schlüssel.
* Die Android-`Pluginregistrierung`
  enthält Shared Preferences und SQLite. Pluginregistrierung beweist keine
  Speicherung des Unlock-Tokens in einer SQLite-Datenbank. Secure-Storage-
  Nutzung und ein offline gültiges Cache-Token sind hier nicht nachgewiesen.
  Die privaten App-Daten wurden nicht ausgelesen; `run-as` scheitert, da die
  installierte App nicht debuggable ist. `adb` läuft als `shell`, nicht Root.

## Anmeldung: zusätzlicher statischer Befund

Nach Wiederherstellung von WLAN berichtete der Nutzer, dass die App wieder
entriegelt. Bei einer anschließenden Bestandsprüfung waren WLAN und Bluetooth
aktiv, mobile Daten ausgeschaltet und ein Android-Standardnetz eingetragen.
Es wurde kein neuer markierter Versuch oder API-Aufruf ausgelöst; die
Rückmeldung unterscheidet weiterhin nicht zwischen verschiedenen
Cloud-/lokalen Implementierungsmöglichkeiten.

UserServices::login (lokaler Mitschnitt - nicht im Repo)
`0x54ecb8` erstellt unter anderem `account`, `password`, `timeOffset`,
`platform`, `model`, `language`, `Jpushid` und `isIot`, und übergibt die Map
bei `0x54ef90` an `HttpUtils::postRequest`. Vor der Zuordnung zu `account`
wird `StringUtil::countryMobile` verwendet; das genaue Ergebnis ist vom
Eingabetyp und den Laufzeitargumenten abhängig. `getInstance` wird für den
Login mit `null` aufgerufen; daraus folgt keine Aussage über den späteren
Unlock-Header.

RequestApi::LOGIN (lokaler Mitschnitt - nicht im Repo)
`0x5669c0` bildet den Pfad aus `/Account/token/` und statischem Feld
`0x10fc`; AppInitialized::init (lokaler Mitschnitt - nicht im Repo)
setzt dieses Feld bei `0xb93298` auf `welock`. Im statischen
Initialisierungspfad ergibt sich somit der Login-Kandidat
`https://clientapi.welock.com.cn/api/Account/token/welock`. Das ist keine
beobachtete Anmeldung und garantiert weder ein akzeptiertes Payloadformat
noch unveränderte Serverfunktion. Insbesondere fehlen belastbare Werte und
Semantik für alle relevanten Geräteparameter, das Login-Antwort-Envelope
und das exakte `Authorization`-Format. Eine echte Anmeldung oder ein
Serveraufruf wurde nicht durchgeführt.

Zugangsdaten sollten nicht im Chat, in Git, in Kommandozeilenargumenten oder
ungeschützten Logs übermittelt werden. Wenn später ein getesteter lokaler
Client und ein klarer, autorisierter Versuch vorliegen, kann der Eigentümer
sie selbst per verdeckter lokaler Eingabe bereitstellen. Auch
`sensible-daten` liegt in OneDrive und kann trotz Git-Ignore synchronisiert
werden; besonders sensible Daten gehören in einen ausdrücklich
nichtsynchronisierten, zugriffsbeschränkten Speicher, sofern verfügbar.

## Frida-Hook: Vorbereitung und Grenzen

Der Entwurf `welock_trace.js` protokolliert
Einstiege in die oben genannten AOT-Funktionen und, falls vorhanden,
exportierte `SSL_read`/`SSL_write`-Funktionen von geladenen TLS-Modulen.
TLS-Klartext ist standardmäßig **ausgeschaltet**. Der Hook entschlüsselt
keinen Verkehr selbst und verändert keine Zertifikatsprüfung.

Voraussetzungen und Prüfschritte:

1. Frida-Client und ein zur Android-Architektur und Frida-Version passender,
   autorisierter Attach-Weg sind erforderlich. Auf dem aktuellen Gerät wurde
   kein Frida-Server und kein Root nachgewiesen; `run-as` schlägt fehl.
   Frida-Tools sind lokal derzeit nicht verfügbar. Ohne Root, debuggable
   Prozess oder geeignet eingebundenes Gadget ist ein Attach nicht zugesichert.
   Keine Neuinstallation, Änderung der App oder Löschung von App-Daten ohne
   gesonderte Entscheidung des Nutzers.
2. Der Hook benötigt die bereits laufende App, ARM64 und exakt die analysierte
   Version von `libapp.so` mit SHA-256
   `32f26edb675bd0c7e70d5cdd4d5f4513d97a67e92cf1b26b471cf62e9bf3a106`.
   Vor Einsatz das tatsächlich installierte Binary vergleichen; die acht
   Instruktionsbytes, die der Hook an jedem Einstieg prüft, ersetzen keinen
   vollständigen Hashvergleich. ASLR wird über die geladene Modulbasis
   berücksichtigt. Bei Abweichung **nicht** einsetzen.
3. Nach Bereitstellung des Attach-Wegs im Projektverzeichnis beispielsweise:

   ```powershell
   $appPid = (adb shell pidof cn.sixpower.wlock).Trim()
   if (-not $appPid) { throw 'App-Prozess nicht gefunden' }
   $log = "sensible-daten\android\frida-trace-$(Get-Date -Format yyyyMMdd-HHmmss).log"
   frida -U -p $appPid -l tools\frida\welock_trace.js -o $log
   ```

   Die Startmeldungen `hook_installed`, `hook_error` und
   `tls_hook_summary` kontrollieren. Die App muss `libapp.so` und die
   TLS-Module bereits geladen haben: der Entwurf scannt nur beim Start.
   Die AOT-Hooks sind generische Einstiegspunkte; asynchrone Ereignisse
   dürfen nicht allein anhand der Reihenfolge einem Request zugeordnet
   werden. `network_default_message_lookup` ist kein Fehlerzeitpunkt.
4. Nur wenn tatsächlich passende TLS-Hooks installiert und verwendet werden,
   kann für einen gezielten Versuch im Skript `CAPTURE_TLS_PLAINTEXT` auf
   `true` gesetzt werden. **Es wird dann aller darüber laufende Klartext
   aufgezeichnet**, nicht nur WELOCK-Unlock: Zugangsdaten, Tokens,
   Personen- und Gerätedaten können enthalten sein. Ausschließlich in
   `sensible-daten` speichern, nicht teilen. Git-Ignore verhindert keine
   OneDrive-Synchronisierung. Nach dem Versuch wieder `false` setzen.
   Hex-Daten sind nicht anonymisiert.
5. Ein `tls_call` enthält Richtung über `SSL_read`/`SSL_write`, Pointer zur
   Verbindung, Zeit, Thread, Rückgabewert und bei Aktivierung `data_hex`;
   maximal 65536 Bytes je Aufruf, größere Stücke sind als `truncated`
   markiert. Partielle Writes werden anhand des tatsächlichen Rückgabewerts
   gekürzt. TLS-Aufrufe sind keine HTTP-Nachrichtengrenzen; Streams müssen
   je Verbindung und Richtung zusammengesetzt werden. Pointer können nach
   Verbindungsende wiederverwendet werden. HTTP/2/HPACK, Kompression oder
   Multiplexing erfordern zusätzliche Dekodierung; kein automatischer
   Request-Response-Abgleich ist implementiert.

Bei der statischen Prüfung exportiert das lokale `libflutter.so` keine
`SSL_read`/`SSL_write`-Symbole. Eventuelle System-SSL-Hooks können andere
App-Komponenten erfassen und müssen **nicht** Flutter/Dart-HTTPS treffen.
`tls_hook_summary` mit null Hooks oder ohne anschließende TLS-Ereignisse ist
ein negativer/unklarer Instrumentierungsbefund, kein fehlender Netzwerkverkehr.
Für statisch eingebundenes BoringSSL müssen interne Funktionsadressen und
C-ABI zuerst für den exakten Build unabhängig identifiziert werden;
`FLUTTER_TLS_OFFSETS` bleibt bis dahin `null`. Ein bloßes geratenes Offset
kann den Prozess beschädigen und darf nicht verwendet werden.

Lokale Prüfung: `node --check tools\frida\welock_trace.js` und
`node tests\test_frida_trace.js`. Die Tests prüfen gegen das lokale Binary
die Einstiegsprefixe und simulieren TLS-Reads, partielle Writes, Fehler und
deaktivierten Klartext; sie ersetzen keinen Frida-Lauf auf Android.

## Strategie und nächster Versuch

1. **Cloud-emulierender Client vor Offline-Versprechen:** Nach autorisiertem
   Attach und wiederhergestelltem Netzwerk genau einen markierten App-Unlock
   aufzeichnen, nach mehr als 30 Sekunden Abstand. Ziel: vollständige
   authentifizierte Anfrage, Response-Envelope und zeitgleichen BLE-Write
   lokal korrelieren; mechanischen Erfolg separat beobachten. Erfolgskriterium:
   Response-`command` und tatsächlicher Write sind inklusive optionaler
   Modellbytes reproduzierbar zugeordnet. Nur den offiziellen WELOCK-Server
   verwenden, keine Geheimnisse an andere Systeme übertragen.
2. Danach einen eigenständigen Client zunächst mit regulärer autorisierter
   Anmeldung und frischem Server-Command für die aktuelle BLE-Antwort
   entwickeln; Antwort und Fehler strikt validieren. Erst nach mechanisch
   bestätigtem Test wäre dies ein verifizierter Unlock.
3. Für Cloud-Unabhängigkeit gekennzeichnete Datensätze mehrerer Sitzungen
   vergleichen: Eingaben, Ablaufzeit, Wiederholung gleicher Faktoren,
   Kontext und Ergebnis. Ein Token nur dann cachen, wenn Bindung, Ablauf und
   Wiederverwendung experimentell belegt sind; ein gespeicherter
   Access-Token ersetzt keine nachweislich dynamische Serverantwort.
   Ohne reproduzierbare lokale Erzeugung oder nachgewiesene
   Wiederverwendbarkeit bleibt Backend-Emulation eine Hypothese.

Derzeit stärkster Blocker ist der fehlende autorisierte Frida-Attach-Weg und
eine dynamisch erfasste Serverantwort. Die Schritte oben sind eine
Versuchsplanung, kein bewiesener Offline- oder Python-Unlock.

## Bewertung Hypothese A: lokaler BLE-Unlock

Stand: 8. November 2026. Diese Bewertung verwendet die vorhandenen Berichte,
Mitschnitte und die bereits dokumentierte historische Quelle. Es wurden
keine neuen APK-Details untersucht und kein neuer Unlock-Versuch ausgelöst.

### Definition und Wahrscheinlichkeiten

**A:** Für dieses konkrete Schloss existiert ein autorisierter BLE-Client,
der nach vorhandener Einrichtung mit lokal verfügbaren Berechtigungen
zuverlässig entriegelt, ohne während des Entriegelungsvorgangs Cloud oder
Internet zu benötigen. Eine frühere Online-Einrichtung ist dabei zulässig.
Ob die Einrichtung selbst vollständig offline erfolgen kann, ist eine
zusätzliche, bislang unbeantwortete Frage.

Die folgenden Zahlen sind **subjektive Arbeitsschätzungen**, keine
statistischen Messwerte oder kalibrierten Bayes-Posterioren. Es existieren
keine belastbaren Basishäufigkeiten und Likelihoods für dieses Modell.
Sie helfen lediglich, Untersuchungen zu priorisieren; eine andere plausible
Bewertung der gleichen Evidenz kann stark abweichen. Die Ereignisse sind
bewusst nicht exklusiv und die Prozentsätze dürfen nicht addiert werden:

| Hypothese | Subjektive Einschätzung | Aussage und Unsicherheit |
|---|---:|---|
| **A: Lokaler Unlock zur Laufzeit möglich** | **50 %**, sehr unsicher | Existenz eines solchen Clients nach gegebenenfalls online erfolgter Einrichtung; es existiert kein bestätigter Client. Plausibler weiter Bereich etwa 20–80 %. |
| **B: Die aktuell untersuchte App benötigt für den getesteten Ablauf eine Netzantwort** | **85 %**, subjektiv | Gilt für den untersuchten App-Pfad, nicht für alle denkbaren Clients oder Firmware-Fähigkeiten. Eine mit dem BLE-Write synchronisierte Serverantwort wurde nicht beobachtet. |
| **C: Cloud-Einrichtung liefert langlebige Berechtigung und der Unlock wird lokal erzeugt** | **30 %**, sehr unsicher | Streng definiert als mögliche alternative Implementierung für dieses Schloss, mit belegbarer lokaler Berechtigung und lokaler Berechnung. C ist ein Spezialfall von A; derzeit ist keine der Voraussetzungen bewiesen. |

Die niedrigere C-Schätzung als A lässt andere mögliche lokale Verfahren zu,
etwa eine vollständig lokale Einrichtung. B und A/C können gleichzeitig
zutreffen: Eine herstellerseitige App kann die Cloud für jeden Unlock
verwenden, obwohl ein alternativer lokaler Client existiert.
Falls B stattdessen „jeder denkbare Unlock benötigt zwingend eine nicht lokal
ersetzbare Cloudantwort“ bedeutet, steht B im Gegensatz zu A; diese starke
Behauptung lässt sich derzeit weder belegen noch sinnvoll quantifizieren.

### Befunde und Konkurrenzmodelle

| Befund | Aussagekraft für A / C | Aussagekraft für B | Grenze |
|---|---|---|---|
| Batterieabfrage und Antwort auch im Offline-Versuch; REA bestätigte die zwei ATT-Frames. | Hoch für lokale BLE-Kommunikation; schwach für lokalen Unlock. | Vereinbar: nur die vorbereitende Batterieabfrage fand statt. | Keine BLE-Authentifizierung oder Entriegelung gezeigt; Frame-Zuordnung mit vorläufiger Zeitkorrektur. [HCI-Bericht](WELOCK-HCI-ANALYSE.md#kontrollierter-offline-versuch-vom-8-november-2026). |
| Mechanisch bestätigter App-Versuch mit Batterieantwort und Folge-Write. | Belegt eine lokale BLE-Strecke zum erfolgreichen Vorgang. | Vereinbar mit Cloudantwort vor dem Folge-Write. | Der Write ist nicht isoliert als Unlock bewiesen; keine HTTP-Body-Aufzeichnung. [HCI-Bericht](WELOCK-HCI-ANALYSE.md#kontrollierter-tastendruck-nach-entsperren-des-telefons). |
| Offline meldete die App Netzwerkfehler und entriegelte laut Nutzer nicht; nach WLAN-Aktivierung meldete der Nutzer wieder Erfolg. | Schwache Gegenevidenz für einen alternativen lokalen Client; deutliche Gegenevidenz nur für Offline-Funktion des getesteten App-Ablaufs. | Starke Indizien für Netzabhängigkeit dieses Ablaufs. | Kein isolierter Cloud-Blockadetest, kein vollständiger Netzpfadnachweis zum Testzeitpunkt und keine synchronisierte Antwort. |
| Statischer Pfad `_sendOpen` → `getOpenBytes` → POST → `command` → BLE. | Kein lokaler Algorithmus für diesen Pfad nachgewiesen; schließt alternative Implementierung nicht aus. | Starke statische Stütze für B. | Die tatsächlich verwendete Serverantwort und ihr Verhältnis zum HCI-Write sind nicht dynamisch korreliert. [AOT-Bericht](FLUTTER-AOT-ANALYSE.md#rekonstruierter-öffnungspfad). |
| Vierbyte-Antwort `55 30 rr bb`, `rr` als API-`randomFactor`. | Lokale Eingabe ist nachgewiesen; mögliche Challenge bleibt Hypothese. | Die App übergibt den Wert dem rekonstruierten Serverpfad. | Kryptografische Rolle, weitere Abhängigkeiten und lokale Schlüsselableitung unbekannt. |
| `UserInfo`, In-Memory-Cache und SharedPreferences-Nutzung. | App speichert Daten, aber kein lokal nutzbares Schlossgeheimnis nachgewiesen. | Kein Widerspruch. | Access-/Refresh-Token sind keine belegten BLE-Schlüssel; Cache-Inhalte und Offline-Gültigkeit unbekannt. |
| [Historische CriticalSecurity-Arbeit](https://github.com/CriticalSecurity/welock) über alte WELOCK-Version und Kommunikationspasswort. | Unabhängiges Plausibilitätsindiz für eine ältere Geräte-/Protokollfamilie. | Alte API kann ebenfalls Voraussetzung für die Ersteinrichtung sein. | Übertragbarkeit auf dieses Schloss, aktuelles Passwort und BLE-Kommandogenerierung unbekannt. Das 3DES-Werkzeug entschlüsselt alte API-Daten, implementiert aber keinen Unlock. |

Für A und C fehlen insbesondere ein zum eigenen Schloss gehörendes
Berechtigungsmaterial, die lokale Befehlsgenerierung und eine mechanisch
bestätigte Wiederholung. Für B fehlen konkret die Netzwerktransaktion,
die Response und eine eindeutige dynamische Zuordnung zum BLE-Folge-Write.
Eine kurze Gültigkeitsdauer oder ein Server-Nonce für BLE ist nicht belegt.

### Beweis und Widerlegung

* **A praktisch belegen:** Nach dokumentierter Einrichtung Internet für
  Client und gegebenenfalls zwischengeschaltete Geräte nachweislich
  unterbinden; einen unabhängigen Client einen neuen BLE-Ablauf ausführen
  lassen; die mechanische Entriegelung mindestens zweimal mit mehr als
  30 Sekunden Abstand bestätigen. Erzeugungsinputs und Quellen sowie
  Netzisolation dokumentieren. Eine solche Beobachtung belegt die konkrete
  lokale Funktionsfähigkeit, nicht automatisch das vom Nutzer vorgeschlagene
  interne Schlüsselableitungs- oder Challenge-Modell.
* **Das konkrete Modell Schlüssel → Ableitung → lokale Authentifizierung
  zusätzlich belegen:** Eingaben, Algorithmus, Authentifizierungsnachricht und
  Reaktion des Schlosses im lokalen Client einzeln nachweisen und gegen
  unabhängige Sitzungen prüfen.
* **A stark widerlegen / falsifizieren:** Ein vollständiges,
  versionsspezifisches Schloss-/Protokollmodell müsste zeigen, dass jeder
  funktionierende BLE-Unlock einen frischen, nicht vorab beschaffbaren oder
  lokal reproduzierbaren Wert benötigt, dessen Erzeugung ausschließlich
  online verfügbar ist, und dass kein alternativer autorisierter Offline-Pfad
  existiert. Das ist eine wesentlich stärkere Behauptung als ein einzelner
  fehlgeschlagener Test und praktisch schwer abschließend zu beweisen.
* Eine direkt vor Unlock beobachtete Cloudantwort, ein wechselnder
  Serverwert oder ein Offline-Fehler belegen für sich nur den jeweiligen
  App-Ablauf; sie falsifizieren A nicht. Umgekehrt beweisen BLE-Traffic,
  ein Netzwerkfehler oder ein Passwortfund keinen lokalen Unlock.

### Einzelnes nächstes Experiment: korrelierte erfolgreiche App-Sitzung

**Ziel:** Die stärkste beobachtbare Grenze klären: Gibt der Server für die
konkrete BLE-Antwort das Bytekommando vor, das die App tatsächlich schreibt?

**Voraussetzungen:** WLAN bleibt nutzerkontrolliert aktiv; ein ausdrücklich
autorisierter, auf dem Gerät nachweislich funktionierender lokaler
Instrumentierungszugang muss erst verfügbar gemacht werden. Der vorhandene
Frida-Entwurf ist auf dem nicht debuggable Telefon bislang nicht einsetzbar,
und seine Flutter-TLS-Hooks sind nicht nachgewiesen. HCI-Snoop muss aktiv
sein; sensible Aufzeichnungen bleiben lokal geschützt und können unter
OneDrive trotz Git-Ignore synchronisiert werden.

**Ablauf:** App und Instrumentierung starten und ihren Erfolg ohne Secrets
verifizieren. Telefon-/PC-Uhr und HCI-Zeitbasis erfassen. Nach mehr als
30 Sekunden seit dem letzten Unlock genau einmal in der App entriegeln.
Im selben Lauf Anforderung mit BLE-Antwortwerten, zugehörige
Serverantwort mit `command`, tatsächlichen BLE-Folge-Write, Zeitmarken und
mechanisches Ergebnis erfassen. Keine Zugangsdaten im Chat anfordern.

**Erfolgskriterium:** Der Request ist eindeutig mit derselben BLE-Sitzung
verknüpft; die Antwortbytes stimmen nach belegter Hex-Dekodierung und ggf.
modellabhängigen lokalen Zusätzen mit dem Write überein; der Nutzer
bestätigt die mechanische Wirkung. Ein bloßer HTTPS-Paketmitschnitt genügt
für die verschlüsselten Inhalte nicht. Ausbleibende Hook-Daten oder fehlende
mechanische Beobachtung machen das Experiment nicht auswertbar.

**Erwarteter Einfluss:** Ein Treffer stärkt B und liefert die notwendigen
Daten für eine unabhängige Kommandoanalyse, beweist aber weder noch
widerlegt er A oder C. Ein abweichender, sicher zugeordneter Datenfluss
schwächt die bisherige Interpretation des App-Pfads. Anschließend wäre
als entscheidender A-Test ein validierter unabhängiger Offline-Client nötig.
Da Instrumentierungszugang fehlt, kann der Versuch gegenwärtig nicht
durchgeführt werden; ein erneuter Offline-App-Tap ohne neue Beobachtbarkeit
hat gegenüber dem bereits erfolgten Versuch geringen Informationsgewinn.

## Strategie: lokaler Unlock mit Erkenntnissen aus CriticalSecurity

Ziel ist ein Python-BLE-Client, der **zur Unlock-Zeit** keinen
Netzwerkzugriff benötigt. Eine einmalige autorisierte Online-Einrichtung
wird getrennt von einer vollständig offline durchführbaren Einrichtung
betrachtet. Beide Varianten erfordern einen mechanisch bestätigten Test;
keine ist bislang erreicht.

### Ausgangspunkt und Voraussetzungen

Das [historische Werkzeug](https://github.com/CriticalSecurity/welock/blob/883cdb7aa37e86be12e0c0fe4ea9d907a93c5d19/welock_crypto_tool.py)
entschlüsselt mit einem **separat zu beschaffenden 3DES-Schlüssel** Daten
der alten API und ein historisches Kommunikationspasswort. Es enthält
weder diesen Schlüssel noch eine BLE-Implementierung; die historische
Quelle beschreibt App-Version 2.5.8.0427 und älter, nicht unsere Version
4.5.8. Der 3DES-Schlüssel schützt dort API-Daten und darf nicht als
nachgewiesener BLE-Schlüssel interpretiert werden. Verfügbarkeit der alten
API, die Kompatibilität der Zugangsdaten und des Schlosses sind offen.
Das Skript wurde weder ausgeführt noch ein Legacy-Endpunkt kontaktiert.
Es ist auch nicht ohne Anpassung für aktuelle Python-3-Byteverarbeitung
zuverlässig lauffähig. Sein unverschlüsseltes HTTP und die protokollierte
historische Zugriffsschwäche sind kein geeigneter Weg, aktuelle
Zugangsdaten zu übertragen oder fremde Konten abzufragen.

### Priorisierte Schritte

| Priorität | Aktion | Aufwand / erwarteter Erkenntnisgewinn | Entscheidungskriterium |
|---|---|---|---|
| 1 | Eine **autorisierte Quelle für die eigenen Schlossdaten** finden: verfügbare lokale Konfiguration oder explizit dokumentierter Export bzw. Hersteller-SDK. Nur falls tatsächlich historisches, eigenes verschlüsseltes Material und der passende historische Schlüssel vorliegen, dessen Format lokal anhand des Werkzeugs prüfen. | Mittel / hoch, wenn ein schlossspezifisches Geheimnis oder eine Protokollbeschreibung existiert; aktuell beides nicht nachgewiesen. | Eigentümerzuordnung, Gerät und Datenformat sind eindeutig; ein entschlüsselter String allein ist kein bewiesener BLE-Schlüssel. Kein Legacy-API-Aufruf auf Verdacht. |
| 2 | Bei autorisiertem Instrumentierungszugang einen synchronisierten erfolgreichen Online-App-Vorgang mit Request, Antwort und HCI erfassen; anschließend mehrere unabhängige Sitzungen mit markierten Antworten und Writes vergleichen. | Mittel bis hoch / hoch: testet, ob und wie `command` den Write bestimmt und welche Eingaben variieren. | Dieselbe aktuelle Sitzung korreliert BLE-Batterieantwort, API-Daten, Antwort-`command` und Folge-Write; lokaler Modell-/Zustandszweig ist berücksichtigt. Captures allein beweisen keinen lokalen Algorithmus. |
| 3 | Falls Schritt 1 ein plausibles Geheimnis liefert, vorhandene Captures **offline** gegen eine anhand von Herstellerdokumentation oder Code belegte Befehlshypothese prüfen; Eingaben, Kodierung und Ausgabe separat validieren. | Unbekannt / hoch bei bekannter Protokollfamilie. | Vorab festgelegtes Modell erklärt mehrere markierte Sitzungen und weitere zurückgehaltene Fälle bytegenau; wechselnder `randomFactor` allein belegt weder Challenge noch ausreichende Eingabe. |
| 4 | Nur nach erfolgreicher Offline-Validierung einen Bleak-Client mit bekannter GATT-Zuordnung, Batterieabfrage, berechneter Nutzlast, expliziten Fehlern und Timeouts erstellen. | Mittel / direkter Fortschritt; derzeit durch Schritt 1–3 blockiert. | Eigener Client entriegelt bei getrenntem Internet und mehr als 30 Sekunden Abstand mindestens zweimal mechanisch bestätigt; jeweils neuer vollständiger Ablauf. |

Ein eventuell mit Cloudzugriff vorab erstellter Vorrat an Antworten wäre eine
**separate Cache-Hypothese**, kein bereits nachgewiesenes Verfahren. Trotz
des für das beobachtete Antwortformat einbyteigen `randomFactor` können
Zeit, Schlosszustand, weitere Eingaben oder Einmaligkeit eine Rolle spielen.
Ohne Belege für Gültigkeitsdauer und Wiederverwendung ist weder eine
vollständige Tabelle noch Replay ein belastbarer Offline-Ansatz; es werden
keine gespeicherten oder geratenen Unlock-Writes blind gesendet.

### Konkretes nächstes Experiment

**Ziel:** Die historische Kommunikationspasswort-Hypothese für genau dieses
Schloss prüfen, ohne fremde Konten, alte API-Schwachstellen oder
Schlosskommandos anzusprechen.

1. Feststellen, ob bereits ein eigener, rechtmäßig verfügbarer
   Herstellerexport, ein passendes SDK oder ein gesichertes altes
   App-/Konfigurationsartefakt samt Herkunft und Version vorhanden ist.
   Andernfalls beim Hersteller lokale BLE-Spezifikation und Exportmöglichkeit
   für das eigene Gerät anfragen.
2. Nur wenn verschlüsseltes historisches Konfigurationsmaterial **und** der
   zugehörige Schlüssel tatsächlich verfügbar sind, das Format isoliert
   lokal und ohne Netzwerk untersuchen; Schlüssel niemals raten und die
   Ausgabe nicht in den Chat übernehmen.
3. Erfolg: ein überprüfbar zum eigenen Schloss gehörender Datensatz mit
   dokumentiertem Feldformat und eine unabhängig belegte Zuordnung zum
   passenden BLE-Protokoll. Ein gefundenes Passwort allein zeigt weder,
   dass es aktuell gültig ist, noch wie daraus ein Unlock erzeugt wird.
   Ohne solche Artefakte ist der nächste Weg die in Schritt 2 beschriebene
   autorisierte Laufzeitbeobachtung; der Frida-Attach ist momentan blockiert.

Alle sensiblen Daten vor Dritten schützen. Die Git-Ignore-Regel verhindert
keine OneDrive-Synchronisierung. Keine Zugangsdaten im Chat anfordern.

## Hypothesenvergleich und korrelierter Versuchsstand

Stand 8. November 2026: Die aktuelle **Leithypothese für den analysierten
App-Öffnungspfad ist H2**: `getOpenBytes` fordert einen Server-Befehl an und
`_sendOpen` verarbeitet das Ergebnis. Vertrauen: hoch für den statischen
Pfad, mittel für die tatsächliche Zuordnung einer Netzwerktransaktion zum
markierten erfolgreichen Versuch. H1 (alle für einen lokalen BLE-Client
notwendigen Informationen liegen schon auf dem Telefon) ist nicht belegt
und durch den Offline-App-Misserfolg nicht widerlegt. H3 (Cloud liefert
längerfristige Berechtigungen, BLE berechnet eine Challenge-Antwort lokal)
ist ebenfalls weder belegt noch widerlegt; `randomFactor` allein beweist
keine Challenge-Response-Implementierung. Die Hypothesen sind nicht
vollständig exklusiv: dieselbe App kann einen Cloudpfad benutzen, obwohl
ein alternativer lokaler Client mit anderer Schlüsselverfügbarkeit existiert.

| Beobachtung | Erfolgreicher App-Versuch | Offline-App-Versuch |
|---|---|---|
| Ergebnis | Nutzer bestätigte mechanische Entriegelung | Nutzer meldete Netzwerkfehler und keine Entriegelung |
| Netzwerkbedingungen | Kein vollständiger mit dem Versuch synchronisierter Netzwerk-Mitschnitt dokumentiert | WLAN und mobile Daten laut Settings aus; Flugmodus und vollständige Cloud-Unerreichbarkeit damals nicht geprüft |
| BLE-Abfrage und Antwort | Frames 8089 und 8092, vorläufig +2,277 s und +2,309 s | Frames 18665 und 18667, vorläufig etwa +4,05 s und +4,08 s |
| Folge-Write und Notification | Frames 8094 und 8100, vorläufig +2,531 s und +3,047 s | Bis Mitschnittende kein weiterer ATT-Write-Command und keine weitere Notification beobachtet |
| Netzwerkrequests und Zeiten | **Nicht aufgezeichnet / nicht bestimmbar** | **Nicht aufgezeichnet / nicht bestimmbar** |

Die Frames stammen aus unterschiedlichen Capture-Dateien; alle Zeitabstände
setzen die noch ungeklärte Korrektur um eine Stunde voraus. Die frühere
erfolgreiche Sequenz ist nur zeitlich mit dem Tap korreliert. Ein Scan der
beiden zugehörigen Bugreport-ZIP-Eintragsnamen fand keine `.pcap`-,
`tcpdump`- oder `netlog`-Datei; daraus folgt nicht, dass die Bugreports
keinerlei Netzwerkmetadaten enthalten. Eine vollständige Liste aller
Netzwerkrequests, ihrer Zeitpunkte und ihrer Bodies lässt sich daraus
derzeit nicht ableiten.

Die bei der aktuellen Bestandsprüfung sichtbaren Android-Einstellungen
waren `airplane_mode_on=0`, `wifi_on=0`, `mobile_data=0`,
`bluetooth_on=1`; `dumpsys connectivity` meldete keinen aktiven
Standardnetzweg, zeigte aber weiterhin spezielle Mobilfunk-IMS-Netze.
Das ist eine Momentaufnahme nach den früheren Versuchen, kein Nachweis
des damaligen vollständigen Netzwerkzustands. `airplane_mode=true`,
generell blockiertes Internet und gezielte Cloud-Unerreichbarkeit wurden
nicht jeweils isoliert getestet.

**Datenfluss bis `request.value`:** Der beobachtete Initial-Write wird lokal
von `CommandService::getBatteryBytes` erzeugt. Für den statisch
rekonstruierten Öffnungspfad stammen `command`-Bytes aus der Antwort von
`getOpenBytes`; modell-/zustandsabhängig können lokale Bytes ergänzt werden.
Die Serveranfrage erhält lokale Schlossdaten und im Vierbyteformat die
BLE-Antwortwerte `randomFactor` und `battery`. Die Android-Bridge
`FlutterBluePlugin.java`
setzt in ihrem `writeCharacteristic`-Fall direkt den Protobuf-Wert und ruft
`BluetoothGatt.writeCharacteristic` auf. Dieser Befund beschreibt den
jeweiligen Pfad, nicht sämtliche möglichen App-Writes oder eine dynamisch
bewiesene Serverantwort-BLE-Korrelation.

**Zusätzlicher Suchbefund:** `authChallenge`, `nonce`, `credential`,
`offline`, `session`, `token` und `cloud` wurden in den generierten
WELOCK-AOT-Dateien durchsucht. In
http_utils.dart (lokaler Mitschnitt - nicht im Repo),
`HttpUtils::getInstance`, wird bei `0x563d98` `randomDigits12` aufgerufen
und das Resultat unter `nonce` gesetzt; bei `0x563d48` geht ein
`requestClientTimestamp` zusammen mit `identifierForVendor` in
`StringUtil::sign` und das Ergebnis unter `sign` in dieselbe
Options-Header-Map. string_util.dart (lokaler Mitschnitt - nicht im Repo),
`StringUtil::sign` `0x5646e8`, verwendet statisch String-Umkehr, UTF-8,
Base64 und zweimal MD5. Das ist eine HTTP-Konfiguration, keine bewiesene
BLE-Challenge, kein Schlossgeheimnis und keine dynamische Bestätigung, dass
Header exakt so auf dem Netzwerk ankommen. Kein Treffer dieser Suchbegriffe
in `ble_lock_face_impl.dart` und `cmd_service.dart` beweist kein Fehlen
äquivalenter oder anders benannter Logik.

**Nächster Versuch — online, synchronisiert und mit einer kontrollierten
Aktion:** Nach Wiederherstellung eines vom Nutzer gewählten Internetwegs
einen lokalen, autorisierten Mitschnitt der App-Verbindungen einschließlich
Zeitstempeln und DNS/TLS-Zielmetadaten einrichten und parallel HCI-Snoop
aktiv lassen; für Bodies zusätzlich einen nachgewiesen funktionsfähigen
lokalen Instrumentierungspunkt benötigen. Uhrquellen und Abweichung vorab
separat bestimmen. Nach mindestens 30 Sekunden Abstand exakt einmal
entriegeln und das mechanische Ergebnis beobachten. Erfolgskriterien:
zeitlich eindeutig zugeordnetes Request-/Response-Paar, zugehöriger
`randomFactor`, `command`, tatsächlicher BLE-Folge-Write und Ergebnis.
Ein reiner VPN-/Paketmitschnitt liefert bei HTTPS normalerweise keine
Request-Bodies oder Response-Werte und kann aufgrund von HTTP/2-Multiplexing
auch nicht automatisch jeden Request identifizieren. Ohne TLS-Klartext
bleibt die stärkste Datenflussfrage offen. Derzeit sind weder aktivierter
Internetweg noch der notwendige autorisierte Zugriff zur Klartextbeobachtung
nachgewiesen; keine App-Neuinstallation oder Änderung der Netzkonfiguration
wurde vorgenommen.

Die Bedingungen für eine vollständig lokale Implementierung wären ein
reproduzierbares Kommandoformat und alle dafür notwendigen, rechtmäßig
verfügbaren gerätespezifischen Eingaben sowie wiederholt mechanisch
bestätigte Offline-Tests ohne Netzroute. Ein negativer App-Test beweist keine
generelle Unmöglichkeit; auch ein Cloud-Algorithmus kann prinzipiell lokal
emulierbar sein, wenn alle erforderlichen Eingaben verfügbar sind.

## Einordnung öffentlicher Arbeiten: lokale Lösung

Recherche am 8. November 2026:

**Gezielte frühere Prüfung:** Eine Suche nach einem aktuellen unabhängigen
Python-/BLE-Unlock und nach dem konkreten API-Pfad ergab damals keinen zusätzlich
verifizierten, kompatiblen Client. Die direkt erneut aufgerufene
[hass-welock-README](https://github.com/hzjchina/hass-welock) nennt Cloud,
eine bereits mit dem Schloss gekoppelte WiFi-Box und App-Client-Zugangsdaten
als Voraussetzungen. Sie beschreibt damit eine mögliche Hersteller-/
Cloud-Alternative bei vorhandener Hardware, keinen lokalen BLE-Client.
Ein erneuter direkter Abruf von `WeyeTech/welockbridge` lieferte HTTP 404;
ein Suchergebnis ist kein unabhängiger Nachweis für dessen aktuelle
Zugänglichkeit oder Gerätekompatibilität. PyPI `welock-iot` lieferte beim
direkten Seitenabruf nur eine Ladefehlermeldung; sein tatsächlicher Inhalt
wurde nicht validiert. Eine vergebliche Suche beweist nicht, dass keine
andere Implementierung existiert.

### Experimenteller Python-Cloud-Login

[welock_cloud_login.py](../tools/welock_cloud_login.py) ist ein isolierter
Login-Kandidat, **kein funktionierender Unlock-Client**. Die Unit-Tests
simulieren den HTTP-Endpunkt; weder Anmeldung noch API-Verhalten wurden
gegen ein reales Konto validiert. Der Endpunkt entspricht dem statischen
Android-Pfad `https://clientapi.welock.com.cn/api/Account/token/welock`;
die Desktop-Engine benutzt statisch eine andere Basisdomain
`https://clientapi.we-lock.com/api`. Ob die rekonstruierten
Desktop-Header und Login-Werte an der Android-Domain akzeptiert werden,
ist offen.

Ein erneuter REA/Ghidra-Lauf mit verlängertem Timeout lieferte für
`(*Client).Login` bei `0x140253d80` die vollständige Funktionsanalyse
`ev_5645f2b0c5678b844c683ed62aced6ea1028cdefc3aa7d865b70ea5df3d0b3bb`.
Die generierte Pseudocode-Ansicht bestätigt für die Desktop-Engine die
Login-Feldnamen, das `Jpushid`-Konkatenationsmuster und den Aufruf von
`post`; Go-Aufrufkonventionen und Laufzeitverhalten sind damit nicht
vollständig verifiziert. Die Evidenz liegt im lokalen Sitzungsordner;
die Engine wurde weiterhin nicht ausgeführt.

Lokale Disassemblierung der nachfolgend identifizierten Desktop-Engine:
`(*Client).Login` `0x140253d80` baut Felder `account`, `password`,
`Jpushid`, `platform`, `model`, `language`, `isIot`, `timeOffset`;
`Jpushid` entsteht aus `MD5(account + "welockid-" + identifierForVendor)`.
`(*Client).headers` `0x1402555a0` verwendet Millisekundenzeit, einen
zwölfstelligen Nonce und `Sign`; `Sign` `0x14025cda0` verarbeitet
`reverse(identifierForVendor + timestamp)`, Base64 und zweimal MD5-Hex.
`(*Client).doPost` `0x140255c80` verwendet formkodiertes HTTP-POST.
Dieser Prototyp übernimmt die statischen Desktop-Defaults `ios`, `iPhone`,
`en`, `1`, App-Version `4.5.2` und `Dart/3.7 (dart:io)` als Hypothese.
Die Mock-Antwortstruktur `code` / `data.access_token` stammt aus
[cmd/screenshots/main.go](https://github.com/thibauddavid/welock-desktop/blob/23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077/cmd/screenshots/main.go),
nicht aus einem echten Mitschnitt. Zeit-, Signatur-, Geräte- und
Authorization-Anforderungen sind am echten Server nicht nachgewiesen.

Start bei Bedarf direkt in einem lokalen PowerShell-Terminal:

```powershell
python .\tools\welock_cloud_login.py
```

Der Nutzer bestätigte, dass ein Cloud-Login die anderen Geräte abmeldet.
Das Programm warnt und verlangt `JA`, bevor es ein Passwort abfragt oder
die Cloud kontaktiert. Es verwendet `getpass`, bricht bei ungeschützter
Eingabe ab und speichert oder druckt Passwort und Token nicht. Requests
verwenden HTTPS mit Zertifikatsprüfung, keine Umgebungs-Proxys und keine
Weiterleitungen; Serverantworten werden nicht ausgegeben. Ein Login verändert
trotzdem den Sitzungszustand des Kontos. Keine Zugangsdaten im Chat oder in
Kommandozeilenargumenten eingeben. Nur der Kontoinhaber sollte den Versuch
selbst durchführen.

Der angemeldete Zugriff, die erforderlichen Schlossdaten, der tatsächlich
aktive Suffix-Zweig und ein gültiger BLE-Befehl sind weiter offen. Das
Skript schreibt absichtlich keine BLE-Kommandos. Ein Erfolg der
Mock-Tests ist kein Nachweis eines Cloud-Logins oder Unlocks.
Die gezielten Python-Tests für Cloud-Login, BLE-Probe und Batterieparser
bestanden mit 20 Tests; die Signatur-Testkonstante wurde separat mit
OpenSSL nachgerechnet. Der interaktive Abbruch ohne Anmeldung wurde
ebenfalls geprüft.

### Experimentelle Cloud-Command-Probe

[welock_command_probe.py](../tools/welock_command_probe.py) führt nach
ausdrücklicher Zustimmung und verdeckter lokaler Passworteingabe einen
Login-Kandidaten aus. Mit derselben generierten Gerätekennung und dem
Access-Token liest die Probe am verbundenen Schloss die bereits beobachtete
Batterieantwort ab und übermittelt `deviceNumber`, `deviceName`,
`randomFactor` und `battery` an `/api/Command/UnLock`. Der aus dem Token
direkt gesetzte Authorization-Header sowie die Übernahme der
Desktop-Header für die Android-API sind Hypothesen, nicht dynamisch
bestätigt. Der exakte Name für das App-Modell ist unbekannt; das Skript
rät ihn nicht. `randomFactorData` wird für den untersuchten vierbyteigen
Antwortzweig ausgelassen; andere Antwortlängen werden abgelehnt.

Start im Projektordner in einer lokalen PowerShell:

```powershell
.\sensible-daten\python-venv\Scripts\python.exe -m tools.welock_command_probe
```

Benötigt werden die eigene WELOCK-E-Mail, die BLE-Adresse des Schlosses,
die Schlossnummer und der exakte `deviceName` für die Cloud-Anfrage.
Bei leerer BLE-Adresse sucht das Programm nach Geräten und bietet lokal
eine Auswahl an; ein gefundener Name belegt nicht dessen Zuordnung zum
Cloud-Feld `deviceName`.
Die Nummer `DEVICE_NUMBER` stammt vom Nutzer und wurde später in der
Cloud-Geräteliste als `deviceNumber` bestätigt. Nur die Batterieabfrage wird geschrieben, kein
Unlock-Write. Ein erfolgreiches Login kann andere Sitzungen abmelden.
Ein erhaltenes `command` wird nur als Bytezahl angezeigt, nicht
gespeichert und nur nach separater ausdrücklicher Zustimmung lokal als
Hex ausgegeben; Terminalausgaben können mitgeschnitten werden. Weder
Passwort, Token, Command noch private Kennungen im Chat veröffentlichen.
Eine Ausgabe ist kein Beweis, dass das Command nach dem Disconnect
wiederverwendbar ist, oder dass es das Schloss öffnet.

Am 08.11.2026 meldete der Nutzer einen akzeptierten Login und anschließend
Code 2003 für den Command-Request; ein Command wurde nicht geliefert.
Da der Request erst nach einer vierbyteigen BLE-Antwort abgesetzt wird,
ist auch diese Antwort für den Versuch belegt. Der angegebene Gerätename
war identisch mit der Schlossnummer; ob das der richtige Cloud-Wert ist,
ist offen. Ein Unlock-Write fand nicht statt.

Die App ordnet in
RequestErrorCode (lokaler Mitschnitt - nicht im Repo)
`key_2003` der Meldung `src_request_no_this_device` zu. Die deutsche
Übersetzung (lokaler Mitschnitt - nicht im Repo)
lautet: „Das Gerät ist nicht vorhanden oder befindet sich nicht innerhalb
des Gateways.“ Diese allgemeine Fehlermeldung beweist weder, dass ein Gateway
benötigt wird, noch welches Feld oder welche Berechtigung die Ablehnung
auslöste. Bei einem zweiten Versuch bestätigte `GetDevices` zwar, dass
Gerätenummer und der zuvor eingegebene **übergeordnete** Gerätename
übereinstimmen; der Command-Request wurde erneut mit 2003 abgelehnt.

Als gezielte nächste Möglichkeit fragt die Probe bei leerem Gerätenamen
nach Login `Device/GetDevices` mit `pageSize=40`, `pageNo=1` ab.
LockService::loadDevices (lokaler Mitschnitt - nicht im Repo)
verwendet den Endpunkt und diese Parameter; die Seitennummer 1 ist eine
unbestätigte Annahme. Der App-Parser erwartet eine Liste von Gerätemodellen
mit `deviceName` und `deviceNumber`:
DeviceModel.fromJson (lokaler Mitschnitt - nicht im Repo).
**Korrektur nach dem zweiten Versuch:** Der übergeordnete Anzeigename ist
nicht zwangsläufig der für den Command verwendete Name. `DeviceModel.fromJson`
liest außerdem `ble` als Liste von `BleLockInfo`; deren `fromJson` liest
einen eigenen `deviceName`. In
MainLockDetailPageLiteState::_onClick (lokaler Mitschnitt - nicht im Repo)
`0x7e9910`–`0x7e9950` werden der Name des ausgewählten BLE-Eintrags und
die übergeordnete Gerätenummer in das Operationsobjekt übernommen.
`BleLockOperateFaceImpl::_sendOpen` übergibt diese Felder an
`getOpenBytes`. Die zuvor implementierte Übernahme des übergeordneten
Namens als Command-Name war daher für diesen Pfad falsch. Die konkrete
Geräteliste und die App-Auswahl wurden nicht gleichzeitig zur Laufzeit
verglichen; ein Detail-Refresh oder ein anderer App-Pfad kann abweichen.

Die Probe zeigt nun die erste Seite samt BLE-Namen nur lokal und übernimmt
Nummer und verschachtelten BLE-Namen eines ausdrücklich ausgewählten
Eintrags, ohne dessen Zuordnung zum gewählten BLE-Gerät zu beweisen.
Sie zeigt keine BLE-Passwörter oder sonstigen Cloud-Felder an.
Bei leerer, fehlerhafter oder unerwarteter
Antwort bricht sie ab. Ist das Schloss nicht auf dieser Seite, ist das
kein Nachweis, dass es nicht im Konto vorhanden ist.

41 gezielte Tests für Cloud- und BLE-Bausteine bestanden mit simuliertem
HTTP und BLE. Der neue Umgang mit dem verschachtelten BLE-Eintrag ist
konnte anschließend gegen den echten Server genutzt werden. Ein erfolgreicher Login
kann andere Sitzungen abmelden; die Liste enthält private Kennungen.
Die Fehlermeldung zu einem Cloud-Statuscode kann ohne Response-Body
weitergegeben werden. Ein erfolgreicher Versuch sollte nur Loginstatus,
Command-Bytezahl und Zeitpunkt mitteilen, keine Nutzdaten.

**Historisches Modell nach dem zweiten Versuch:** Login und Geräteliste funktionieren, die Command-Anfrage
wurde zweimal abgelehnt. Ein falscher Modellname ist eine begründete,
noch nicht bestätigte Fehlerhypothese; ebenso bleiben die übrigen
Anfrageparameter offen. Ein Versuch mit lokal ausgewähltem verschachteltem
BLE-Eintrag ist erforderlich; ein Suffix und dessen Wirkung bleiben unbestätigt.

#### Erster Cloud-Command und vorbereiteter Einzelversuch

Nach Nutzerangaben lieferte der Versuch mit dem zum gewählten BLE-Gerät
passenden verschachtelten Namen am 08.11.2026 erstmals einen gültig
hex-dekodierbaren Command von 15 Bytes; die Probe schrieb ihn **nicht**.
Die rohen Bytes werden hier bewusst nicht dokumentiert. Ein lokaler
Vergleich mit Frame 8094 aus dem mechanisch bestätigten App-Ablauf ergab
für diesen älteren Folge-Write ebenfalls 15 alphanumerische ASCII-Bytes
mit demselben Zweibyte-Präfix wie der erhaltene Command. Dies ist ein
Formvergleich zwischen verschiedenen Sitzungen, kein Bytevergleich derselben
Challenge, und belegt weder die Gültigkeit noch die richtige Suffix-Regel.
Die zuvor ausgegebene Command-Instanz wird nicht wiederverwendet.

`welock_unlock_experiment.py` ist ein
separater, ausdrücklich zu bestätigender Versuch: Es werden eine frische
BLE-Antwort und ein neuer
Cloud-Command in derselben Verbindung angefordert. Nur bei der beobachteten
Form (15 Bytes, entsprechendes Präfix und alphanumerischer Inhalt) wird
einmal ohne Suffix geschrieben. Andernfalls wird abgebrochen; es gibt
keine Wiederholung und keinen Fallback. Ein optionaler Suffix im App-Code
bleibt als möglicher Unterschied für andere Modelle oder Zustände offen.
Ein BLE-Write oder eine Notification bedeutet **keinen** mechanischen
Erfolgsnachweis; dazu muss der Nutzer den Knauf selbst prüfen. Nach jedem
Versuch sind mehr als 30 Sekunden Abstand einzuhalten.

**Echter Versuch vom 08.11.2026:** Der Nutzer startete den Einzelversuch
mit eigener Bestätigung, wählte den passenden BLE-Eintrag, meldete einen
abgeschlossenen BLE-Write und eine anschließende, nicht ausgewertete
Notification und bestätigte ausdrücklich die **mechanische Entriegelung**.
Das ist ein erfolgreicher Python-Unlock mit Cloud-Unterstützung in einem
Einzelversuch. Der genaue mechanische Zeitpunkt wurde nicht gemessen; die
Notification allein wurde nicht als Erfolg interpretiert. Ein unabhängiger
HCI-Mitschnitt dieser Python-Sitzung liegt nicht vor.

**Wiederholung vom 08.11.2026:** Der Nutzer bestätigte die erneute
mechanische Entriegelung. Dabei wurden BLE-Adresse und Cloud-BLE-Name
direkt eingegeben; ein abgeschlossener BLE-Write und eine anschließende,
nicht ausgewertete Notification wurden gemeldet. Die Verbindungssuche
nach der eingegebenen Adresse erfolgt weiterhin intern. Nach Nutzerwunsch
wurde die zuvor feste 35-Sekunden-Wartezeit entfernt; der Nutzer muss den
Abstand von mehr als 30 Sekunden zwischen Unlock-Versuchen selbst einhalten.
Ein anschließender dritter Versuch ohne diese feste Wartezeit führte laut
Nutzer ebenfalls zur mechanischen Entriegelung. Die BLE-Verbindung wird beim Verlassen des `async with BleakClient`
nach der Notification beziehungsweise dem Timeout und auch im Fehlerfall
geschlossen; das konfigurierte Notification-Timeout beträgt 15 Sekunden.

Das separate installierbare Paket `welock-client`
übernimmt diesen Ablauf. Seine automatisierten Tests verwenden Simulationen;
das Paket selbst wurde bislang nicht mechanisch am Schloss geprüft.

Das Ergebnis belegt weder Offline-Unlock noch die Serverfunktion,
die Nutzung eines gespeicherten Commands oder Kompatibilität mit anderen
Geräten. Bei einem Fehler während oder nach einem Write ist dessen physische
Wirkung ungewiss; nicht sofort erneut versuchen.

### Desktop-Client und seine opaque Engine

Eine nachfolgende GitHub-Code-Suche nach `randomFactor` und WELOCK fand
[thibauddavid/welock-desktop](https://github.com/thibauddavid/welock-desktop/tree/23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077)
auf Stand `23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077`. Die Projekt-README
beschreibt einen unabhängigen Beta-Client mit direktem Bluetooth-Unlock und
Cloudanmeldung, getestet auf nur wenigen Schlössern. Das ist eine
Hersteller-unabhängige Behauptung des Projekts, keine Bestätigung für unser
Schloss. Seine [BLE-Ablaufsteuerung](https://github.com/thibauddavid/welock-desktop/blob/23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077/internal/app/ble.go)
führt Batterieabfrage, Antwort, Cloud-Mint, BLE-Write und gegebenenfalls
Ergebnisreport aus. Der
[Radio-Code](https://github.com/thibauddavid/welock-desktop/blob/23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077/internal/app/ble_radio.go)
verwendet jedoch Service `FEE0` und eine gemeinsame Characteristic `FEE1`;
hier beobachtet wurden Nordic-UART-Service `6e400001…` und getrennte Write-/
Notify-Characteristics `6e400002…` und `6e400003…`. Daher funktioniert
dieser Radio-Code nicht unverändert mit den hier beobachteten UUIDs.

Die eigentliche Engine ist eine von der Desktop-App gestartete,
vorkompilierte ausführbare Datei mit lokalem JSON-RPC; ihr Quellcode liegt
im Desktop-Repository laut README nicht vor. Die öffentliche Windows-Datei
wurde **nur heruntergeladen und statisch analysiert**, nicht ausgeführt.
Git-Blob `a73a13ba603395eb5a6cc335083ace745d5a1af5` stimmte mit dem
Repository überein; SHA-256:
`1b36cfdb919a39c9aae639b910fcc1837b0ca64afdd2b055ba5cfd811010d759`.
REA `inspect-go-binary`, Evidence
`ev_d88fefff9bb8194fbedecc216d4e4ed6bdbc8b57f14685a3f8b99ce51e7d9bc2`,
fand Go-1.25.5-Buildinformationen und ein als modifiziert markiertes
`welock-core`-Modul. Buildmetadaten sind keine Authentizitäts- oder
Sicherheitsprüfung. Das angegebene Core-Repository und die entsprechende
Go-Proxy-Version lieferten beim direkten Abruf HTTP 404.

Ein lokaler Read-only-Vergleich der Go-Funktionstabelle mit `objdump` ergab:
`welock.(*Client).UnlockCommand` bei VA `0x140256f20` übergibt bei
`0x140257244` den 15-Byte-String `/Command/UnLock` an
`welock.(*Client).mintCommand` bei `0x140256be0`. Letztere ruft bei
`0x140256c18` `(*Client).post`, sucht anschließend das Feld `command`,
dekodiert es mit `encoding/hex.DecodeString` und sucht `serverID`.
Dieser unabhängige statische Befund stützt das **Cloud-Mint-Modell dieses
Clients**, belegt aber weder dessen konkreten HTTPS-Verkehr noch einen
Serveralgorithmus oder eine zwingende Cloudabhängigkeit aller Clients.

**Wichtiger Kompatibilitätsvorbehalt:** Die
[BLE-Quelldatei](https://github.com/thibauddavid/welock-desktop/blob/23523c0b17f5d4e3ff1a2ebb9a2f33b984d53077/internal/app/ble.go)
kommentiert Batterie an Antwort-Index 2. Die statisch inspizierte
`ble.ParseUnlockNonce`-Funktion der Engine lädt bei `0x140280dc0` und
`0x140280dc7` zweimal das Byte an Index 2 in zwei Ergebnis-Slots; deren
exakte Typzuordnung wurde nicht unabhängig rekonstruiert. Im hier
untersuchten App-Pfad wurde die vierbyteige Antwort dagegen als
`55 30 randomFactor battery` ausgewertet. Das ist ein ungelöster Widerspruch
und ein weiterer Grund, weder Engine noch Parser blind zu übernehmen.

Der erste REA-Versuch, die Go-Funktion unter Windows zu dekompilieren,
scheiterte an einem nicht konfigurierten Provider. Unter WSL wurde der installierte Ghidra-Provider und das JDK eingebunden;
der erste Import lief in REAs Start-Timeout von 330 Sekunden. Ein
nachfolgender Lauf mit verlängertem Timeout analysierte den Login wie im
vorhergehenden Abschnitt beschrieben. Die dort nicht behandelten
Go-Funktionstabellen- und Maschinenbefunde für den Unlock stammen aus
lokalem Bytevergleich und `objdump`, nicht aus dieser Login-Dekompilation.
Es wurden keine Zugangsdaten übertragen, keine Backend-Anfragen gestellt
und keine Schlossbefehle gesendet.

**Aktuelles Modell:** Vertrauen hoch, dass der untersuchte App-Pfad und
der neue Desktop-Client Serverantworten zur Befehlserzeugung einsetzen;
niedrig für die Übertragbarkeit des Desktop-Clients auf dieses Schloss und für die
Annahme, dass damit jeder Offline-Algorithmus ausgeschlossen wäre.
Stärkste Unsicherheit bleibt die serverseitige Berechnung bzw. ein
gerätegebundenes Geheimnis. Höchster praktischer nächster Erkenntnisgewinn
ist ein synchronisierter erfolgreicher Online-App-Vorgang mit nachweislich
funktionierender, autorisierter HTTPS-Klartextinstrumentierung und HCI.
Er kann Request, Response und Write korrelieren, aber für sich allein
keinen Offline-Algorithmus beweisen. Dafür ist ein instrumentierbarer
Android-Testzugang erforderlich, der aktuell nicht zur Verfügung steht.

**Ein priorisiertes Experiment:** Ein bereits instrumentierbares,
autorisiertes Android-Gerät mit BLE und installiertem WELOCK-Konto per USB
bereitstellen. Keine Bootloader-Entsperrung oder Zurücksetzung des
bestehenden Telefons voraussetzen. Zunächst den Klartextzugriff auf
Flutter-HTTPS anhand eines harmlosen Testrequests nachweisen; der bisherige
Frida-Entwurf allein ist dafür kein Nachweis. Danach HCI-Snoop und
Klartextaufzeichnung für einen einzelnen App-Unlock zeitlich synchronisieren,
nach mehr als 30 Sekunden Abstand entriegeln und die mechanische Wirkung
prüfen. Erfolg ist eine eindeutig derselben Sitzung zugeordnete BLE-Antwort,
API-Anfrage, Antwort-`command` und nach Transformation bytegleicher Write
mit bestätigter mechanischer Entriegelung. Sensible Mitschnitte lokal außerhalb
von OneDrive halten, Zugangsdaten nicht im Chat veröffentlichen. Die
Auswertung kann einen Cloud-Client ermöglichen, beweist aber keine lokale
Erzeugung und keine Wiederverwendbarkeit.

### Weitere frühere Quellen

* [CriticalSecurity/welock](https://github.com/CriticalSecurity/welock)
  beschreibt die Android-App **2.5.8.0427 und älter** aus 2021 und eine
  ältere HTTP-API. Laut Artikel lieferte diese die Konfiguration mit einem
  verschlüsselten BLE-Kommunikationspasswort; nach dessen Entschlüsselung
  konnte das untersuchte Schloss laut Autoren per BLE geöffnet werden.
  Das ist ein relevantes Indiz dafür, dass mindestens ein älteres System
  nach Beschaffung der Berechtigung lokal arbeiten konnte. Es belegt weder
  das Kommandoformat noch die Kompatibilität unseres konkreten Schlosses.
* Das veröffentlichte
  [welock_crypto_tool.py](https://github.com/CriticalSecurity/welock/blob/883cdb7aa37e86be12e0c0fe4ea9d907a93c5d19/welock_crypto_tool.py)
  verarbeitet die **alte API** mit 3DES-ECB und benötigt einen separat
  extrahierten Schlüssel. Es implementiert keinen BLE-Unlock. Das
  [welock_log_keys.py](https://github.com/CriticalSecurity/welock/blob/883cdb7aa37e86be12e0c0fe4ea9d907a93c5d19/welock_log_keys.py)
  hookt Java-`SecretKeySpec`, nicht generell Dart-/native Kryptografie.
  Daraus folgt nicht, dass die aktuelle App oder das BLE-Protokoll 3DES
  einsetzen. Die alte API wurde nicht kontaktiert.
* Die angegebene Artikelseite `criticalsecurity.nl/welock.html` war wegen
  DNS-Auflösung nicht erreichbar; die oben verlinkte Projekt-README enthält
  den entsprechenden Artikeltext. Ein Ausfall beweist keine dauerhafte
  Nichtexistenz.
* `https://github.com/WeyeTech/welockbridge` und die GitHub-API lieferten bei
  direktem Abruf **404**. Eine Suchindexkopie beschreibt zwar ein BLE-SDK für
  „G-Series“ mit AES-128, Schlüssel und Passwort. Diese Zweitquelle kann
  veraltet sein; Implementierung, Rechte und Identität mit dem WELOCK-Schloss
  sind nicht verifizierbar. Der Name allein belegt keine Kompatibilität,
  AES-Nutzung oder funktionierende Offline-Entriegelung. Ein 404 beweist
  nicht, ob das Repository gelöscht, privat oder anders nicht zugänglich ist.
* Die öffentlich zugängliche
  [hass-welock-Integration](https://github.com/hzjchina/hass-welock)
  dokumentiert Unlock über **WELOCK Cloud und WiFi-Box**, nicht über lokale
  BLE-Befehle. Sie ist gegebenenfalls eine Cloud-Alternative, kein Beleg für
  Cloud-Unabhängigkeit; ein vorhandener WiFi-Box-Besitz ist nicht belegt.

**Bewertung:** Ein rein lokaler BLE-Client ist für dieses Schloss plausibel,
aber mit diesen Quellen noch nicht nachgewiesen oder implementierbar. Es
fehlen ein nachweislich zum Gerät passendes Kommandoformat, rechtmäßig
verfügbare schlossspezifische Zugangsdaten und eine bestätigte Erzeugung für
eine neue BLE-Antwort. Die alte Veröffentlichung und die aktuelle App
betreffen unterschiedliche Versionen und Backendpfade. Der Offline-Fehler
beweist umgekehrt nicht, dass die Schloss-Firmware einen eigenen
Internetkontakt benötigt.

**Höchster nächster Erkenntnisgewinn:** Eine autorisierte Online-App-Aktion
mit lokaler Beobachtung der vollständigen Unlock-Serverantwort und des
zugehörigen BLE-Writes; anschließend kontrolliert die Abhängigkeit von
`randomFactor`, Schlossidentität und Zeit untersuchen. Ohne erfolgreichen
Attach-Weg bleibt das vorerst blockiert. Alternativ könnten vom Hersteller
bereitgestellte lokale SDK-Dokumentation und schlossspezifische Berechtigungen
den Aufwand verkürzen. Keine unbekannten Unlock-Payloads oder alten API-
Schwachstellen ausprobieren; für alle Unlock-Versuche gilt weiterhin ein
Abstand von mehr als 30 Sekunden und mechanische Erfolgskontrolle.

## Cloud-API-Inventar und Zutritts-/Berechtigungsdaten (12. November 2026)

Dieser Abschnitt beantwortet die Frage, ob die WeLock-Cloud-API mehr als den
Unlock-Befehl liefert, insbesondere **wer Zutritt erhalten hat** und **wer
berechtigt/administriert** ist. Ergebnis: **ja**, beides ist über lesende
Endpunkte abrufbar und wurde am eigenen Konto live bestätigt.

### Methode und Geltungsbereich

- Endpunkt-Inventar per Byte-Scan der Strings in
  `arm64-v8a/libapp.so` (App 4.5.8).
  String-Vorkommen beweisen Existenz, nicht Semantik der Felder.
- Die Logcat (`sensible-daten/android-recent-logcat.txt`) und HCI-Mitschnitte
  enthalten **keinen** Klartext der WeLock-HTTPS-Aufrufe (Flutter + TLS); die
  Parameter wurden daher aus dem AOT-Binary abgeleitet und anschließend live
  gegen das eigene Konto verifiziert.
- Verifikation am 12.11.2026 mit Konto des Eigentümers, Schloss `DEVICE_NUMBER`,
  Modell `SECBREBL01`. Nur **lesende** Endpunkte wurden aufgerufen; kein
  Unlock, keine Mutation. Rohdaten enthalten personenbezogene Felder und
  bleiben in `sensible-daten` bzw. werden maskiert ausgegeben.

### Vollständiges Endpunkt-Inventar (aus dem AOT-Binary)

Basis-URL `https://clientapi.welock.com.cn/api`. Gefundene Pfade, gruppiert:

- **Konto:** `/Account/token/welock`, `/Account/refresh`, `/Account/Registered`,
  `/Account/VerificationCodeLogin`, `/Account/MessageLogin`,
  `/Account/GetVerificationCode`, `/Account/Captcha`, `/Account/ChangePassword`,
  `/Account/Modify`, `/Account/AccountBind`, `/Account/LogOff`,
  `/Account/UserPush`, `/Account/marketing`, `/Account/fcmToken`.
- **Befehle (Geräteaktion):** `/Command/UnLock`, `/Command/Activation`,
  `/Command/AddCard`, `/Command/SetCard`, `/Command/AddFingerprint`,
  `/Command/DeleteFingerprint`, `/Command/AddPassword`, `/Command/SetPassword`,
  `/Command/DelPassword`, `/Command/ClearOrdinaryUsers`,
  `/Command/CommunicationPassword`, `/Command/ReadUnlockRecord`,
  `/Command/DeviceSyncTime(V2)`, `/Command/LockDelay`, `/Command/OTA`,
  `/Command/Reset`, `/Command/Report`, `/Command/SyncID`, `/Command/DeleteID`,
  `/Command/SetBleGateway`.
- **Gerät/Verwaltung (überwiegend lesend oder Mutation):**
  `/device/GetUnlockRecord`, `/device/PermissionList`, `/device/GetDeivceInfo`,
  `/device/GetDeivceInfoQr`, `/device/GetLockDevice`, `/Device/GetDevices`,
  `/Device/GetDeivceInfoPackage`, `/Device/GetDeviceGroup`, `/Device/GroupList`,
  `/device/DevicePasswordList(2)`, `/device/TemporaryPasswordList(/Info)`,
  `/device/ApplyForUnlockingList`, `/device/ApplyForUnlockingReview`,
  `/Device/addPermission_26428`, `/Device/delPermission_26428`,
  `/device/TransferPermission`, `/device/Bind_26429`, `/device/DeleteDev_26429`,
  `/device/AlterDevName`, `/device/LocalUnLock`, `/device/UnlockRecordAdd(/Del)`,
  `/device/DevicePassword(/Delete/UserDelete)`, `/device/TemporaryPassword(Del)`.

### Verifizierte lesende Abfragen

Alle Formular-POST, `Authorization`-Header mit `access_token`, Signatur wie beim
Login. Bei fehlendem Pflichtparameter antwortet die API mit `code 1002` und dem
Feldnamen in `msg`.

| Endpunkt | Parameter | Antwort-Datenfelder (Top-Level) |
|---|---|---|
| `/device/GetUnlockRecord` | `deviceNumber`, `pageNo`, `pageSize` | Liste: `id`, `nickName`, `userName`, `userID`, `mobile`, `unlockingTime`, `operatingState`, `unlockResult`, `position`, `deviceName`, `deviceNumber` |
| `/device/PermissionList` | `deviceNumber` (Pagination optional) | Liste: `account`, `nickName`, `lockNumber`, `roleID`, `beginTime`, `endTime`, `num`, `creationTime`, `remark` |
| `/device/GetDeivceInfo` | `deviceNumber` | Objekt: `deviceName`, `deviceNumber`, `model`, `roleLevel`, `unlockNumber`, `ble[]` (`position`, `deviceName`, `deviceMac`, `devicePassword`, `power`, `version{modelName,modelNumber,hardware,firmware}`), `features[]`, `permission[]` (`account`, `nickName`, `roleLevel`, `unlockNumber`, `beginTime`, `endTime`, `addTime`), `lease` |

**„Wer hat Zutritt erhalten":** `GetUnlockRecord` ist ein vollständiges
Zutrittsprotokoll (Zeitpunkt, Nutzer, Methode, Ergebnis, Position). Am eigenen
Schloss waren die cloud-gestützten Entriegelungen vom 8.11.2026 als Methode
`operatingState=6` mit `unlockResult=1` sichtbar, ein Knauf-/Lokaleintrag als
`operatingState=1`. Diese Codezuordnung ist beobachtet, nicht abschließend
bewiesen.

**„Wer ist administriert":** `PermissionList` und `GetDeivceInfo.permission[]`
listen berechtigte Konten mit Rolle (`roleID`/`roleLevel`, beim Eigentümer `1`),
Gültigkeitsfenster und Erstellzeit. Am Testkonto existiert aktuell genau ein
Eintrag (der Eigentümer). Weitere, noch nicht mit Live-Daten gefüllte lesende
Endpunkte für Zutritt/Verwaltung: `DevicePasswordList2`,
`TemporaryPasswordList`, `ApplyForUnlockingList` (im Test leer bzw. `code 2000/
2003`).

### Relevanz für den noch offenen lokalen Offline-Unlock

`GetDeivceInfo.ble[].devicePassword` liefert pro BLE-Modul einen **24 Zeichen**
langen Wert, und die `features`-Liste des Schlosses enthält „蓝牙修改通讯密钥"
(BLE-Kommunikationsschlüssel ändern) sowie „蓝牙近程开锁" (BLE-Nahbereichs-
entriegelung) und „蓝牙同步开锁记录" (Entriegelungsprotokoll per BLE
synchronisieren). Das deckt sich mit dem historischen Hinweis von
CriticalSecurity auf ein **BLE-Kommunikationspasswort** und ist ein konkreter,
bislang nicht ausgewerteter Ansatzpunkt: Falls `devicePassword` der lokale
BLE-Schlüssel ist, könnte ein Offline-Unlock ohne Cloud grundsätzlich möglich
sein. Ungeklärt bleibt, ob der Unlock-`command` rein serverseitig mit einem
Kontoschlüssel oder lokal aus `devicePassword`, `randomFactor` und `battery`
berechnet wird. Der Wert wird in Ausgaben maskiert und gehört zu den
schützenswerten Daten gemäß [Projektregeln](PROJEKT-DOKUMENTATION.md).

### Werkzeug

[tools/welock_cloud_audit.py](../tools/welock_cloud_audit.py) führt die drei
lesenden Abfragen aus, maskiert personenbezogene Felder standardmäßig
(`--show-pii` für Klartext), speichert nichts und sendet keinen Gerätebefehl.
Das Passwort kommt aus `getpass` oder der Umgebungsvariable `WELOCK_PASSWORD`.
Eine strikte Whitelist verhindert den Aufruf mutierender Endpunkte.

## Offline-Forschung: devicePassword und command (12. November 2026)

Dieser Abschnitt verfolgt den Hebel aus dem vorigen Abschnitt: Kann der
Cloud-Unlock-`command` lokal aus dem per Cloud abrufbaren
`devicePassword` (BLE-Kommunikationsschlüssel) und den Session-Parametern
`randomFactor`/`battery` berechnet werden? Ein positiver Nachweis würde einen
Offline-BLE-Unlock ohne Cloud grundsätzlich ermöglichen.

### Schlüsselanalyse (read-only)

`GetDeivceInfo.ble[].devicePassword` liefert pro BLE-Modul **24 Zeichen**. Die
Analyse ([tools/welock_offline_keyinfo.py](../tools/welock_offline_keyinfo.py))
zeigt für beide Module des Testschlosses (`SECBREBL01`): der Wert ist **gültiges
Base64** und dekodiert zu **exakt 16 Byte (128 Bit)**. Das ist konsistent mit
einem **3DES-(2-Key, 16 Byte)** oder **AES-128**-Schlüssel. Entropie ≈ 4,3–4,4
Bit je Base64-Zeichen. Der Schlüssel wird in Ausgaben maskiert und gehört zu den
schützenswerten Daten; Rohwerte nur in `tools/offline-data`.

### Determinismus- und Strukturexperiment (kein BLE-Write)

[tools/welock_offline_experiment.py](../tools/welock_offline_experiment.py) fragte
am 12.11.2026 eine kleine, bestätigte Stichprobe von Cloud-Befehlen für
verschiedene `(randomFactor, battery)` an (acht Anfragen, **kein** Schreiben ans
Schloss) und wertete sie lokal aus:

- **Determinismus: ja.** Dieselbe Eingabe `(rf=7, battery=100)` lieferte bei
  Wiederholung **denselben** Befehl. Der `command` hängt also deterministisch
  von `(Schlüssel, deviceNumber, randomFactor, battery)` ab und enthält
  offenbar **keine** serverseitige Zufalls-Nonce oder Zeitkomponente. Das ist
  die Grundvoraussetzung für eine lokale Reproduktion.
- **Struktur:** Der 15-Byte-Befehl ist `U1` + 13 alphanumerische Zeichen. Über
  die Stichprobe variierten die **Positionen 0–7** (ein zusammenhängender
  8-Byte-Block) sowie **Position 12**; die **Positionen 8–11 blieben konstant**.
  Ein variabler 8-Byte-Block zusammen mit einem 16-Byte-Schlüssel passt zum
  Muster einer **8-Byte-Blockchiffre (DES/3DES)** und deckt sich mit dem
  historischen 3DES-Hinweis von CriticalSecurity.
- **Lokale Hypothesen:** Die getesteten MD5/SHA/HMAC-Varianten reproduzierten
  den Befehl erwartungsgemäß **nicht** (Hash ≠ Blockchiffre). Das widerlegt eine
  lokale Berechnung nicht; es grenzt sie auf eine Blockchiffre mit noch
  unbekanntem Klartext-Layout und unbekannter Byte→Alphanumerisch-Kodierung ein.

### Bewertung und nächster Schritt

| Teilfrage | Stand |
|---|---|
| Schlüssel lokal verfügbar | Ja: 16-Byte-Key aus Cloud (`devicePassword`, Base64). |
| command deterministisch | Ja, für die getesteten Eingaben inkl. Wiederholung. |
| Server-Nonce/Zeit nötig | Nach bisheriger Evidenz nein (Determinismus). |
| Algorithmus/Encoding | Offen: wahrscheinlich 8-Byte-Blockchiffre (DES/3DES/AES), Klartext-Layout und alphanumerische Kodierung der 13 Zeichen unbekannt. |
| Offline-Unlock nachgewiesen | Nein: noch keine lokale Reproduktion eines gültigen Befehls, keine mechanische Verifikation. |

**Höchster nächster Erkenntnisgewinn:** die Byte→Zeichen-Kodierung der 13
Befehlszeichen und das Klartext-Layout bestimmen – entweder durch gezielte
Variation einzelner Eingabebits (differenzielle Analyse der variablen
Positionen) oder durch Reverse Engineering der Dart-AOT-Funktion
`CommandService::getOpenBytes`. Erst nach lokaler Reproduktion eines Befehls,
der zu einer frischen BLE-Challenge passt, folgt – vor Ort und mit mechanischer
Kontrolle – ein einzelner, bestätigter Offline-Unlock-Versuch. Bis dahin werden
keine selbst erzeugten Payloads an das Schloss gesendet.

## Differenzielle Analyse: `command` ist eine Funktion von `randomFactor` allein (12. November 2026)

Nachtrag zur Offline-Forschung. Mit
[welock_offline_experiment.py](../tools/welock_offline_experiment.py)` --differential`
wurden 18 Cloud-Befehle angefragt (**kein BLE-Write**): eine Baseline
(`rf=7, battery=100`), eine Wiederholung und je acht Varianten, in denen genau
**ein** Bit von `randomFactor` bzw. `battery` gekippt wird. So lässt sich die
Wirkung jedes einzelnen Eingabebits auf die 13 Befehlszeichen isolieren.
Rohdaten: `tools/offline-data/experiment-*.json` (git-ignoriert).

### Ergebnisse (verifiziert an diesem Schloss/Schlüssel)

- **`battery` beeinflusst den Befehl NICHT.** Alle acht Battery-Bit-Flips
  änderten **null** Befehlszeichen. Die Batterie geht nicht in die
  Befehlserzeugung ein.
- **`randomFactor` bestimmt den Befehl vollständig.** Da `rf` ein einzelnes
  Byte ist, gibt es nur **256 mögliche Befehle** pro Schloss.
- **Positionen 0–7** sind eine **geschlossene, reversible Funktion von `rf`**:
  jedes Zeichen ist die Base64-Ziffer `(rf * k) >> 2 & 63` (6-Bit-Feldauszug aus
  `rf*k`) mit den Faktoren `k = {1, 8, 3, 4, 8, 5, 8, 3}` für pos0..pos7. An
  allen neun getesteten `rf`-Werten exakt bestätigt.
- **Positionen 8–11** sind konstant (`AAAA`).
- **Position 12** ist deterministisch in `rf`, aber **nicht** multiplikativ –
  konsistent mit einer **Prüfziffer/Checksumme**; als einfache Formel (noch)
  ungelöst.

### Konsequenz: keine Blockchiffre, `devicePassword` ist für den Befehl irrelevant

Die zuvor vermutete 8-Byte-Blockchiffre (DES/3DES/AES) ist **widerlegt**: Die
scheinbare „Avalanche" (ein Eingabebit ändert viele Ausgabezeichen) entsteht
allein durch die Multiplikation `rf*k`, nicht durch kryptografische Diffusion.
Der 16-Byte-`devicePassword` geht **nicht** variabel in den Befehl ein (keine
additive/mischende Wirkung sichtbar); er war für die Befehlserzeugung ein
**Irrweg**. Der Cloud-`command` ist damit eine **Kodierung des
Challenge-Bytes `rf`**, kein verschlüsseltes Token.

### Neue Bewertung

| Teilfrage | Stand |
|---|---|
| Hängt `command` von `battery` ab? | Nein (differenziell widerlegt). |
| Hängt `command` von `devicePassword` ab? | Nicht sichtbar; für die Erzeugung irrelevant. |
| Befehlsraum | Nur 256 Werte (eine Funktion von `rf`). |
| pos0–7 | Näherungsformel `(rf*k)>>2 & 63` (für kleine `rf` exakt, mit vereinzelten Ausnahmen im Vollbereich – s. Korrektur unten). |
| pos8–11 | Konstant `AAAA`. |
| pos12 | Deterministisch in `rf`, vermutlich Prüfziffer; Formel offen. |
| Offline-Befehlserzeugung | **Gelöst** über die **geerntete Tabelle `rf→command`** (maßgeblich; Formel nur als Näherung). Tabelle **vollständig 256/256** (in mehreren `--resume`-Läufen wegen Cloud-Drosselung). |
| Offline-Unlock mechanisch bestätigt | **Nein** – weiterhin offen (siehe unten). |

### Korrektur durch die Voll-Bereichs-Ernte: die Tabelle ist maßgeblich

Die obige multiplikative Formel für pos0–7 wurde an **neun** niedrigen
`rf`-Werten (≤135) exakt bestätigt, **generalisiert aber nicht** über den vollen
Bereich. Die vollständige Ernte aller 256 `rf`-Werte (mit
[welock_offline_oracle.py](../tools/welock_offline_oracle.py), s. u.) zeigt
vereinzelte Abweichungen: z. B. gilt `pos3 = rf & 63` überall **außer** bei
`rf = 62, 63, 126, 127` (dort `pos3 = 1` statt `63`) – ein Fixkomma-/Carry-
Artefakt am oberen Rand jedes 64er-Blocks. Die Formel ist damit eine sehr gute
**Näherung**, aber nicht exakt. **Maßgeblich für die Offline-Erzeugung ist die
geerntete Tabelle `rf→command`**, nicht die Formel.

### Werkzeug und Stand der Ernte

[welock_offline_oracle.py](../tools/welock_offline_oracle.py) erntet die Tabelle
einmalig aus der Cloud (`--harvest`, kein BLE-Write) und erzeugt danach Befehle
rein offline (`--table … --rf N`). Die Cloud **drosselt** nach ~146 schnellen
Anfragen (HTTP 403, Umleitung auf eine Sperrseite); das Werkzeug bricht nach
mehreren Ablehnungen in Folge ab und lässt sich mit `--resume` nach einer
Abkühlpause fortsetzen. So wurde die Tabelle in mehreren Läufen auf **256/256
`rf`-Werte vervollständigt** (git-ignoriert unter
`tools/offline-data/oracle-table-*.json`). Der Offline-Lookup ist verifiziert
(z. B. `rf=7` → `U1XXXXXXXXAAAAX`, `rf=200` → `U1YYYYYYYYAAAAY`, identisch zur
Cloud).

### Höchster nächster Schritt

Die Offline-Tabelle ist **vollständig (256/256)**; die Cloud wird für den Unlock
nicht mehr benötigt. Der eigentliche verbleibende Schritt ist die **mechanische
Verifikation** – **nur vor Ort, mit mechanischer Kontrolle und >30 s Abstand** –
ein
einzelner Versuch, bei dem der lokal erzeugte Befehl zur frischen BLE-Challenge
geschrieben wird. **Verbleibendes Risiko:** eine geräteseitige Replay-/
Zählersperre ist bisher nicht ausgeschlossen und lässt sich ausschließlich durch
diesen physischen Versuch prüfen. Bis dahin werden keine selbst erzeugten
Payloads an das Schloss gesendet.
