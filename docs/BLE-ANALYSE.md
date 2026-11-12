# WELOCK BLE-Analyse – Zwischenstand

## Ergebnis und Geltungsbereich

**Aktualisierung:** In einer späteren, mit Zustimmung durchgeführten
HCI-Aufzeichnung wurden Service-, Write- und Notify-UUIDs für ein
beobachtetes Gerät nachgewiesen. Die Ergebnisse und ihre Grenzen stehen in
der [HCI-Analyse](WELOCK-HCI-ANALYSE.md). Der nachfolgende Text beschreibt
den früheren statischen Zwischenstand.

**Das Unlock-Protokoll ist noch nicht rekonstruiert.** Insbesondere sind die
Schloss-Service- und -Characteristic-UUIDs, die Authentifizierung und die
konkreten Lock-/Unlock-Payloads nicht belegt. Aus der Schlossnummer DEVICE_NUMBER
allein lässt sich hier kein Schlüssel oder Kommando ableiten. Die folgenden
Ergebnisse sind statische Beobachtungen dieser APK, keine Messungen am Schloss.
Die Aufzählungen sind daher keine vollständige Spezifikation.

Untersucht: `welock.apk`, Paket `cn.sixpower.wlock`, Version
4.5.8, VersionCode 9988
(`apktool.yml`). APK-SHA-256:
`7b33794fc795c6c82491e564f43c4ef3f413d87dcf5af6baa17e8a966717a11d`.

Die vorhandene [README](reverse-engineering.md) wurde zuerst gelesen. Anders als dort
nahegelegt liegt ein wesentlicher Teil der App in Flutter-AOT-Code. Dass
Android-Bluetooth-Klassen im Java-Code vorkommen, bedeutet nicht, dass die
schlossspezifische Protokollimplementierung dort vollständig vorliegt.

## Vorgehen, Werkzeuge und Fehlschläge

* REA `6.8.0`, lokal über `npx rea-agents@latest`, wurde für
  `identify-flutter-build`, `inspect-native-exports`,
  `search-android-classes`, `inspect-android-method` und
  `trace-android-references` eingesetzt. Die APK wurde dabei nicht ausgeführt.
* `identify-flutter-build` lieferte für beide ABIs den Dart-Snapshot-Hash
  `d91c0e6f35f0eb2e44124e8f42aa44a7`, aber keine Dart-Version. Das ist
  keine Zuordnung zu einer konkreten Dart-Version.
* Der erste APK-Aufruf mit `--detail summary` scheiterte an einem unbekannten
  CLI-Flag. Der zweite scheiterte am fehlenden JADX-Backend. Das von REA
  verlangte `jadx-headless-mcp 0.7.1` wurde separat heruntergeladen und
  anhand des von REA dokumentierten SHA-256
  `6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75`
  verifiziert. Die mit JADX mitgelieferte JRE scheiterte anschließend,
  weil `jdk.compiler` fehlt. Mit einem lokal bereitgestellten JDK 21
  funktionierte die Android-Analyse.
* REA fand 8026 Top-Level-Android-Klassen; die Suche nach `cn.sixpower`
  lieferte nur `MainActivity` und `R`, nicht den kompilierten Dart-Code.
  `inspect-android-method` dekompilierte
  `org.pcgy.flutter_blue.FlutterBluePlugin.onMethodCall`.
* `trace-android-references` fand für `FlutterBluePlugin.k` einen
  aufrufenden Android-Methodenknoten: `onMethodCall`, mit fünf direkten
  DEX-Invokes. Für `onMethodCall` selbst wurden keine direkten eingehenden
  JADX-Referenzen gefunden. Das widerlegt keinen dynamischen Flutter-Aufruf:
  `MethodChannel.IncomingMethodCallHandler` ruft einen Interface-Handler
  auf, der bei Plugin-Registrierung gesetzt wird. Referenzabdeckung gilt
  nur für die von JADX erkannten Android-Knoten.
* Für `BaseDfuImpl.writeOpCode` meldete REA vier aufrufende Methodenknoten:
  `ButtonlessDfuImpl.performDfu`, `LegacyButtonlessDfuImpl.performDfu`,
  `LegacyDfuImpl.writeOpCode` und `SecureDfuImpl.writeOpCode`.
  Für `BaseCustomDfuImpl.writePacket` wurden `uploadFirmwareImage` und
  der synthetische Zugriff `access$200` gefunden.
