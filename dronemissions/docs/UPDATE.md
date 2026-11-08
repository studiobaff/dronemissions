## Missionsplaner: kompakte Werkzeugleisten, Kalotte und POI-AGL · 8.11.2026

Branch `codex/planner-cap-corridor`, Generator 0.4.0. Eigener PR nach `main`, Web-Deployment; Bridge unverändert.

- Schmale Leisten für Kamera, Flugart, Aufnahmeabstände und Zeichnen über einer größeren Karte; ein-/ausklappbare Seitenleiste. Automatische Vorschau und editierbare Umrisse bleiben erhalten.
- Neue Helix/Doppelhelix: Kugelkalotte, automatischer Blick zur Objektmitte, senkrechte Scheitelaufnahme. Bestehende Zylinderform bleibt bei alten Planungen erhalten.
- Eigene Flugarten Linie/Korridor. POI relativ Start oder AGL am Ziel plus Offset; getrennt vom Flug-Höhenbezug. Feste Kalotte + Gelände-Folgen wird abgelehnt.
- Optionale Zusatzpause nach Foto standardmäßig 0; Ausrichten/Anhalten bleibt. Nominale Überlappung ist ausdrücklich keine 3D-Oberflächenmessung.
- PHP-Geometrie-/DEM-/KMZ-Regressionen, Scheduler-Test und Planner-API-Integration bestanden. Browser bei 1280 × 720: Polygon ziehen, automatische Neuberechnung, Wechsel zur Doppelhelix, Kalotte mit 292 Fotos nach Speichern/Wiederöffnen identisch, Linie/Korridor, fehlender POI-AGL-Start sperrt Speichern. Neue Testfälle in `tests/planner.php`. Kein Gerätetest/Flugtest.
- Anforderung „abgeflogene Höhenreferenzpunkte als Planungsgrundlage“ in `docs/PLANNER.md` dokumentiert, **noch nicht implementiert**; keine automatische Höhenableitung aus vier Wegpunkten behaupten.

## Missionsplaner: automatische Vorschau und verständliche Aufnahmeabstände · 8.11.2026

Branch `codex/planner-live-preview`. Generator 0.3.0. Veröffentlichung über eigenen PR und den vorhandenen Web-Deployment-Workflow; kein Bridge-Build nötig.

- Gemeinsame Planungsansicht mit weiterhin editierbarem Umriss; automatische, serialisierte Neuberechnung nach Parameter-/Geometrieänderungen. Veraltete Antworten werden verworfen, Speichern/Export bleiben bis zur aktuellen gültigen Vorschau gesperrt.
- Neue Planungen: Foto- und Bahnen-/Höhenabstand direkt in Metern. Optional Vorgabe über Überlappung. Bildfeld, Rechenabstand und nominale Prozentwerte sichtbar; tatsächliche eingepasste Abstände separat.
- Raster verteilt mindestens zwei Bahnen über den Umriss. Alte gespeicherte Planungen werden neu berechnet; bestehende Missions-KMZs bleiben unverändert.
- Browser auf isolierter Testinstallation: Polygon zeichnen, Ecke ziehen, Zwischenpunkt einfügen, Ecke löschen, Undo; automatische Reaktion auf Meterabstand, Höhe und Richtung; Wechsel Grid → Helix → Grid; ungültige Höhe sperrt Export, Korrektur erholt sich; Speichern/Neuladen behält Abstände; keine Konsolenfehler.
- PHP-Geometrie-/DEM-/KMZ-Regressionen, neue Meter-/Rasterfälle, Scheduler-Test und Planner-API-Integration bestanden. CI prüft zusätzlich die übrigen Archivfälle.
- Kein Gerätetest oder Flugtest dieser neuen Planergeneration. 3D-/Schrägbildüberlappung wird ausdrücklich nur als Rechenwert bezeichnet.

# Update vom GitHub-Branch auf den Server

**Produktivinstallation:** Seit PR #1/#2 veröffentlicht GitHub Actions geprüfte Änderungen in `main` automatisch auf `service.studiobaff.com/dronemissions/`. Änderungen vom Claude-Branch zuerst per PR nach `main` übernehmen. Der Release-Wechsel sichert SQLite/Konfiguration und prüft HTTPS; private Daten bleiben außerhalb. Die folgenden manuellen Kopierbefehle sind nur für andere Installationen bzw. administrativen Notbetrieb gedacht. Für die Produktivinstallation nicht parallel per rsync veröffentlichen. Details: `deploy/README.md` im Repository.

Übergabe für die Person oder den Assistenten, der den Webserver betreut. Stand: 8. November 2026.

## Was wo liegt

