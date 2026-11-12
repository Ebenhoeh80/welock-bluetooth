# WeLock – Reverse-Engineering-Dokumentation

Dieser Ordner dokumentiert, **wie** das lokale Entsperr-Verfahren hinter dieser
Home-Assistant-Integration erarbeitet wurde – vom BLE-Protokoll über die
Cloud-API bis zur entscheidenden differenziellen Analyse. Die Dokumentation
dient der **Nachvollziehbarkeit**: Sie erklärt den Weg, damit andere ihn für ihr
eigenes Gerät verstehen und (unter eigener Rechtsgrundlage) selbst nachgehen
können.

## Rechtliche Grundlage

Das Reverse Engineering wurde zur Herstellung von **Interoperabilität** nach
**§ 69e UrhG** durchgeführt: an einem selbst erworbenen Schloss, mit dem eigenen
Konto, ausschließlich zur Anbindung an eine eigene Steuerung (Home Assistant).
Die Voraussetzungen des § 69e UrhG sind:

- die Software wurde rechtmäßig erworben,
- die Informationen sind für die Interoperabilität erforderlich,
- es werden keine urheberrechtlich geschützten Programmteile kopiert.

Aus diesem Grund enthält dieses Repository **keine** dekompilierten App-Teile,
keine APK, keine Binärartefakte und keine Bluetooth-/Netzwerk-Mitschnitte. Die
Dokumente verweisen stellenweise auf solches Material – diese Dateien lagen nur
**lokal** vor und werden bewusst **nicht** veröffentlicht. Wer den Weg
reproduzieren möchte, dekompiliert die App selbst, für sein eigenes Gerät und
unter seiner eigenen Rechtsgrundlage.

## Anonymisierung

Geräte- und kontospezifische Werte sind durch Platzhalter ersetzt, weil sie für
das Verständnis unerheblich und für jedes Gerät anders sind:

| Platzhalter | Bedeutung |
|---|---|
| `DEVICE_NUMBER` | die konkrete Schlossnummer (`deviceNumber`) |
| `ANDROIDSERIAL` | die ADB-Seriennummer des Analyse-Telefons |
| `U1XXXXXXXXAAAAX` / `U1YYYYYYYYAAAAY` | konkrete, gerätespezifische Unlock-Befehle (nur die **Struktur** ist dokumentiert) |

Die geerntete `rf→command`-Tabelle ist **gerätespezifisch** und wird nie
veröffentlicht; jede Installation lernt sie für ihr eigenes Schloss selbst.

## Kernergebnis in einem Satz

Der an das Schloss geschriebene Entsperr-Befehl ist eine **Funktion des
einen Byte `randomFactor` allein** – `battery` und der 24-stellige
`devicePassword` gehen nicht variabel ein. Pro Schloss existieren damit nur
**256 mögliche Befehle**; eine Blockchiffre (3DES/AES) ist widerlegt. Die
Integration kann die Befehle daher lokal zwischenspeichern und – nach einmaligem
Lernen – ohne Cloud entsperren.

## Lesereihenfolge

1. **[reverse-engineering.md](reverse-engineering.md)** – chronologisches
   Vorgehen und Einstieg (ADB, Dekompilierung, Suchstrategie).
2. **[BLE-ANALYSE.md](BLE-ANALYSE.md)** – das Bluetooth-Protokoll (Nordic UART
   Service, Battery-Challenge, Command-Write).
3. **[FLUTTER-AOT-ANALYSE.md](FLUTTER-AOT-ANALYSE.md)** – statische Analyse des
   Flutter-/Dart-AOT-Codes (Öffnungspfad, HTTP-Schicht).
4. **[WELOCK-CLOUD-ANALYSE.md](WELOCK-CLOUD-ANALYSE.md)** – die Cloud-API, das
   Endpunkt-Inventar und die **differenzielle Analyse**, die zeigt, dass der
   Befehl nur von `randomFactor` abhängt.
5. **[WELOCK-HCI-ANALYSE.md](WELOCK-HCI-ANALYSE.md)** – Auswertung der
   Bluetooth-HCI-Mitschnitte (lokal; Rohdaten nicht im Repo).
6. **[UNLOCK-STRATEGIE.md](UNLOCK-STRATEGIE.md)** – daraus abgeleitete Strategie
   für den lokalen Unlock.
7. **[PROJEKT-DOKUMENTATION.md](PROJEKT-DOKUMENTATION.md)** und
   **[HOMEASSISTAND-Projekt.md](HOMEASSISTAND-Projekt.md)** – Projektüberblick
   und Integrations-Planung.

## Sicherheits- und Reproduktionshinweis

- Sende **keine** selbst erzeugten oder wiederholten Unlock-Payloads „auf
  Verdacht" an ein Schloss und halte zwischen Versuchen **> 30 Sekunden**
  Abstand.
- Die offline erzeugten Befehle sind rechnerisch verifiziert (identisch zur
  Cloud-Antwort). Eine **mechanisch** erfolgreiche Entriegelung mit einem rein
  lokal erzeugten Befehl ist nur vor Ort, mit mechanischer Kontrolle, zu prüfen;
  eine geräteseitige Replay-/Zählersperre ist nicht abschließend ausgeschlossen.
- Die zugehörigen Forschungs- und Audit-Werkzeuge liegen unter
  [`../tools/`](../tools/) (siehe dortige `README`).
