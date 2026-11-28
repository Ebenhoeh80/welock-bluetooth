# Technische Notizen: Architektur, Fehlerbilder, Messungen, Qualitäts-Gates

Diese Seite beschreibt, wie die Integration funktioniert, wofür sie Zeit braucht, was schiefgehen
kann und wie sie sich erholt, was automatisch geprüft wird und welche Optionen verworfen wurden –
und warum. Zahlen sind gemessen, mit Datum und Methode; wo etwas nicht gemessen wurde, steht es
dabei. Zuletzt aktualisiert: 2026-11-23 (Version 2.6.1).

Englische Fassung: [ENGINEERING.md](ENGINEERING.md).

## 1. Architektur und Datenfluss

```
 Home Assistant                       Integration "welock_ble"                       außen
 ───────────────                        ──────────────────────                     ───────
 lock.unlock  ─────────────►  lock.py ──► coordinator.async_unlock()
 switch / Optionen ────────►  switch.py   │  _ensure_unlock_possible()  (12 s Intervall, belegtes Schloss)
                                           │  _ble_lock                  (eine BLE-Sitzung je Schloss)
                                           ▼
                                     ble.async_exchange()  ───────────►  Schloss (Nordic UART, BLE)
                                      _async_connect → _async_read_status → _async_send_command
                                           │  command_provider(state)
                                           ▼
                               choose_unlock_command()  ──► Cache (256 gelernte Befehle) ──► offline
                                           └──────────────► api.WeLockApiClient ───────────► Cloud (HTTPS)
```

`choose_unlock_command()` lernt eine Cloud-Antwort nur, solange der Offline-Entsperr-Schalter
eingeschaltet ist; bei ausgeschaltetem Schalter gibt es den Cloud-Befehl zurück, ohne in den Cache
zu schreiben.

- **Koordinator** (`coordinator.py`) ist der einzige Ort mit Zustand: Anwesenheits-/RSSI-Abfrage
  alle 60 s (liest Home Assistants Bluetooth-Cache, keine Funkaktivität), Batteriestand alle 24 h
  per BLE, Entsperrstatistik (`stats.py`, letzte 100 Versuche), Repair-Issues (`issues.py`,
  Schwellenwerte in `health.py`).
- **BLE-Transport** (`ble.py`) ist in kleine Schritte zerlegt: `_Notifications` (was das Schloss
  zurücksendet), `_note_advertisement`, `_async_connect` (Retry-Helfer, zählt Versuche),
  `_async_read_status`, `_async_send_command`, `_async_teardown`. Die Verbindung wird nach einem
  abgeschlossenen Entsperren im Hintergrund geschlossen (`teardown_runner`), sodass der
  Service-Aufruf früher zurückkehrt.
- **Cloud** (`api.py`): Bei jedem Aufruf wird angemeldet, eine Anfrage gesendet und das Token
  verworfen (einmalig; eine Anmeldung beendet andere Sitzungen des Kontos). MD5 in `md5_hex`
  gehört zum Cloud-Protokoll (Signatur und Client-Kennung), es ist keine Sicherheitsentscheidung.
- **Speicher:** Befehlstabelle und Statistiken nutzen Home Assistants versionierten `Store`.

## 2. Nebenläufigkeit und Lebenszyklus

- Alle BLE-Zugriffe auf ein Schloss werden durch `_ble_lock` serialisiert; ein Entsperren
  währenddessen wird abgelehnt (`lock_busy`), ein zweites innerhalb von 12 s ebenfalls
  (`unlock_too_soon`, der Riegel bleibt etwa 10 s eingelegt).
- Das Hintergrund-Teardown hält `_ble_lock`, bis die Verbindung geschlossen ist (etwa 2 bis 2,7 s),
  und addiert die Teardown-Zeit danach zum bereits erfassten Versuch.
- Beim Entladen wird bis zu 10 s auf noch schließende Verbindungen gewartet (`async_shutdown`).

## 3. Fehlerbilder und Erholung

