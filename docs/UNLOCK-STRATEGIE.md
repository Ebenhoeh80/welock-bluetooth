# Untersuchungsstrategie: eigenständiger WELOCK-Unlock

## Ziel und Priorisierung

Das Ziel ist ein verifizierter, zuverlässiger Python-BLE-Client, der das
Schloss des Eigentümers ohne die offizielle App entriegelt. Verständnis
der gesamten App oder reine Code-Rekonstruktion sind keine eigenständigen
Ziele.

- Wähle selbständig die nächste sichere Aktion mit dem höchsten erwarteten
  Fortschritt zum funktionierenden Unlock. Berücksichtige Aufwand,
  Erkenntnisgewinn und Erfolgswahrscheinlichkeit; wechsle Strategien,
  wenn ein gezieltes Experiment voraussichtlich ergiebiger ist.
- Nutze REA und geeignete ergänzende Werkzeuge dort, wo sie den kürzesten
  belastbaren Weg unterstützen. Wiederhole abgeschlossene Arbeit nicht
  ohne konkreten Erkenntnisgewinn.
- Aktualisiere nach abgeschlossenen Schritten das Protokollmodell und
  die Vertrauensgrade, benenne den stärksten Blocker und wähle den nächsten
  Schritt. Halte den aktuellen Stand in der
  [README](reverse-engineering.md#current-shortest-path-to-a-working-python-unlock-implementation).
- Fahre selbständig fort, bis der Unlock nachweislich funktioniert oder
  eine Aktion zusätzliche Daten, einen physischen Eingriff oder eine
  Entscheidung des Nutzers erfordert.

## Benötigte Experimente

Wenn Nutzereingaben erforderlich sind, beschreibe vorab für **ein**
priorisiertes Experiment das Ziel, die exakten benötigten Schritte,
den erwarteten Erkenntnisgewinn und messbare Erfolgskriterien. Benenne
Unsicherheiten und setze das Experiment nur mit verfügbaren Ressourcen um.

Ein erfolgreicher Schreibvorgang oder eine Meldung allein beweist keine
Entriegelung. Ein Erfolg erfordert die überprüfte mechanische Funktion und
eine Wiederholung unter Einhaltung von mehr als 30 Sekunden Abstand
zwischen Unlock-Versuchen.

Die Datenschutz-, Evidenz- und Dokumentationsregeln in
[PROJEKT-DOKUMENTATION.md](PROJEKT-DOKUMENTATION.md) bleiben verbindlich.

## Aktueller Stand und priorisierter nächster Schritt (12.11.2026)

**Durchbruch durch die differenzielle Analyse:** Der Cloud-`command` ist eine
**Funktion von `randomFactor` allein** – `battery` und `devicePassword` gehen
nicht variabel ein. `rf` ist ein einzelnes Byte, also gibt es nur **256
mögliche Befehle** pro Schloss. Die Positionen 0–7 folgen der geschlossenen,
reversiblen Formel `(rf*k)>>2 & 63` (verifiziert), 8–11 sind konstant, Position
12 ist eine deterministische Prüfziffer. Die frühere 3DES/AES-Hypothese ist
damit **widerlegt**. Details:
[Differenzielle Analyse](WELOCK-CLOUD-ANALYSE.md#differenzielle-analyse-command-ist-eine-funktion-von-randomfactor-allein-12-november-2026).

Der Offline-Generator wird als **geerntete Tabelle `rf→command`** gebaut
([welock_offline_oracle.py](../tools/welock_offline_oracle.py) `--harvest`, kein
BLE-Write; danach `--table … --rf N` rein offline). Die multiplikative Formel ist
nur eine Näherung (vereinzelte Ausnahmen im Vollbereich), daher ist die Tabelle
maßgeblich. **Stand: 256/256 vollständig** – in mehreren `--resume`-Läufen
geerntet (Cloud drosselt nach ~146 Anfragen). Die Cloud wird für den Unlock
damit nicht mehr benötigt.

Erst nach lokaler Erzeugung eines zur **frischen** BLE-Challenge passenden
Befehls folgt – vor Ort, mit mechanischer Kontrolle und >30 s Abstand – ein
einzelner Versuch. **Verbleibendes Risiko:** eine geräteseitige Replay-/
Zählersperre ist nicht ausgeschlossen und nur durch diesen physischen Versuch
prüfbar.