* REA-Native-`analyze` auf ARM64 `libapp.so` scheiterte: Windows-Ghidra
  unterstützt dort laut REA-Diagnose keine ARM64-ELF-Targets; Hopper ist
  auf Windows nicht verfügbar, IDA und Kuna waren nicht konfiguriert.
  Deshalb wurden keine REA-Call- oder Def-Use-Graphen des Dart-AOT-Codes
  gewonnen. Eine Kryptografie-Datenflussanalyse des Dart-Codes war unter
  diesen Voraussetzungen ebenfalls nicht möglich.
* Die folgenden AOT-Strings wurden zusätzlich durch einen lokalen
  Byte-Scan extrahiert, **nicht** durch REA semantisch rekonstruiert.
  String-Vorkommen beweisen weder Ausführung noch einen Aufrufzusammenhang.
  Alle angegebenen Offsets sind Datei-Offsets in
  `arm64-v8a/libapp.so`.
* Ein Android-Gerät war per ADB sichtbar. Es wurde kein Schloss angesteuert,
  keine App verändert und kein HCI-Mitschnitt aufgenommen.

## Architektur

Das `Manifest` erklärt Bluetooth-Scan-,
Connect- und Advertise-Berechtigungen sowie `MainActivity` und den Nordic-DFU-
Service. `cn.sixpower.wlock.MainActivity.onCreate` startet die
Flutter-Activity und behandelt die Navigationsleiste
(`MainActivity.java`).
`GeneratedPluginRegistrant.registerWith` registriert sowohl
`FlutterBluePlugin` als auch `FlutterNordicDfuPlugin`
(`GeneratedPluginRegistrant.java`).

REA `inspect-native-exports` beobachtete in der ARM64-`libapp.so` fünf
exportierte Dart-Snapshot-Objekte, darunter Isolate-Daten und -Instruktionen,
aber keine exportierten WELOCK-Methodennamen. Das schließt nicht exportierte
Symbole oder wiederherstellbare Dart-Metadaten nicht aus.

Im Snapshot vorhandene, für die weitere Analyse priorisierte Dart-Quellnamen:

| String | Offset | Belegte Bedeutung |
|---|---:|---|
| `package:welock_ui/pages/simple_unlock_page.dart` | `0x12d960` | UI-bezogener Quellname, nicht als tatsächlicher Unlock-Einstieg nachgewiesen |
| `package:welock_ui/pages/main_lock_detail_page_lite.dart` | `0x1694ac` | Schlossdetail-Quellname; Verhalten unbekannt |
| `package:welock_common/service/ble_lock_face_impl.dart` | `0xd8f7d` | BLE-Schloss-Quellname; Implementierung und Aufrufer unbekannt |
| `package:welock_common/service/lock_service.dart` | `0x91e1c` | Schloss-Service-Quellname |
| `package:welock_common/service/lock_operation_face.dart` | `0x80cac` | Operations-Quellname |
| `package:welock_common/models/request_ble_cmd_model.dart` | `0xb7aed` | Kommando-Modell-Quellname; Struktur unbekannt |
| `package:welock_ui/pages/nordic_dfu_page.dart` | `0x152153` | DFU-UI-Quellname; Verbindung zur Android-Brücke nicht nachgewiesen |

Diese Dart-Dateien sind **nicht** als Quelltext im Projekt vorhanden; die
Tabelle beschreibt im Binary gefundene Namen, keine rekonstruierten Klassen
oder Methoden. Es wurden weitere WELOCK-Quellnamen gefunden; eine vollständige
Inventarisierung aller WELOCK-Klassen ist nicht gelungen.

## BLE-Kommunikationspfade

Sichtbar sind mindestens zwei getrennte Android-Pfade:

1. Allgemeine BLE-Operationen über
   `FlutterBluePlugin.onMethodCall`
   (`FlutterBluePlugin.java`).
   `p` startet `BluetoothLeScanner.startScan`; `onMethodCall` behandelt
   Connect, Disconnect, Service Discovery, Read, Write, Descriptor und
   Notification. `connectGatt` verwendet `BluetoothGattCallback` der
   inneren Klasse `c`. `k` löst primären Service, optionalen sekundären
   Service und Characteristic anhand übergebener UUIDs auf.