| Fehler | Wirkung | Erholung / Abhilfe |
|---|---|---|
| Schloss außerhalb Bluetooth-Reichweite | Entsperren wird mit klarer Meldung abgelehnt | Entität nicht verfügbar; Repair-Issue nach 6 h |
| Langsame oder fehlgeschlagene Verbindung | Entsperren scheitert oder dauert lange | bis zu 3 Versuche im Retry-Helfer; Sensor für Verbindungsqualität und Repair-Issue |
| Cloud nicht erreichbar | kein neuer Befehl | mit Offline-Entsperren und gespeichertem Befehl wird die Cloud nicht benötigt |
| Falsches oder geändertes Passwort | `InvalidAuth` | Re-Authentifizierungs-Flow startet |
| Gespeicherter Befehl scheitert beim Schreiben | kann erneut scheitern | der Befehl wird verworfen, der nächste Versuch fragt die Cloud |
| Exchange liefert keinen Status (intern) | möglicherweise nicht initialisierte Variable (von CodeQL gefunden) | jetzt ausdrücklich als fehlgeschlagener Versuch behandelt |
| Beschädigter Speicher | falsche Zahlen | tolerantes Laden ignoriert beschädigte Teile, auch einen `commands`-Wert mit falscher Form |
| Bluetooth-Trennung kehrt nie zurück | der einzelne Slot pro Schloss bleibt reserviert, spätere Entsperrungen werden abgelehnt | `TEARDOWN_TIMEOUT` begrenzt `stop_notify()` und `disconnect()` auf je 5 s |
| Hintergrund-Teardown kann nicht geplant werden | Verbindung bleibt offen und der Slot bleibt belegt | das Übergabeflag wird erst nach der Planung gesetzt; bei Misserfolg werden Verbindung und Schloss hier geschlossen |

## 4. Wohin die Zeit fließt (gemessen)

Methode: Die Integration zeichnet für jedes Entsperren Phasenzeiten auf; zehn aufeinanderfolgende
Entsperrungen am echten Schloss (ASUS USB-BT500-Adapter, RSSI etwa -66 bis -76 dBm) wurden am
2026-11-20 ausgelesen.

| Phase | Ergebnis |
|---|---|
| Bluetooth-Verbindung | 2,9 bis 32,2 s, Median 11 s (mehr als 95 % der Gesamtzeit) |
| Statusanfrage und Antwort | 53 bis 196 ms |
| Cloud-Befehl (Anmeldung und Anfrage) | 218 ms; auf dem Offline-Pfad keiner |
| Warten auf die Bestätigung des Schlosses | etwa 500 ms (493 bis 657 ms) bei 9 von 10, einmal 1,2 s |
| Teardown (im Hintergrund, nicht Teil des Aufrufs) | 1,8 bis 2,7 s |
| Software der Integration, Test mit einem Fake-Schloss | Median 0,8 ms (Budget-Test `test_the_software_part_of_an_unlock_stays_small`, Grenze 250 ms) |

Die Verbindungszeit folgt nicht dem Alter der letzten Anzeige des Schlosses (6,9 s bei 1,1 s
Alter, 3,3 s bei 26 s Alter): Der Funkweg entscheidet, nicht die Strategie der Integration. Eine
Entsperrzeit von etwa 2 s erfordert daher einen kürzeren Funkweg (einen ESP32-Bluetooth-Proxy in
der Nähe des Schlosses) oder eine stehende Verbindung – nicht anderen Code.

## 5. Qualitäts-Gates

Die unten aufgeführten Gates werden in CI erzwungen, sofern in einer Zeile nicht *manuell* steht;
manuelle Zeilen sind Messungen, keine blockierenden Prüfungen.

