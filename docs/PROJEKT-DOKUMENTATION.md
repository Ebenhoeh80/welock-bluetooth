# Regeln für die WELOCK-Projektdokumentation

Diese Regeln gelten für dieses Projekt und ergänzen die bestehenden
technischen Ergebnisse in der [README](reverse-engineering.md).

## Aufbau und Pflege

- Dokumentiere professionell, nachvollziehbar und aktuell. Struktur und
  Dateiaufteilung dürfen verbessert werden; vermeide unnötige Duplikate.
- Verwende thematisch passende Ordner und aussagekräftige Dateinamen.
  Bewahre Analysewerkzeuge, Ergebnisse und Projektartefakte im Projekt auf.
- Halte den Abschnitt „Current shortest path to a working Python unlock
  implementation“ in der README aktuell und verlinke detaillierte Berichte.
- Kennzeichne ältere, überholte Ergebnisse als historischen Stand, statt
  Befunde stillschweigend umzudeuten oder Beweise zu löschen.

## Evidenz und Reproduzierbarkeit

- Trenne nachgewiesene Fakten, wahrscheinliche Zuordnungen und offene
  Hypothesen. Beschreibe Fehlschläge und relevante Grenzen der Werkzeuge.
- Gib für technische Befunde konkrete Fundstellen und soweit verfügbar
  Methoden, Dateioffsets, Frame-Nummern, Hashes und Analysepfade an.
- Nenne bei Tests Aufbau, Ergebnis und Grenzen; behaupte keinen Erfolg ohne
  die zum Ziel passende Prüfung. Ein BLE-Write allein beweist keinen
  mechanisch erfolgreichen Unlock.
- Führe für Protokollannahmen die verwendete App-Version, das untersuchte
  Gerät beziehungsweise den Mitschnitt und gegebenenfalls Modellvarianten an.

## Sensible Daten und Gerätetests

- Bewahre Bugreports, Mitschnitte, Gerätekennungen, Tokens und
  authentifizierungsrelevante Nutzdaten ausschließlich im Git-ignorierten
  Ordner `sensible-daten` auf. Gib sie nicht in öffentlichen Berichten aus.
- Git-Ignore verhindert keine OneDrive-Synchronisierung und schützt nicht
  bereits getrackte Dateien; weise bei Bedarf auf diese Grenzen hin.
- Sende keine unbekannten oder wiederholten Unlock-Payloads auf Verdacht.
  Halte zwischen Unlock-Versuchen mehr als 30 Sekunden Abstand. Trenne
  Benachrichtigungszeiten, BLE-Zeitstempel und mechanische Bestätigung.