2. Firmware-Updates über `FlutterNordicDfuPlugin.onMethodCall` und
   `m`, `DfuServiceInitiator` und Nordic-DFU-Implementierungen
   (`FlutterNordicDfuPlugin.java`).
   Diese enthalten eigene GATT-Schreibpfade. Die Klasse nutzt zusätzlich
   einen älteren `BluetoothAdapter.LeScanCallback`, der nach Gerätenamen
   mit `DFU` sucht.

Der vollständige UI-zu-Funk-Graph ist **nicht** belegt. Der tatsächlich
nachvollzogene gemeinsame Endabschnitt lautet:

```text
Flutter-Seite / UI / Protokollerzeugung: unbekannt
      ... MethodChannel-Nachricht "writeCharacteristic" ...
MethodChannel.IncomingMethodCallHandler.onMessage
  -> MethodCallHandler.onMethodCall [Interface-Dispatch]
  -> FlutterBluePlugin.onMethodCall, case 5
  -> Protos$WriteCharacteristicRequest aus MethodChannel-Bytes
  -> FlutterBluePlugin.m(remoteId) -> BluetoothGatt
  -> FlutterBluePlugin.k(serviceUuid, secondaryServiceUuid, characteristicUuid)
  -> characteristic.setValue(request.value)
  -> characteristic.setWriteType(1 oder 2)
  -> BluetoothGatt.writeCharacteristic(characteristic)
```

Die Registrierung des Handlers erfolgt in `FlutterBluePlugin.n`; der
Interface-Dispatch ist in
`MethodChannel.java`
sichtbar. Dass ein bestimmter UI-Button diesen Pfad nutzt, ist noch nicht
nachgewiesen.

`Protos$WriteCharacteristicRequest` besitzt die Felder `remoteId` (1),
`characteristicUuid` (2), `serviceUuid` (3), `secondaryServiceUuid` (4),
`writeType` (5) und `value` (6)
(`Protos$WriteCharacteristicRequest.java`).
Das Protobuf ist hier das **interne MethodChannel-Transportformat**: Die
Android-Brücke setzt nur `value` als Characteristic-Wert; es ist nicht
nachgewiesen, dass das gesamte Protobuf über BLE gesendet wird. Die Brücke
unterstützt Write With und Without Response; welche Variante das Schloss
für welches Kommando verwendet, ist unbekannt.

Für eingehende Daten wandelt `FlutterBluePlugin.c.onCharacteristicChanged`
die Characteristic in eine `Protos$OnCharacteristicChanged`-Nachricht um und
gibt sie über `j` an Flutter zurück. `onServicesDiscovered` übermittelt
gefundenen Service-Metadaten. `onMethodCall`, case 4, aktiviert lokal
Notification/Indication und schreibt den CCCD; case 6 liest eine
Characteristic. Diese generischen Pfade beweisen keine spezifischen
Eigenschaften der Characteristics des konkreten Schlosses.

## UUIDs

### Direkte Java-/DFU-Belege

Die folgenden Nordic-UUIDs sind Bibliotheks-**Defaults**, die durch
`UuidHelper` übersteuert werden können. Ihre Präsenz im Code beweist nicht,
dass das konkrete Schloss sie anbietet oder bei der normalen Steuerung nutzt.