| Prüfer | Gate | Ergebnis 2026-11-23 |
|---|---|---|
| Ruff (E, W, F, I, B, C4, UP) | keine Befunde | bestanden; erweiterte Regeln (SIM, RET, PL, C901, ANN) sind *manuell* und nicht in `pyproject.toml` konfiguriert (201 Befunde mit der aktuellen Tool-Version, bewusst nicht aktiviert) |
| black | Formatierung (CI und `RELEASING.md` nutzen black; `ruff format` würde 3 weitere Dateien ändern) | bestanden |
| MyPy mit den echten Home-Assistant-Typen | keine Fehler | bestanden (19 Quelldateien geprüft) |
| pytest, Unit-Tests (Python 3.10 bis 3.13) | alle bestanden | 131 bestanden, 1 übersprungen (Live-Test, `-m "not live"`) |
| pytest in echtem Home Assistant Core | alle bestanden | 87 bestanden |
| Coverage (beide Suiten zusammen) | mindestens 95 % | 98,46 % |
| hassfest | gültiges Manifest, Strings, Quality Scale | bestanden |
| xenon | absolut B, Module A, Durchschnitt A | bestanden |
| CodeQL (security-and-quality) | keine neuen Alerts | bestanden; eine Regel für das MD5-Protokoll-Hashing abgeschaltet (`.github/codeql/codeql-config.yml`) |
| Diagnostics | das gesamte JSON enthält keinen Konto-, Titel-, Schlossnummern-, Adress- oder Befehlswert | bestanden (Test durchsucht jeden Bezeichner) |
| Lieferkette (CI) | `contents: read`, Actions an SHAs gepinnt, Testpaket gepinnt | bestanden; hassfest und hacs/action bleiben bewusst auf ihren dokumentierten Referenzen |
| Home Assistant Quality Scale | `quality_scale.yaml` | Gold; nur Platinum `strict-typing` offen |

Nicht ausgeführt: SonarQube, Semgrep (auf dem Entwicklungsrechner nicht verfügbar), py-spy und
Scalene (die oben genannten Zahlen stammen aus den eigenen Phasenzeiten der Integration und einem
Benchmark mit einem Fake-Schloss).

## 6. Entscheidungen und verworfene Optionen

- **Cloud-Anmeldung parallel zur Bluetooth-Verbindung** verworfen: der Cloud-Schritt sind 218 ms
  von etwa 11 s; der Gewinn liegt unter 2 %.
- **Erfolg vor der Bestätigung des Schlosses melden** noch nicht umgesetzt: es würden etwa 0,5 s
  (5 %) gespart, aber die Erfassung des Versuchs auf dem sicherheitsrelevanten Pfad geändert; dafür
  ist zuerst ein Test am Schloss nötig.
- **Stehende Bluetooth-Verbindung / Verbinden bei Ankunft** nicht umgesetzt: Akkuverbrauch und
  ohne das Schloss nicht testbar; bleibt eine strategische Option.
- **Identität des Eintrags = Bluetooth-Adresse des Moduls** (beibehalten). Home Assistants
  Bluetooth-Erkennung meldet genau diese Adresse, und die Adresse eines Schlossmoduls ist fest
  (anders als eine IP-Adresse). Die Schlossnummer als Identität zu verwenden würde Erkennung und
  Entsperrpfad für einen kaum vorkommenden Fall (ausgetauschtes Modul) neu aufbauen und birgt das
  Risiko, Entitäten eines sicherheitsrelevanten Geräts zu verlieren. Der Titel zeigt die
  Schlossnummer in Klammern (`WeLock (22231059)`); der Modulname (`WeLockFMHAE`) ist nur das, was
  die Cloud zum Entsperren benötigt.
- **Voluptuous zu probatio:** Home Assistants Typ-Hinweise nennen bereits eine andere
  Schema-Bibliothek; mypy meldet sie für drei Module (`pyproject.toml`, dokumentierte
  Übersteuerung). Home-Assistant-Release-Notes beobachten.

## 7. Offene Punkte

- Platinum-Regel `strict-typing`.
- Feldtest jedes Release-Kandidaten am Schloss (mehrfach entsperren, offline und über die Cloud).
  2.5.0-rc.1 wurde am 2026-11-20 getestet und als 2.5.0 veröffentlicht.
- 2.6.0 wurde noch nicht am Schloss ausprobiert. Es ändert nichts am Entsperrpfad, aber jeder
  erfasste Versuch trägt jetzt zusätzlich die Scanner-Bezeichnung: nach dem Update prüfen, dass ein
  Entsperren weiterhin im Verlauf und in den Diagnostics erscheint.