- Quelle: `https://github.com/studiobaff/dronemissions`, Branch `claude/drone-missions-ui-handoff-4nsj6e` (nach dem Merge in `main`: Branch `main`).
- Das Repository ist öffentlich. Das ist in Ordnung, weil es nur Code, Doku und synthetische Beispiele enthält. Zugangsschlüssel, `config.json`, `missions.sqlite`, `blobs/`, `sessions/` und `tmp/` liegen im privaten Verzeichnis außerhalb des Webroots und sind per `.gitignore` ausgeschlossen. Niemals private Daten ins Repository legen.
- Auf dem Server wird nur der Inhalt von `dronemissions/public/` ausgeliefert. Alles andere (Tests, `tools/`, `bridge/`, Doku) bleibt außerhalb des Webroots.

## Schritte

1. Datenbank und `blobs/` sichern (siehe `DEPLOYMENT.md`, Abschnitt Updates und Backups).
2. Aktuellen Stand holen, zum Beispiel in ein Arbeitsverzeichnis auf dem Server oder auf dem Mac:

```sh
git clone --branch claude/drone-missions-ui-handoff-4nsj6e --depth 1 https://github.com/studiobaff/dronemissions.git dronemissions-src
```

Bei vorhandenem Arbeitsverzeichnis stattdessen `git fetch origin && git checkout claude/drone-missions-ui-handoff-4nsj6e && git pull`.

3. Nur `public/` in den Webroot kopieren, ohne private Dateien zu überschreiben:

```sh
rsync -av --delete --exclude 'config.json' dronemissions-src/dronemissions/public/ /usr/local/www/vhosts/studiobaff/dronemissions/
```

Zielpfad an die Installation anpassen. `--delete` entfernt veraltete Dateien aus dem Webroot; der private Ordner liegt nicht darunter und ist nicht betroffen.

4. Schema-Ergänzung: Diese Version legt beim ersten Aufruf automatisch die Spalten `overview_waypoint`, `overview_version`, `litchi_url` und die Tabelle `mission_attachments` an, falls sie fehlen (`dm_migrate()` in `lib.php`). Bestehende Daten werden nicht verändert.

5. Prüfen: HTTPS-Aufruf, Login, Bibliothek, eine Mission öffnen, Download einer Originaldatei, Karte mit Panel „Karte & Zonen“. PHP-Syntax bei Bedarf mit `php -l` auf `api.php`, `lib.php`, `zones.php`, `address.php`, `location.php`.

## Bridge

Die installierte Version und den genauen Quellstand vor jedem Build in [BRIDGE.md](BRIDGE.md) und [STATUS.md](STATUS.md) prüfen. `main` enthält derzeit nicht den vollständigen Bridge-Quellbaum. Nicht unbesehen einen älteren Branch über die installierte Version bauen: iPad-Aufräumfunktion und ADB-Verpackungsfix müssen enthalten sein.

Aus einem sauberen, geprüften Bridge-Checkout:

```sh
python3 -m unittest discover -s bridge/tests
python3 bridge/build_desktop.py
```

Das aktuelle Bundle heißt **`outputs/dronemissions-bridge.app`**, das Installationsziel **`/Applications/dronemissions-bridge.app`**. App vor dem Austausch beenden, bisherigen Stand als Rückfallkopie behalten, neuen Build separat bereitstellen und Signatur sowie gebündelte ADB-Prüfsumme prüfen. Zugangsdaten und Einstellungen nicht löschen.

Für den authentifizierten Download im Webarchiv das geprüfte Paket erstellen:

```sh
ditto -c -k --keepParent "outputs/dronemissions-bridge.app" "dronemissions-bridge-macOS-<commit>.zip"
```

ZIP und zugehörige Versionsdokumentation in den privaten Serverordner `bridge/` außerhalb des Webroots übertragen, Server-Prüfsumme und authentifizierten Download vergleichen. Alte Pakete separat archivieren, damit keine veralteten Downloads angeboten werden. Nur das Web-Release wird automatisch über GitHub Actions veröffentlicht; Mac-Build und Download-Paket sind getrennte Schritte.

Erlaubte Endungen: zip, dmg, pkg, exe, msi, txt, md. Dateinamen mit „mac“ oder „win“ werden der Plattform zugeordnet. Die Web-App berechnet die SHA-256-Prüfsumme beim ersten Aufruf und zeigt sie im Dialog. Ein Windows-Paket entsteht nur auf einem Windows-Rechner (`bridge/README.md`, Abschnitt Windows 11).


## Nachtrag Kartenebenen

Mit den Kartenebenen kommt die Tabelle `map_layers` hinzu; `dm_migrate()` legt sie beim ersten Aufruf an. Vektor-Ebenen liegen als `.geojson` im Blob-Ordner des privaten Verzeichnisses. Für den WMTS-Import muss der Server ausgehende https-Verbindungen zu dem Dienst aufbauen dürfen. Die Integrationstests nehmen optional `--wmts-fixture <URL>`; mit `DRONEMISSIONS_DEV=1` darf der Dienst auf 127.0.0.1 liegen.