| UUID | Rolle / Operation | Fundstelle |
|---|---|---|
| `00002902-0000-1000-8000-00805f9b34fb` | Standard-CCCD; Descriptor-Write für Notify/Indicate | `FlutterBluePlugin.f13344v`, `onMethodCall`, case 4, `FlutterBluePlugin.java` |
| `00001801-0000-1000-8000-00805f9b34fb` | Generic Attribute Service | `BaseDfuImpl.GENERIC_ATTRIBUTE_SERVICE_UUID`, `BaseDfuImpl.java` |
| `00002a05-0000-1000-8000-00805f9b34fb` | Service-Changed-Characteristic | `BaseDfuImpl.SERVICE_CHANGED_UUID`, `BaseDfuImpl.java` |
| `0000fe59-0000-1000-8000-00805f9b34fb` | Secure-DFU-Service | `SecureDfuImpl` statischer Initialisierer, `SecureDfuImpl.java` |
| `8ec90001-f315-4f60-9fb8-838830daea50` | Secure-DFU-Control-Point; Write und Notify im DFU-Pfad | `SecureDfuImpl.isClientCompatible` und `performDfu`, `SecureDfuImpl.java` |
| `8ec90002-f315-4f60-9fb8-838830daea50` | Secure-DFU-Paket-Characteristic; Write | `SecureDfuImpl.isClientCompatible`, `SecureDfuImpl.java` |
| `8ec90003-f315-4f60-9fb8-838830daea50` | Buttonless DFU ohne Bond-Sharing; Write/Indicate im DFU-Pfad | `ButtonlessDfuWithoutBondSharingImpl`, `Datei` |
| `8ec90004-f315-4f60-9fb8-838830daea50` | Buttonless DFU mit Bond-Sharing | `ButtonlessDfuWithBondSharingImpl`, `Datei` |
| `8e400001-f315-4f60-9fb8-838830daea50` | Experimenteller Buttonless-DFU-Service und Characteristic | `ExperimentalButtonlessDfuImpl`, `Datei` |
| `00001530-1212-efde-1523-785feabcd123` | Legacy-DFU-Service | `LegacyDfuImpl`, `Datei` |
| `00001531-1212-efde-1523-785feabcd123` | Legacy-DFU-Control-Point; Write/Notify | `LegacyDfuImpl`, `Datei` |
| `00001532-1212-efde-1523-785feabcd123` | Legacy-DFU-Paket; Write | `LegacyDfuImpl`, `Datei` |
| `00001534-1212-efde-1523-785feabcd123` | Legacy-DFU-Versions-Characteristic; Read | `LegacyDfuImpl.readVersion`, `Datei` |

Die UUIDs aus Java-`new UUID(long, long)` wurden aus den beiden 64-Bit-Werten
in die kanonische UUID-Darstellung umgerechnet.

### Unzugeordnete ASCII-UUID-Kandidaten aus dem AOT-Binary

Alle folgenden Strings stehen in
`arm64-v8a/libapp.so`. Der Byte-Scan
erfasst nur ASCII-UUIDs im vollständigen 36-Zeichen-Format, nicht alle
möglichen UUID-Repräsentationen. Service-/Characteristic-Rolle und
Read/Write/Notify sind **nicht** semantisch nachgewiesen:

