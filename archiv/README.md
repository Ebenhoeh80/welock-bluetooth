# Archiv / Archive

Dieses Verzeichnis enthält archivierte, ersetzte oder historische Skripte aus früheren Entwicklungs- und Testständen (z. B. aus der initialen Bereinigung von `/toolsdev` und Vorversionen der Diagnose-Skripte).

Die aktiven, produktionsreifen Werkzeuge befinden sich in [`/tools`](../tools/README.md).

### Archivierte Skripte:
- `welock_cloud_login_all.py`: Experimentelles Cloud-Login-Skript zur Ausgabe aller Rohdaten. Vollständig integriert in `tools/welock_cloud_login.py` (mit `--show-data` bzw. `login_response_data` in `--json`).
- `welock_unlock_experiment.py`: Frühes Entriegelungs-Experiment. Reifere Version in `tools/welock_command_probe.py` und `tools/welock_unlock.py`.
- `toolsdev_migrated/`: Skripte aus dem früheren `/toolsdev`-Verzeichnis vor der Zusammenführung.
