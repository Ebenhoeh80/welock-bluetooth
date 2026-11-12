# WELOCK: HCI-Mitschnitt und BLE-GATT-Befunde

**Fortschreibung:** Die unten historisch als `W1` bezeichnete Initialnachricht
ist nach neuer AOT- und Bytevergleichsevidenz eine Batterieabfrage. Für das
beobachtete vierbyteige Antwortformat wurden die nachfolgenden Parameter
`randomFactor` und `battery` zugeordnet. Einzelheiten und Grenzen stehen in
der [fortgeschriebenen AOT-Analyse](FLUTTER-AOT-ANALYSE.md#fortschreibung-blutter-und-rea-funktionsanalyse).
Dies beweist weder das Format des späteren Unlock-Befehls noch eine
eigenständige Entriegelung.

## Kontrollierter Offline-Versuch vom 8. November 2026

Nach einer Wartezeit von mehr als 30 Sekunden wurde um `06:41:03 UTC`
einmal die beim früheren, mechanisch bestätigten App-Test verwendete
Schaltfläche betätigt. Unmittelbar davor meldeten die Android-Einstellungen
`wifi_on=0` und `mobile_data=0`; Bluetooth war aktiviert. Diese
Einstellungen allein belegen nicht das Fehlen sämtlicher anderer möglicher
Netzwerkverbindungen. Der markierte Tap und ein Screenshot 20 Sekunden
danach sind unter `sensible-daten/android` abgelegt. Der Screenshot zeigt
keine explizite Erfolgsmeldung; das mechanische Ergebnis ist unbestätigt.
Die vom Nutzer ausgeschalteten Netzwerkverbindungen wurden nicht verändert.

Nachtrag: Der Nutzer berichtet für den Offline-App-Ablauf die Meldungen
„Connect success“ und „Request network failed“ sowie, dass das Schloss
nicht entriegelt. Diese Nutzerbeobachtung präzisiert den Offline-Befund;
die Zuordnung eines konkreten HCI-Frames und die technische Fehlerursache
bleiben dennoch von den unten genannten Einschränkungen betroffen.

Der anschließend gesicherte
Bugreport (lokaler Mitschnitt - nicht im Repo)
hat SHA-256
`b9b37318e6b22b9938e2b82b80e37f25997673b20185c546c610e72a13bc62c7`;
der daraus extrahierte
HCI-Mitschnitt (lokaler Mitschnitt - nicht im Repo)
hat SHA-256
`28ebe90e0e52d5fc13ef0da4da519ba04715a1008fbfa2542372615e84058a4b`.
Ein lokaler Btsnoop-/ACL-/ATT-Rohrecordvergleich fand in Frame 18665 einen
bytegenau passenden 15-Byte-Batterie-Write und in Frame 18667 eine
vierbyteige Antwort mit Batteriepräfix, jeweils an den zuvor beobachteten
Handles `0x000e` beziehungsweise `0x000b`. Unter der weiterhin vorläufigen
Korrektur von minus einer Stunde liegen diese Frames etwa vier Sekunden nach
dem Tap. Bis zum letzten Btsnoop-Record, korrigiert etwa 49 Sekunden nach
dem Tap, wurde kein weiterer ATT-Write-Command oder keine weitere
ATT-Notification beobachtet.

REA `inspect-packet-capture` bestätigte unabhängig für diese beiden Frames
die ATT-Opcodes `0x52` und `0x1b` sowie die genannten Handles;
REA-Evidenz (lokaler Mitschnitt - nicht im Repo),
ID `ev_c41e0ec9595fd3e71c6a407d08f15bb1a4a9a12a7468f68fb9efd70981f4ee2f`.
Die Prüfung umfasst nur diese zwei ausgewählten Frames, nicht die
Abwesenheit späterer Pakete. Ein erster REA-Hilfeaufruf wurde nach 30 Sekunden
ohne Ausgabe abgebrochen; ein erneuter Aufruf mit längerer Frist und die
anschließende Analyse waren erfolgreich. Byteinhalt, Länge und Zeitbereich
stammen weiterhin aus dem lokalen Rohrecordvergleich.

**Einordnung:** Die zeitliche Zuordnung ist plausibel, aber von der
ungeklärten Zeitkorrektur abhängig; die Klassifikation wurde zunächst
mit einem Rohrecordparser und anschließend für zwei Frames mit REA
vorgenommen. Ein ausbleibender Folge-Write allein ist
weder ein mechanischer Erfolgs- oder Misserfolgsnachweis noch ein Beweis,
dass die Cloud zwingend erforderlich ist: unter anderem bleiben andere
Fehler und ein späterer Vorgang außerhalb des Mitschnitts möglich.
Das Ergebnis und die Ursache sind offen. Ein neues Unlock-Experiment darf
nicht ohne die vorgeschriebene Pause von mehr als 30 Sekunden erfolgen.

## Smartphone-Benachrichtigungen vom 8. November 2026

Der Nutzer stellte ein Bild von drei WELOCK-Benachrichtigungen (lokaler Mitschnitt - nicht im Repo)
bereit und erläuterte, sie seien durch Entriegelungen in der App entstanden.
Die Meldungen zeigen `01:02:58`, `01:03:24` und `01:03:57`; diese Zeiten
bezeichnen Meldungen, nicht nachgewiesene Tastendruckzeitpunkte. Sie liegen
26 beziehungsweise 33 Sekunden auseinander. Die zuvor genannte Regel von
**mehr als 30 Sekunden zwischen Unlock-Versuchen** bleibt verbindlich;
aus Benachrichtigungsabständen allein kann der Abstand zwischen
Tastendrücken nicht exakt bestimmt werden.

Der bei geöffnetem Telefon gesicherte
Bugreport (lokaler Mitschnitt - nicht im Repo) enthält den
HCI-Mitschnitt (lokaler Mitschnitt - nicht im Repo)
mit SHA-256 `f9424685e303049f52f25c11b6f506bd7898c42d9b2fe80064748eaf39198e8a`.
Der vorherige Mitschnitt `welock-controlled-03.log` ist sein bytegenaues
Präfix. REA `inspect-packet-capture` bestätigte die ATT-Opcodes und Handles
aller zwölf nachstehend ausgewählten Frames, Evidence-ID
`ev_f05ed0d82c9bdbac9cb7db7a406bb27a563282e59c763d10bcabe6b16fdfb532`;
Byte-Längen und Zeiten wurden ergänzend aus den Btsnoop-Rohrecords geprüft.

Die folgende zeitliche Zuordnung setzt weiterhin die **nicht unabhängig
erklärte Korrektur von minus einer Stunde** auf die als UTC+1 interpretierten
Btsnoop-Zeiten voraus. Angegeben ist die 5-Byte-Notification am Ende der
jeweiligen Sequenz. Die zeitliche Nähe ist ein starkes Indiz, aber kein
eigenständiger Nachweis für mechanischen Erfolg oder die Herkunft jeder
Benachrichtigung.

| Meldung | Batterie-Write | 4-Byte-Notify | Folge-Write | 5-Byte-Notify | Korrigierte HCI-Zeit |
|---|---:|---:|---:|---:|---|
| 01:02:58 | 11292 | 11295 | 11297 | 11304 | 01:02:57,902 |
| 01:03:24 | 11433 | 11438 | 11440 | 11446 | 01:03:24,018 |
| 01:03:57 | 11704 | 11706 | 11712 | 11716 | 01:03:57,348 |

Die drei 4-Byte-Antworten, Folge-Writes und 5-Byte-Antworten sind jeweils
untereinander verschieden; Rohwerte bleiben geschützt. Eine weitere
gleichartig aufgebaute Sequenz endet korrigiert um `01:03:41,194`
(Frames 11568, 11570, 11574, 11580), ohne eine auf dem Bild sichtbare
zugehörige Benachrichtigung. Daher kann nicht jede solche Sequenz allein
anhand der Paketform als erfolgreicher Unlock klassifiziert werden. Es
wurde kein neuer BLE-Write vom PC ausgelöst.

## Einordnung und Datenschutz

Nach der statischen [Flutter-AOT-Analyse](FLUTTER-AOT-ANALYSE.md) wurde mit
Zustimmung ein Android-Bugreport lokal erstellt und ausschließlich auf
Bluetooth-Daten untersucht. Der Gesamt-Bugreport wurde auf Computer und
Telefon anschließend gelöscht. Der extrahierte
HCI-Mitschnitt (lokaler Mitschnitt - nicht im Repo)
liegt im ignorierten Projektordner. **Er kann Gerätekennungen und
authentifizierungsrelevante Daten enthalten und sollte nicht veröffentlicht
werden.** Der Nutzer hat anschließend gebeten, die lokalen Daten für
zukünftige Analysen aufzubewahren. Auch der nachfolgend beschriebene neue
Bugreport und die extrahierten Bluetooth-Dateien liegen auf Nutzerwunsch
thematisch gegliedert unter `sensible-daten`: HCI-Aufzeichnungen unter
`hci`, Bugreports unter `bugreports` und REA-Evidenz unter `rea`.
Kopien im bisherigen Archiv und im Sitzungsordner bleiben erhalten; die
Projektkopien wurden per SHA-256 mit den Archivdateien verglichen.
Die Projekt-`.gitignore` ignoriert `sensible-daten`. Git-Ignore verhindert
weder Cloud-Synchronisierung noch das Einchecken bereits getrackter Dateien:
Das Projekt liegt in OneDrive und kann daher synchronisiert werden.

Der Nutzer bestätigte zwei erfolgreiche Entriegelungen nach dem Neustart von
Bluetooth. Im Mitschnitt gibt es zwei untersuchte BLE-Verbindungen zu
derselben Peer-Adresse. Ihre zeitliche Nähe und das bestätigte Vorgehen
machen einen Bezug zum Schloss plausibel, aber aus den vorliegenden Paketen
allein ist die Zuordnung zur Schlossnummer `DEVICE_NUMBER` nicht sicher belegt.
Die Nummer erschien nicht als ASCII-String in den untersuchten Frames; das
ist kein Beweis, dass sie anders kodiert fehlt.

## Herkunft und Verifikation

* Android-Bluetooth-Dienst nach Neustart: `sSnoopLogSettingAtEnable = FULL`.
* Extrahiert wurde `FS/data/log/bt/btsnoop_hci.log` aus dem Bugreport.
  BTSnoop-Version 1, Linktyp 1002, 2.625 Records, davon 676 HCI-ACL-Records.
  Keine der 2.625 Record-Längen war im Dateiformat als gekürzt markiert.
* SHA-256 des untersuchten Mitschnitts:
  `239f3ed857ba0557c8c78ca8bd9d7c38929d397f2ea4f0859ed2d299180a5f50`.
  Frame-Nummern unten gelten für genau diese Datei und sind einsbasiert.
* REA `inspect-packet-capture` mit Linux-TShark 4.2.2 unter WSL:
  Evidence-ID
  `ev_b8d87483351e0d703bc4b0e069c963ab6c39ecaf0876042fed5b7c255eede8ff` (lokaler Mitschnitt - nicht im Repo).
  Die Abfrage umfasste 14 gezielt ausgewählte Frames, nicht sämtliche
  Pakete. Die Ergebnisse wurden zusätzlich mit Windows-TShark 4.6.9 und
  einer lokalen HCI-/L2CAP-/ATT-Dekodierung geprüft.
* Der erste Bugreport bei `sSnoopLogSettingAtEnable = EMPTY` enthielt nur
  eine gekürzte Btsnooz-Zusammenfassung ohne ACL-Daten. Erst nach dem
  vom Nutzer durchgeführten Bluetooth-Neustart und den beiden erneuten
  Entriegelungen war die separate vollständige Datei im Bugreport vorhanden.
* Ein erster eigener ATT-Parser interpretierte eine andere Read-By-Type-
  Antwort fälschlich als Characteristic-Deklaration; dies wurde durch Prüfung
  der Eintragslänge korrigiert und mit TShark gegengeprüft. Ein Versuch,
  Zeiten aus der gekürzten Btsnooz-Zusammenfassung umzurechnen, schlug fehl;
  deshalb wird daraus kein Zeitbereich behauptet. Bei einer erneuten Prüfung
  lieferte TShark `btatt.value` für die als Nordic UART dekodierten
  Notifications nicht; die 23 unten aufgeführten Frames wurden stattdessen
  anhand ihrer Rohframes und ATT-Metadaten überprüft, ohne Nutzdaten
  auszugeben.

## GATT: im Mitschnitt beobachtet

| Rolle | UUID | ATT-Handle im Mitschnitt | Eigenschaften | Beleg |
|---|---|---:|---|---|
| Service | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | Servicebereich `0x0009–0xffff` | Primary Service | Frames 2143 und 2352 |
| Write-Characteristic | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | Value `0x000e`, Declaration `0x000d` | `0x0c`: Write und Write Without Response | Frames 2164 und 2374 |
| Notify-Characteristic | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | Value `0x000b`, Declaration `0x000a` | `0x10`: Notify | Frames 2161 und 2370 |
| CCCD des Notify-Werts | `00002902-0000-1000-8000-00805f9b34fb` | `0x000c` | Descriptor | Frames 2171 und 2386 |

Die UUID-Strings waren schon an den Datei-Offsets `0x14c9f3`, `0x15700b`,
`0xe058c` und `0x16701e` in
`libapp.so` vorhanden; erst die
GATT-Discovery belegt ihre Rollen **für das beobachtete Gerät**. ATT-Handles
sind sitzungs-/firmwareabhängig und dürfen nicht als allgemeingültige
Kennungen anderer Geräte vorausgesetzt werden.

## Sichtbarer Ablauf

In beiden Verbindungen wurden Services und Characteristics entdeckt.
Der CCCD `0x000c` wurde mit `01 00` per ATT Write Request (`0x12`)
beschrieben und die Gegenstelle antwortete jeweils mit Write Response
(`0x13`), z. B. Frames 2177/2180 und 2396/2398. Danach folgten Writes an
Value-Handle `0x000e` mit ATT Write Command (`0x52`, ohne ATT-Response)
und Notifications von `0x000b` (`0x1b`).

Alle **11** beobachteten Characteristic-Schreibwerte dieser beiden
Verbindungen waren 15 Bytes lang und begannen mit `0x55`. Über alle 15
Positionen war nur Position 0 bei allen Werten gleich. Insgesamt gab es
fünf unterschiedliche Schreibwerte. Daraus allein folgen weder die Bedeutung
von `0x55` noch eine Verschlüsselungs-, Prüfbyte- oder Opcode-Struktur.

Um möglicherweise sensible Werte nicht in einer Projektdatei abzulegen,
werden identische komplette Schreibwerte als `W1` bis `W5` und identische
komplette Notifications als `N1` bis `N9` anonymisiert. Diese Bezeichnungen
sind **keine rekonstruierten Protokoll-OpCodes**.

| Verbindung | Frame | Beobachtung |
|---|---:|---|
| A | 2185 / 2190 | `W1` (15 Bytes) → `N1` (4 Bytes) |
| A | 2191 / 2199 | `W2` (15 Bytes) → `N1` (4 Bytes) |
| A | 2200 / 2206 | `W3` (15 Bytes) → `N2` (5 Bytes) |
| A | 2226 / 2228 | `W1` (15 Bytes) → `N3` (5 Bytes) |
| A | 2232 / 2238 | `W4` (15 Bytes) → `N4` (5 Bytes) |
| A | 2254 / 2256 | `W1` (15 Bytes) → `N3` (5 Bytes) |
| A | 2258 / 2264 | `W4` (15 Bytes) → `N4` (5 Bytes) |
| B | 2403 / 2408 | `W1` (15 Bytes) → `N5` (4 Bytes) |
| B | 2409 / 2415 / 2417 | `W4` (15 Bytes) → `N6` (20 Bytes), `N7` (17 Bytes) |
| B | 2434 / 2440 | `W1` (15 Bytes) → `N8` (4 Bytes) |
| B | 2444 / 2450 | `W5` (15 Bytes) → `N9` (5 Bytes) |

Der Pfeil zeigt **nur die beobachtete Reihenfolge**, nicht eine bewiesene
Request-/Response-Zuordnung. Dass `W1` in beiden Verbindungen identisch und
wiederholt ist, ist nachgewiesen; ob es sich etwa um Initialisierung, eine
Statusabfrage oder einen Teil der Authentifizierung handelt, ist unbekannt.
Die Notifications von 20 und 17 Bytes sind zwei ATT-Notifications; eine
Zusammengehörigkeit auf Anwendungsebene ist nicht belegt.

## Nachtrag: weitere Entriegelungen

Nach den ersten Aufzeichnungen meldete der Nutzer weitere Entriegelungen.
Bluetooth war weiterhin aktiviert und `sSnoopLogSettingAtEnable = FULL`.
Ein erneuter lokaler Bugreport wurde erstellt und
`btsnoop_hci.log` (lokaler Mitschnitt - nicht im Repo)
daraus extrahiert. Dessen SHA-256 lautet
`d74db5fd5846c7947b1c75b2b246896740162a58bba5ccbdc4450037b0d5de63`;
er enthält 5.742 vollständige Records. Der vorherige Mitschnitt mit
2.625 Records ist bytegenau sein Anfang, deshalb sind dessen Frame-Nummern
unverändert. Der neue
Bugreport (lokaler Mitschnitt - nicht im Repo)
und die extrahierten Dateien bleiben lokal; **der vollständige Bugreport
kann auch nicht-Bluetooth-bezogene persönliche Informationen enthalten**.
Die REA-Evidence-ID oben bezieht sich nur auf den älteren Mitschnitt.
Für diesen Nachtrag wurden Windows-TShark und ein lokaler byteweiser
Vergleich genutzt; eine neue REA-Evidence-ID liegt nicht vor.

Im hinzugekommenen Teil sind fünf weitere Verbindungen zu demselben
beobachteten Peer nachweisbar. Die nachstehende Liste zeigt alle dabei
ermittelten Characteristic-Writes und Notifications. `W1`–`W5` und
`N1`–`N9` haben dieselbe Bedeutung wie oben; neue Labels stehen jeweils
für neue vollständige Bytefolgen. Die jeweils einleitenden
CCCD-Schreibvorgänge sind separat aufgeführt. Die Verbindung wird durch die
Frame-Nummer des Verbindungsereignisses identifiziert:

| Verbindung | Beobachtete Sequenz: Frame und Vergleichslabel |
|---|---|
| 2819 | 2906 CCCD; 2912 W1; 2918 N10 (4); 2920 W6; 2942 N11 (5) |
| 4359 | 4439 CCCD; 4445 W1; 4449 N12 (4); 4451 W7; 4458 N13 (5) |
| 4770 | 4851 CCCD; 4858 W1; 4862 N14 (4); 4863 W8; 4869 N15 (20); 4870 N16 (20); 4871 N17 (20); 4872 N18 (1); 4874 CCCD; 4889 W1; 4892 N19 (4); 4893 W9; 4900 N20 (5) |
| 4937 | 5016 CCCD; 5023 W1; 5025 N21 (4); 5027 W10; 5033 N22 (20); 5034 N16 (20); 5035 N17 (20); 5036 N23 (9); 5039 CCCD; 5052 W1; 5054 N24 (4); 5055 W11; 5061 N25 (5) |
| 5403 | 5483 CCCD; 5490 W1; 5493 N26 (4); 5495 W12; 5501 N27 (5) |

Alle 14 neuen Writes sind 15 Bytes lang und beginnen mit `0x55`. Über beide
Mitschnitte zusammen sind das 25 Writes und 12 verschiedene vollständige
Werte. In den fünf neuen Verbindungen ist `W1` zu Beginn und nach einer
erneuten CCCD-Aktivierung jeweils bytegleich; die darauf folgenden Writes
`W6`–`W12` sind untereinander und von den früheren Werten verschieden.
Dass das zweite Write variiert, beweist weder Verschlüsselung noch
Challenge-Response. Zwei aufeinanderfolgende lange Notifications (`N16`
und `N17`) sind in den Verbindungen 4770 und 4937 jeweils bytegleich;
ihre inhaltliche Bedeutung und ein Zusammenhang mit anderen Notifications
sind nicht belegt.

Die weiteren Entriegelungen wurden nicht einzeln mit Zeitmarken erfasst und
es gibt keinen Kontrolllauf ohne Entriegelung. Daher lässt sich weiterhin
keiner der neuen Werte zuverlässig einem konkreten Tastendruck oder einem
Unlock-Befehl zuordnen. Auch die Zuordnung der Peer-Adresse zur angegebenen
Schlossnummer bleibt ungeprüft.

### Zeit- und Bytevergleich ausgewählter Folgen

Für sieben Folgen wurden die Frames 2912/2918/2920, 4445/4449/4451,
4858/4862/4863, 4889/4892/4893, 5023/5025/5027, 5052/5054/5055 und
5490/5493/5495 byteweise verglichen. Jede Vier-Byte-Notification ist
vollständig verschieden; dabei unterscheidet sich nur ihr Byte mit
Nullindex 2. Die unmittelbar folgenden Writes sind alle verschieden;
deren Bytepositionen 1–9 und 14 variieren, Positionen 0 und 10–13
bleiben in dieser Stichprobe konstant. Die untersuchte Stichprobe ist klein
und enthält auch Folgen mit langen nachfolgenden Notifications: Daraus
folgen weder ein Challenge-Response-Algorithmus noch ein Unlock-Opcode.

Die Zeit von Initial-Write bis Notification betrug in diesen sieben Folgen
24–91 ms, von Notification bis zum nächsten Write 208–301 ms.
Dies sind beobachtete Abstände inklusive App- und Übertragungsverzögerung,
keine nachgewiesenen Mindestwartezeiten. Der Vergleich verwendete
TShark-Rohframes lokal; ein erster Versuch mit dem Zeitfeld als `float`
schlug fehl, weil die JSON-Ausgabe dieses Feld als ISO-Zeit darstellte.
Die erfolgreiche Messung verwendete stattdessen `frame.time_relative`.

### Stand der dynamischen Instrumentierung

Am 08.11.2026 meldete das verbundene Telefon Android 16 und
`ro.debuggable=0`. `run-as cn.sixpower.wlock id` scheiterte mit
`package not debuggable`; ein `su`-Programm wurde über den normalen
Shell-Suchpfad nicht gefunden. Dies beweist nicht, dass andere
Instrumentierungswege ausgeschlossen sind, erlaubt aber keinen direkten
Frida-Attach als normale Shell. Eine Suche im vorhandenen Bugreport fand
keine Treffer für `LocalUnLock`, `RequestBleCmdModel`,
`sendCmdUint8List`, `flutter_blue` oder `authChallenge`; die Suche beweist
nicht, dass zur Laufzeit keine solchen Daten existieren.

Der sichtbare Bildschirm war aus und die Bildschirmsperre aktiv; ein
Screenshot lieferte deshalb keinen nutzbaren App-Inhalt. Ein kontrollierter
Leerlauf-/Unlock-Vergleich konnte ohne entsperrtes Telefon und Bedienung
nicht gestartet werden. Weder App-Daten noch Installation oder
Telefon-Sicherheitseinstellungen wurden verändert.

### Kontrollierter Tastendruck nach Entsperren des Telefons

Nach dem Entsperren zeigte die App die Schlossseite mit der Nummer
`DEVICE_NUMBER`. Nach 20 Sekunden ohne automatisierte Eingabe erfolgte genau ein
ADB-Tap auf den sichtbaren Entriegelungsbutton. Die Gerätezeit vor und nach
dem Tap sowie der Leerlaufbeginn sind in der sensiblen
Zeitmarkierung (lokaler Mitschnitt - nicht im Repo) abgelegt.
Ein Screenshot nach dem Tap zeigt **„Connect success“**; diese Meldung
allein belegt keine mechanische Entriegelung. Der Nutzer bestätigte
anschließend ausdrücklich, dass der Knauf bei diesem Versuch entriegelt
wurde. Ein späterer Screenshot zeigt wieder die Schlossseite.

Der zugehörige
HCI-Mitschnitt (lokaler Mitschnitt - nicht im Repo) hat SHA-256
`03f57b098af3846fb74970355ddba39197bc6d4a3d9cf334e03d2e66cabb159b`;
der vorherige Mitschnitt ist bytegenau sein Anfang. Der
Bugreport (lokaler Mitschnitt - nicht im Repo) und die
Screenshots bleiben im ignorierten Projektordner. Die Analyse wurde mit
TShark und einem lokalen Bytevergleich durchgeführt, nicht mit REA.

**Zeitbasis:** TShark gab für die neuen Frames Unix-Zeiten etwa eine Stunde
nach der erfassten Geräte-Epoch-Zeit an. Die Gerätezeitzone war `+0100`; die folgenden
Tap-Abstände sind deshalb mit einer **vorläufigen** Korrektur von -3600 s
berechnet. Das ist eine plausible lokale Zeitstempelverschiebung, aber
keine unabhängig bewiesene Erklärung ihres Ursprungs. Ohne diese Korrektur
gab die Auswahl für das markierte Zeitfenster keine ATT-Frames zurück.

| Frame | Vorläufiger Abstand vom Beginn des Taps | Beobachtung |
|---:|---:|---|
| 8002 | vor den unten aufgeführten ATT-Frames | BLE-Verbindung; dieselben Peer-Endpunkte wie zuvor |
| 8082 | +2,108 s | CCCD-Write an Handle `0x000c` |
| 8089 | +2,277 s | 15-Byte-Write an `0x000e`, bytegleich zum früheren `W1` |
| 8092 | +2,309 s | 4-Byte-Notification an `0x000b` |
| 8094 | +2,531 s | neuer 15-Byte-Write an `0x000e` |
| 8100 | +3,047 s | 5-Byte-Notification an `0x000b` |

Im 20-Sekunden-Leerlauf vor dem Tap wurden unter dieser Zeitkorrektur keine
ATT-Write-Commands, Notifications oder Write-Requests beobachtet. Das ist
ein Vergleich der sichtbaren Schlossseite mit anschließendem Tastendruck,
**kein** gleichartiger Kontrolllauf mit BLE-Verbindungsaufbau ohne Unlock.
Die zeitliche Reihenfolge und der gleiche Peer sprechen für eine Zuordnung
der Sequenz zur Bedienung von `DEVICE_NUMBER`; eine technische Bindung der
Peer-Adresse an die angezeigte Nummer ist dadurch noch nicht bewiesen.

Frame 8094 ist damit ein **starker Kandidat für einen aktionsspezifischen
Write im bestätigten Entriegelungsablauf**, aber noch kein isolierter oder
entschlüsselter Unlock-Befehl. In
acht verglichenen Folgen waren die 4-Byte-Notifications und nachfolgenden
15-Byte-Writes jeweils verschieden; nur Byte 2 der Notifications variierte.
Kein einzelnes Byte des folgenden Writes entsprach diesem variierenden Byte
über alle acht Folgen hinweg mit konstantem XOR. Ein Test über 31
beobachtete 15-Byte-Writes fand keine einfache Summen- oder XOR-Prüfsumme
über ein zusammenhängendes Präfixsegment, die das letzte Byte bis auf eine
Konstante erklärt. Das schließt andere Prüfsummen, Verschlüsselung oder
Schlüsselabhängigkeit nicht aus.

### Weitere Versuche und PC-BLE-Probe

Nach der Bestätigung wurden drei weitere Taps mit rund 16 Sekunden Abstand
erfasst. **Erst danach** teilte der Nutzer mit, dass zwischen Entriegelungen
mehr als 30 Sekunden liegen müssen, weil das Schloss während der
Entriegelungsphase keinen weiteren Unlock-Befehl empfangen kann. Die
kurzen Abstände waren deshalb für diese Versuchsreihe ungeeignet; sie
werden künftig nicht wiederholt. Ein Befehl für den dritten Tap ist nicht
nachgewiesen; der Grund dafür ist nicht sicher festgestellt. Mechanische
Erfolge der weiteren Versuche wurden nicht bestätigt.

Der neue Mitschnitt (lokaler Mitschnitt - nicht im Repo) hat
SHA-256 `be2b95d5ae1b6c2c79701dba578e5c37a7356a86f8361d21ef2949e92ec2cae0`,
8.535 Records ohne auf Dateiebene gekürzte Records und enthält den
vorherigen Mitschnitt als exaktes Präfix. Unter derselben vorläufigen
Zeitzonenkorrektur sind die folgenden Sequenzen den ersten beiden Taps
zeitlich nahe; sie haben denselben Peer wie der bestätigte Versuch.

| Tap | Initial-Write | 4-Byte-Notification | Folge-Write | 5-Byte-Notification |
|---|---:|---:|---:|---:|
| 1 | 8313 | 8317 | 8319 | 8325 |
| 2 | 8486 | 8488 | 8490 | 8497 |
| 3 | keine entsprechende Folge gefunden | – | – | – |

Die Initial-Writes sind bytegleich mit Frame 2185. Die Folge-Writes in
8094, 8319 und 8490 sind je 15 ASCII-alphanumerische Bytes lang und
unterscheiden sich voneinander an den Nullindex-Positionen 2–9 und 14.
Ihre Positionen 0–1 und 10–13 sind in diesen drei Frames jeweils konstant.
Auch die vier Byte langen vorangehenden Notifications sind verschieden;
dies belegt allein weder eine Challenge noch deren mathematische Beziehung
zum Write.

Vom Windows-PC aus wurde anschließend mit Bleak der beobachtete Peer
gescannt, verbunden und seine GATT-UUIDs und Eigenschaften erneut
bestätigt. Ein separater einmaliger Test abonnierte Notifications und
schrieb **nur** den zuvor aufgezeichneten Initialwert W1 ohne ATT-Response.
Der PC erhielt eine vier Byte lange Notification; sie war nicht bytegleich
zur Notification vor dem bestätigten Versuch. Es wurde dabei **kein
Unlock-Folge-Write** gesendet. Details der empfangenen Bytes liegen nur
in der ignorierten
Probe-Datei (lokaler Mitschnitt - nicht im Repo).
Der PC-Transport funktioniert damit bis zur ersten Antwort; der nachfolgende
Write muss weiterhin korrekt erzeugt und seine Wirkung überprüft werden.

### Weitere vom Nutzer ausgelöste Entriegelungen

Der Nutzer berichtete von weiteren Entriegelungen. Das Telefon meldete
weiterhin `sSnoopLogSettingAtEnable = FULL`. Der anschließende
Mitschnitt (lokaler Mitschnitt - nicht im Repo) hat SHA-256
`ecd3f2cb9a00ee851b9af0a6c14b4d9f1665967065bb7b5e5f86ae75208a34ff`;
der vorherige Mitschnitt ist sein bytegenaues Präfix. Unter den neuen
Datensätzen wurden fünf Verbindungen mit ATT-Writes und Notifications zu
denselben Peer-Endpunkten wie beim bestätigten Test gefunden. Vier der
Sequenzen enthalten je eine 4-Byte-Notification und einen anschließenden
15-Byte-Write mit vollständig alphanumerischem Inhalt:

| Verbindung | Initial-Write | 4-Byte-Notification | Folge-Write | Weitere Notification |
|---:|---:|---:|---:|---:|
| 10406 | 10493 | 10495 | 10497 | 10503 |
| 10542 | 10625 | 10627 | 10629 | 10635 |
| 10712 | 10805 | 10808 | 10811 | 10817 |
| 10877 | 10965 | 10967 | 10970 | 10983 |

Die genauen Tastendruckzeiten und mechanischen Ergebnisse der einzelnen
neuen Folgen sind nicht separat markiert. Verbindungsaufbau und Paketfolge
allein beweisen daher nicht, welche dieser vier Folgen jeweils eine
Entriegelung verursachte.

REA `inspect-packet-capture` bestätigte OpCodes und Handles für die jeweils
vier markierten Frames der Verbindungen 10406 und 10877;
Evidence `ev_50aa0c44f35fecb89678207f50f6d4ab93685eb48893632a3cc9c1558ce0921e` (lokaler Mitschnitt - nicht im Repo).
Erstversuche scheiterten an einer fehlenden Linux-Bibliothek
`libibverbs.so.1` und an fälschlich komma-getrennten Feldnamen; nach
Installation der Bibliothek und wiederholten `--fields`-Optionen gelang
die Abfrage. REA analysierte nur die acht ausgewählten Frames, nicht die
mathematische Erstellung der Nutzwerte.

Ein lokaler Vergleich aller 21 beobachteten Folgen der Form Initial-Write,
4-Byte-Notification, 15-Byte-Folge-Write ergab 19 unterschiedliche
Notifications. Zwei Notifications wiederholten sich:

* Frames 10627 und 10808 sind bytegleich; die anschließenden Writes 10629
  und 10811 ebenfalls. Das ist mit einer deterministischen Abbildung
  vereinbar, beweist sie aber nicht.
* Frames 10329 und 10346 sind ebenfalls bytegleich, die jeweiligen
  Folge-Writes 10344 und 10347 aber verschieden. Der erste davon entspricht
  dem wiederholten Initial-Write. Die Notification allein erklärt somit
  nicht eindeutig, welcher vollständige Write folgt; Zustand oder Art der
  Aktion können zusätzlich relevant sein, sind aber nicht identifiziert.

Die Abstände zwischen den nicht markierten Nutzeraktionen wurden nicht als
Mindestwartezeit interpretiert. Für neue Entriegelungsversuche gilt
weiterhin die Nutzerangabe: **mehr als 30 Sekunden Abstand**.

## Noch nicht rekonstruiert

* **Unlock:** Frame 8094 ist nach dem markierten Tastendruck ein Kandidat,
  aber seine Funktion, Erzeugung und mechanische Wirkung sind nicht bewiesen.
* **Lock, Status, Batterie und Nutzerverwaltung:** keine Kommandostruktur
  oder Ergebnisdekodierung nachgewiesen.
* **Authentifizierung und Kryptografie:** kein Schlüssel, kein
  Challenge-Response-Ablauf und kein Algorithmus nachgewiesen. Im betrachteten
  Ausschnitt wurden keine SMP-Pakete und keine HCI-Auth-/Encryption-Change-
  Events beobachtet; das beweist weder, dass kein bestehendes Bonding oder
  keine Verschlüsselung existiert, noch dass die Anwendung ohne eigene
  Authentifizierung arbeitet.
* **Replay:** Die Wiederholungen und das gemeinsame `0x55` reichen nicht,
  um einen Write sicher als wiederholbares Entriegelungspaket anzusehen.
  Keine unbekannten Pakete blind an ein Schloss senden.

## Nächster evidenzbasierter Schritt

Einen Kontrolllauf „verbinden, aber nicht entriegeln“ mit dem bestätigten
Entriegelungsablauf vergleichen und insbesondere bestimmen, welches Write
nur bei der Entriegelung vorkommt. Zwischen Entriegelungsversuchen nach
Nutzerangabe **mehr als 30 Sekunden** warten. Über mehrere unabhängige
Sitzungen prüfen, welche Bytes von Schlossantworten, Schlüsseln, Account-
oder Serverdaten abhängen. Vor einer Umsetzung sind die genaue Funktion,
die Erfolgsantwort und das Verhalten bei fehlgeschlagenem Unlock zu belegen.

Nach Ende der Untersuchung kann das HCI-Snoop-Logging in den
Entwickleroptionen wieder deaktiviert werden; ein erneuter Bluetooth-Neustart
kann erforderlich sein, damit die Änderung wirksam wird.