| UUID | Datei-Offset |
|---|---:|
| `0000fee0-0000-1000-8000-00805f9b34fb` | `0x9c278` |
| `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | `0xe058c` |
| `0000fee1-0000-1000-8000-00805f9b34fb` | `0xe5f84` |
| `00000003-0000-1000-8000-00805f9b34fb` | `0x13bb62` |
| `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | `0x14c9f3` |
| `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | `0x15700b` |
| `00000001-0000-1000-8000-00805f9b34fb` | `0x15afe5` |
| `00002902-0000-1000-8000-00805f9b34fb` | `0x16701e` |
| `00000002-0000-1000-8000-00805f9b34fb` | `0x16c6fb` |

Ein Kandidat kann zu einem anderen Gerätetyp, Framework oder ungenutzten
Code gehören. Der CCCD hat zusätzlich den oben aufgeführten direkten
Java-Beleg, die übrigen nicht.

## Unlock, Lock und Datenfluss

* **Unlock-Einstieg:** nicht identifiziert. Der String
  `simple_unlock_page.dart` ist nur ein Kandidat, kein Beweis für einen
  Button oder einen Call Graph.
* **Unlock-Payload:** unbekannt; das Request-Feld `value` erreicht zwar
  `setValue`, sein Erzeuger und Inhalt sind jedoch nicht rekonstruiert.
* **Lock-Einstieg und Payload:** ebenso unbekannt. Es ist nicht belegt,
  dass dieses Modell überhaupt einen getrennten elektrischen Lock-Befehl
  unterstützt.
* **Vom Benutzer:** Die Schlossnummer wurde für diese Untersuchung genannt;
  ihr Einsatz im Programm, ein etwaiger Account oder weitere Berechtigungen
  sind nicht nachgewiesen.
* **Vom Schloss:** Discover-Services-Ergebnis, Read-Werte und Notifications
  können über die Android-Brücke zu Flutter gelangen. Welche Werte das
  konkrete Schloss liefert und ob sie für eine Challenge verwendet werden,
  bleibt offen.
* **Übertragung:** `request.value` wird als lokaler Characteristic-Wert an
  Android übergeben. Weder ein konkreter Bytestrom noch erfolgreiche
  Funkübertragung oder Schlossreaktion wurden beobachtet.

## Kryptografie, Pairing und Session

Eine Suche nach `Cipher`, `SecretKeySpec`, `MessageDigest`, AES, SHA-1,
SHA-256, MD5 und HMAC in den hier untersuchten Android-Paketen
`cn.sixpower.wlock`, `org.pcgy.flutter_blue`,
`org.pcgy.flutternordicdfu` und `no.nordicsemi.android.dfu` fand keine
schlossspezifische Kryptografie-Implementierung. Ein SHA-256-Hinweis in
`LegacyButtonlessDfuImpl` betrifft ein DFU-Init-Paket, nicht nachgewiesen
die Schlossauthentifizierung. Diese eingeschränkte Suche ist **kein Beweis
für das Fehlen von Kryptografie** im Dart-AOT- oder nativen Code.

Der isolierte AOT-String `authChallenge` bei `0x78499` belegt weder ein
BLE-Challenge-Response-Verfahren noch seine Verwendung durch WELOCK.
Schlüsselerzeugung, Schlüsselquelle, BLE-Pairing/Bonding, Identitätsprüfung,
Session-Aufbau, Verschlüsselungsalgorithmus, IV/Nonce und MAC sind unbekannt.
Die DFU-Option `keepBond` beschreibt ausschließlich die Update-Konfiguration.

## Firmware-Update

`FlutterNordicDfuPlugin.onMethodCall` akzeptiert `startDfu` und `abortDfu`.
Für den Start sind `address` und `filePath` erforderlich; bei `fileInAsset`
wird das Asset vor dem Start in eine lokale Datei kopiert. `m` verarbeitet
`.hex` und `.zip`, konfiguriert `DfuServiceInitiator` und startet
`org.pcgy.flutternordicdfu.DfuService`.

Im Plugin gesetzte Defaults: `keepBond=true`, `forceDfu=false`,
`prepareDataObjectDelay=400 ms`, Packet Receipt Notifications deaktiviert
und experimenteller Buttonless-Modus aktiviert. Mehrere Optionen können durch
MethodChannel-Argumente überschrieben werden. Die Felder `numberOfPackets`
und `enablePRNs` werden an `m` übergeben, dort im gezeigten Code jedoch
nicht verwendet; ihre tatsächliche Wirkung ist hier nicht belegt.
Bei fehlender oder leerer gespeicherter Adresse startet `m` einen Scan; der
Callback akzeptiert den ersten beobachteten Namen mit `DFU`. Aus dem Code
allein folgt nicht, dass dieser Scan im normalen erfolgreichen Startfall
ausgeführt wird oder dem korrekten Schloss zugeordnet ist.

`DfuServiceProvider.getServiceImpl` prüft nacheinander kompatible
Buttonless-, Secure- und Legacy-Implementierungen; der experimentelle Pfad
ist von einer Intent-Option abhängig. Der nachgewiesene Schreibgraph:

```text
startDfu -> FlutterNordicDfuPlugin.m -> DfuServiceInitiator.start
  -> DfuServiceProvider.getServiceImpl -> passende DFU-Implementierung
  -> [Control] Secure/Legacy/Buttonless -> BaseDfuImpl.writeOpCode
     -> setValue -> BluetoothGatt.writeCharacteristic
  -> [Firmware] BaseCustomDfuImpl.uploadFirmwareImage -> writePacket
     -> setValue -> BluetoothGatt.writeCharacteristic
