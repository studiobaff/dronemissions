# KMZ-Editor · 8. November 2026

Neu: Archivmission öffnen → **Wegpunkte bearbeiten**. Punkte ziehen, Koordinaten/Höhen ändern, kontrolliert löschen/einfügen und als neue Version speichern. Originale bleiben erhalten. Separate Module `kmz-editor*`; Claudes Planer-UI wird nicht verändert. Umfang, Grenzen und Prüfungen: [KMZ-EDITOR.md](KMZ-EDITOR.md). Veröffentlichung über geprüften PR nach main; nur Web-App, kein Bridge-Build nötig.

## Oberfläche, Freigabekarte und PDF · 10.11.2026

Sprachen: Deutsch, English, Українська (Auswahl unten in der Seitenleiste oder unter Einstellungen; `?lang=uk` für Links). Übersetzt sind Seitenleiste, Kopf, Werkzeugleiste, Auswahl, kompakte Liste, Freigabekarte, Einzelmissionskarte, Kartenpanel-Beschriftungen, Naturschutz-Status und das gesamte PDF; Dialoge für Upload, Mission, Planer und Editor bleiben vorerst deutsch. Kompakte Liste: Griff links, Positionsnummer ohne Klammern, Titel mit Projekt- und Typ-Chip, Öffnen, Checkbox rechts; bei Touch zusätzlich Hoch/Runter-Knöpfe. Karte: H als weißer Kreis mit blauem Rand, Aufnahmepunkt als orangefarbenes Symbolquadrat, Kennung als eigenes Schild darunter, Zuordnung fein gestrichelt, Flugroute mit heller Kontur, gewählte Mission mit Ring hervorgehoben. PDF: Kopf mit Logo, Wortmarke und Betreiber (Einstellungen → Name), Karte, Legende, Quellen, Tabelle der Missionen bzw. Wegpunkte mit wiederholter Kopfzeile; Schrift DejaVu Sans als eingebettetes Unicode-Subset (Kyrillisch), keine Bedien- oder Statustexte mehr im Dokument.

## Missionsplaner 0.6 · Oberfläche nach Litchi-Vorbild · 8.11.2026

Branch `claude/planner-ui-litchi`, eigener PR nach `main`; Codex prüft und veröffentlicht. Nur `public/planner.js`, Planer-Regeln in `public/style.css` und Doku; keine Änderung an Berechnung, API, Export oder Datenformaten, kein Bridge-Build nötig. Große Karte mit Werkzeuggruppen an der Karte, Slider-Leiste mit Zahlenfeldern, größenveränderliche Seitenleiste mit fünf Abschnitten, Stepper an Zahlenfeldern, Ergebnis-Pille in der Karte, Prüfseite in der Seitenleiste. Tests: `node --check`, `planner-live.cjs`, `planner.php`, `parser.php`, Deploy-Tests, Integration/Vorschauen/Projektkarten/Planner-API auf frischer Loopback-Installation, Browserläufe bei 1280 × 720, 1440 × 900, 1180 × 820 und 430 × 860 mit Screenshots unter `docs/screenshots/planner/`. Gestaltungsregeln: `docs/PLANNER-UI-DESIGN.md`.

## Höhenreferenz direkt aus dem Webarchiv · 8.11.2026

Im Planer unter „Höhenpunkte aus Erkundungsflug“ eine DJI-KMZ aus dem Archiv wählen und „Höhenpunkte übernehmen“ anklicken. Liste mit Projektpfaden, serverseitiger Prüfung beider Projektberechtigungen, Dateityp und Prüfsumme. Die neueste KMZ-Version wird als feste Kopie der Höhenpunkte in den Entwurf übernommen; Name, Versionsnummer und Quellprüfsumme bleiben erhalten. Spätere Änderungen der Quelle verändern den Entwurf nicht. Lokaler Upload bleibt verfügbar. Startbezug, Auswahl und Sicherheitsabstand werden weiterhin bewusst eingestellt, Mindesthöhenprüfung zunächst aus. API-Tests (Rechte, aktuelle Version, gespeicherte Kopie) und Browserprüfung bestanden. Keine Bridge-Änderung.

## Missionsplaner 0.5.2 · Einzelbilder / Video · 8.11.2026

Aufnahmeauswahl in der oberen Werkzeugleiste; keine Bezeichnung „SkySplat“. Video-Grid erzeugt nur Anfang/Ende jeder Bahn. Gelände kann zusätzliche Höhenstützpunkte verlangen; Helix behält ihre Kurvenstützpunkte. Jeder KMZ-Abschnitt richtet die Kamera aus, startet die Aufnahme und stoppt sie am letzten Wegpunkt. Gimbal-Pitch wird zwischen benachbarten Punkten interpoliert. Keine Foto-/Hover-Aktionen im Videoexport. Bestehende Wegpunkt-Stopps bleiben erhalten; kein Versprechen eines unterbrechungsfreien Rundflugs.

Aufnahmeart wird im Entwurf gespeichert, alte Entwürfe öffnen als Einzelbilder. Prüfsumme umfasst jetzt neben Punkten auch Exportparameter. Video zeigt Wegpunkte, Videoabschnitte und reine Streckenzeit statt Fotozahlen/Fotopausen. Fotoabstand und Längsüberlappung sind beim Video-Grid ausgeblendet; Bahnenabstand/Querüberdeckung bleiben einstellbar. Videocrop, Seitenverhältnis und FOV müssen zum tatsächlichen Aufnahmeformat passen. Auflösung/Bildrate werden in DJI Fly eingestellt, nicht vom Planer gesetzt.

PHP-Geometrie-/Exporttests und API-Lebenszyklus mit synthetischen Daten bestanden, einschließlich Gelände, Abschnittsteilung, Speichern/Wiederöffnen und Archivkonflikten. Browser: Wechsel 30 Fotos → 6 Video-Wegpunkte bei identischen Bahnen; Bahnabstand ändert die Vorschau automatisch. DJI-Fly-Geräte-/Flugtest für Video weiterhin offen. Nur Web-App; kein Bridge-Build nötig. Details: `PLANNER.md`.

## Missionsplaner 0.5.1 · Kalotte mit Gelände · 8.11.2026

Die bisherige pauschale Sperre „feste Kugelkalotte kann nicht dem Gelände folgen“ entfällt. Das bestehende DEM-Verfahren hebt/senkt die Flugpunkte, richtet die Kamera neu auf den POI aus und erhält den Nadir-Scheitel. FOV-Anzeigen unterscheiden jetzt Winkelüberdeckung nach DEM und Windungswerte vor DEM. Fehlende Daten, Mindesthöhe und Bewegungsgrenzen bleiben geprüft. Starres Kippen/Rotation der Flugroute ist nicht enthalten. Nur Web-App; kein Bridge-Build. Details in `PLANNER.md`.

## Missionsplaner 0.5.0 · Höhenreferenzen und FOV · 8.11.2026

Branch `codex/planner-height-references`. Nur Web-App; kein Bridge-Build. Veröffentlichung über eigenen PR nach bestandenen Checks.

- DJI-KMZ-Höhenreferenzen mit explizitem Startbezug/Offset, Auswahl, Sicherheitsabstand und serverseitiger Mindesthöhenprüfung. Save/Reopen und JSON behalten Referenzpunkte; Originaldatei bleibt unberührt. Gestrichelte Referenzroute mit getrennten Strecken, keine Höheninterpolation.
- FOV-gesteuerte Halbkugel/Doppelhelix mit Nadir; −70°-Trapezprojektion für Raster. Winkel-/nominale Überdeckung nicht als nachgewiesene 3D-Oberflächenüberdeckung darstellen.
- Kreuzraster, Footprint, längste Kante, ±1°/+90°, verkettete Meterabstände, optionaler Startort zur Umkehrung der Routenreihenfolge. Status zweizeilig über der Karte. Neue Startorte werden bei neuer Planung verworfen.
- Geschwindigkeitsvorgaben Grid 2,6 / Helix 4,3 m/s aus bereitgestellten Referenzdateien; manuell änderbar. API-Default unverändert.
- Behebung zweier Browser-/Persistenzfehler: Höhenreferenzen fehlten in gespeicherten Planungen; Import konnte durch den generischen Dialog-Backdrop-Handler das Planerfenster schließen.
- PHP-/API-/Scheduler-Tests und isolierte Browserprüfung bestanden. Geräte-/Flugprüfung weiterhin offen. Details und Grenzen: `PLANNER.md`.

## Missionsplaner: kompakte Werkzeugleisten, Kalotte und POI-AGL · 8.11.2026

Branch `codex/planner-cap-corridor`, Generator 0.4.0. Eigener PR nach `main`, Web-Deployment; Bridge unverändert.

- Schmale Leisten für Kamera, Flugart, Aufnahmeabstände und Zeichnen über einer größeren Karte; ein-/ausklappbare Seitenleiste. Automatische Vorschau und editierbare Umrisse bleiben erhalten.
- Neue Helix/Doppelhelix: Kugelkalotte, automatischer Blick zur Objektmitte, senkrechte Scheitelaufnahme. Bestehende Zylinderform bleibt bei alten Planungen erhalten.
- Eigene Flugarten Linie/Korridor. POI relativ Start oder AGL am Ziel plus Offset; getrennt vom Flug-Höhenbezug. Feste Kalotte + Gelände-Folgen wird abgelehnt.
- Optionale Zusatzpause nach Foto standardmäßig 0; Ausrichten/Anhalten bleibt. Nominale Überlappung ist ausdrücklich keine 3D-Oberflächenmessung.
- PHP-Geometrie-/DEM-/KMZ-Regressionen, Scheduler-Test und Planner-API-Integration bestanden. Browser bei 1280 × 720: Polygon ziehen, automatische Neuberechnung, Wechsel zur Doppelhelix, Kalotte mit 292 Fotos nach Speichern/Wiederöffnen identisch, Linie/Korridor, fehlender POI-AGL-Start sperrt Speichern. Neue Testfälle in `tests/planner.php`. Kein Gerätetest/Flugtest.
- Anforderung „abgeflogene Höhenreferenzpunkte als Planungsgrundlage“ in `docs/PLANNER.md` dokumentiert, inzwischen in Generator 0.5.0 umgesetzt, siehe Abschnitt oben; kein Hindernismodell aus vier Wegpunkten ableiten.

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

10.11.2026: Orbit Grid mit Foto/Video, variabler Kreisüberlappung und verbundenem
oder separatem Pfad. Missionen für Karte/PDF einzeln oder alle auswählbar;
Naturschutz bleibt sichtbar.

10.11.2026: Standortprüfung trennt Schutzgebietstreffer von gemeldeten UAS-
Einschränkungen. Keine pauschale Verbotsbewertung aus Schutzgebietsflächen;
„Wann relevant?“ erläutert Gebietsregeln, Artenschutz und Natura 2000. Fehlende
oder veraltete Daten bleiben als ungeklärt sichtbar. Hinweise in DE/EN/UK.