```

`writeOpCode` nutzt Write With Response, `writePacket` Write Without Response
(`BaseDfuImpl.java`,
`BaseCustomDfuImpl.java`).
Der DFU-Pfad ist kein Nachweis für ein normales Unlock-Kommando.
Ein WELOCK-spezifischer Firmware-Download, das Updateformat des konkreten
Schlosses und dessen Bootloader-Verhalten bleiben ungeklärt.

## Home-Assistant-Bewertung und nächste Schritte

| Anforderung | Stand |
|---|---|
| BLE-Service und Characteristics des Schlosses | Unbekannt; AOT-Kandidaten vorhanden, nicht zugeordnet |
| Pairing und Authentifizierung | Unbekannt |
| Unlock / Lock | Payload und Ablauf unbekannt |
| Status / Batterie | Keine belegten Characteristics oder Antwortformate |
| Nutzerverwaltung | Dart-Namenskandidaten vorhanden; BLE-Operationen unbekannt |
| DFU | Android-Implementierung und Default-UUIDs dokumentiert; Geräteunterstützung ungeprüft |

Für eine belastbare Fortsetzung:

1. REA auf einem unterstützten Host mit einem für ARM64-ELF geeigneten
   nativen Provider betreiben; ein Flutter-/Dart-AOT-fähiges
   Rekonstruktionswerkzeug auf die Snapshot-Version abstimmen. Die
   vorstehenden Dart-Dateinamen und UUID-Offsets als Einstiegspunkte
   verwenden, Aufruf- und Datenfluss bis zur MethodChannel-Nachricht
   nachweisen und Decompiler-Ausgaben gegen Instruktionen prüfen.
2. Mit Zustimmung und am eigenen Gerät eine kontrollierte Android-HCI-
   Aufzeichnung erstellen: getrennte, zeitlich markierte Versuche für
   Verbindung, einen Unlock, ggf. erneuten Unlock und Statusabfrage.
   Service Discovery, CCCD-Schreibvorgänge, Richtungen, Write-Typ,
   Antwort-Notifications und Verbindungswechsel vergleichen.
3. Vor Weitergabe Aufzeichnungen lokal auf personenbezogene Daten,
   Schlüssel, Tokens, Geräteadressen und Zugangsdaten prüfen. Ein Mitschnitt
   allein beweist weder Schlüsselableitung noch Wiederholbarkeit; dynamische
   Nonces und serverseitige Schritte sind gesondert zu untersuchen.
4. Erst nach wiederholbarer Verifikation eine Home-Assistant-Integration
   implementieren; keine Kandidaten-UUID oder Payload blind übernehmen.

## 20 priorisierte Projektdateien

Die Auswahl enthält tatsächliche Dateien; die oben genannten Dart-Pfade sind
nur Strings und werden deshalb nicht als Dateien ausgegeben.

| # | Datei | Rolle und Relevanz |
|---:|---|---|
| 1 | `welock.apk` | Original-Artefakt; Referenz für erneute REA-Analyse |
| 2 | `arm64-v8a/libapp.so` | ARM64-Dart-AOT-Snapshot; prioritäre Quelle für UI und Protokoll |
| 3 | `armeabi-v7a/libapp.so` | Zweite Architektur desselben Snapshots; Abgleichsmöglichkeit |
| 4 | `AndroidManifest.xml` | App-Einstieg, Berechtigungen, registrierter DFU-Service |
| 5 | `MainActivity.java` | Android-Einstieg und Flutter-Activity |
| 6 | `GeneratedPluginRegistrant.java` | Registrierung der BLE- und DFU-Brücken |
| 7 | `FlutterBluePlugin.java` | Scan, Connect, GATT-Reads/Writes und Callbacks |
| 8 | `a.java` | Umwandlung von Android-BLE-Objekten in Flutter-Protobuf-Nachrichten |
| 9 | `Protos$WriteCharacteristicRequest.java` | Struktur der internen Write-Anforderung |
| 10 | `Protos$OnCharacteristicChanged.java` | Struktur der Notification-Rückgabe an Flutter |
| 11 | `Protos$DiscoverServicesResult.java` | Struktur der Service-Discovery-Rückgabe |
| 12 | `MethodChannel.java` | Dynamischer Dispatch über die Grenze zwischen Flutter und Android |
| 13 | `FlutterNordicDfuPlugin.java` | DFU-Einstieg, Optionen und Dateiauswahl |
| 14 | `DfuService.java` | App-seitiger DFU-Service |
| 15 | `DfuServiceProvider.java` | Auswahl des konkreten Nordic-Updatepfads |
| 16 | `SecureDfuImpl.java` | Secure-DFU-UUIDs und Zustandsablauf |
| 17 | `LegacyDfuImpl.java` | Legacy-DFU-UUIDs und Kommandos |
| 18 | `BaseDfuImpl.java` | CCCD und generisches DFU-Control-Point-Schreiben |
| 19 | `BaseCustomDfuImpl.java` | Firmware- und Init-Paket-Schreibpfad |
| 20 | `UuidHelper.java` | Überschreibung der DFU-UUID-Defaults |
