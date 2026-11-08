# Missionsplaner – Pause am 8. November 2026

Auf ausdrücklichen Wunsch des Nutzers pausiert. Keine Veröffentlichung in diesem Arbeitsgang. Der Nutzer fährt den Mac herunter.

## Arbeitsstand

- Repository: studiobaff/dronemissions.
- Arbeitsverzeichnis: `work/roundtrip-device-proof` innerhalb des lokalen missionplaner-Ordners.
- Branch: `codex/planner-live-preview`, Ausgangsbasis main `823af6fc22694edc413f86739c23c70b781ac15f`.
- Änderungen sind als lokaler Zwischenstand gesichert. Noch nicht gepusht, kein PR, nicht live. Nicht mit Claudes Branch oder dem Hauptarbeitsverzeichnis überschreiben.

## Auftrag und Problem

Die Route reagierte nach Parameteränderungen nicht automatisch. Der Umriss soll jederzeit direkt bearbeitbar bleiben; Missionsart (insbesondere Helix), Abstand und Höhe sollen während der Kartenarbeit erreichbar sein.

## Implementierter Zwischenstand

- Gemeinsame Ansicht „Planen · Umriss & Flugparameter“; separate Ansicht „Prüfen & Exportieren“.
- Zeichen-/Importwerkzeuge einklappbar; nach Übernahme des Umrisses werden die Flugparameter sichtbar.
- Geoman-Eckpunkte beziehungsweise Kreisgriffe standardmäßig editierbar; Sperren weiterhin möglich.
- Automatische Vorschau mit 650 ms Verzögerung nach Änderungen. Neue Klasse `DmLivePreview` in `public/planner-live.js`: jeweils eine Anfrage, Änderungen werden zusammengefasst, veraltete Antworten verworfen.
- Karte, Zoom und gewählte 3D-/Profilansicht bleiben bei Aktualisierung erhalten. Vorherige Route während Neuberechnung abgeblendet; Export/Speichern bis zur aktuellen gültigen Vorschau gesperrt.
- Status mit Fotozahl, Strecke und Höhen; manueller Knopf „Vorschau aktualisieren“ als erneuter Versuch.
- Korrekturen beim Abbrechen einer Zeichnung, Startpunktsetzen, Laden/neuer Planung und Synchronisieren der Halbkugel-Höhe mit dem Slider.
- Node-Regressionstest für Anfragensteuerung und CI-Schritt ergänzt; PLANNER.md aktualisiert.

## Tatsächlich geprüft

Auf isolierter synthetischer PHP-Testinstallation, nicht im Produktivarchiv:

- JavaScript-Syntax und neuer Scheduler-Test erfolgreich (vor den letzten kleinen UI-Korrekturen).
- Im echten Browser Kreis gezeichnet: ohne Klick auf Berechnen entstand automatisch eine Helix (744 Fotos, 15–60 m).
- Obere Höhe 60 → 85 m: automatische Aktualisierung auf 1170 Fotos, 15–85 m, 3D-Ansicht blieb offen.
- Anschließend Abstand 35 m, Radius 55 m und obere Höhe 70 m geändert: automatisch 178 Fotos, 1,73 km, 15–70 m.
- Ungültige obere Höhe 10 m bei unterer Höhe 15 m: sichtbare Validierung „top: Wert zwischen 15 und 500 erforderlich.“
- Kein Gerätetest oder Flugtest. Keine produktiven Missionsdaten geändert.

## Vor Veröffentlichung noch nötig

1. Letzte kleine Änderungen erneut auf Syntax prüfen und Scheduler-Test ausführen.
2. Browser: nach ungültiger Höhe korrigieren und automatische Erholung/Exportfreigabe prüfen; Polygon-Eckpunkt verschieben/einfügen/löschen und automatische Route beobachten; Grid/Ausrichtung/Überlappung ändern; mehrfach schnell ändern; Umriss bleibt editierbar. Neues/Laden einer Planung prüfen.
3. Anfragenkonflikte insbesondere beim Planungswechsel und beim Startpunktsetzen kurz durchsehen. Abgebrochene Zeichnung muss wieder eine aktuelle Vorschau erzeugen.
4. Screenshot der fertigen gemeinsamen Ansicht sichern; keine privaten Daten veröffentlichen.
5. Relevante API-/Planner-Regressionen und CI ausführen. Eigenen PR erstellen, erst nach grünen Checks zusammenführen und deployen. Aktuelle main vorher prüfen.
6. Produktive Release-ID und ausgelieferte Assets prüfen. Falls PHP OPcache noch alte HTML-Dateien liefert: vorhandenen lokalen Helper `work/refresh-preview-cache.py` verwenden; dabei keine Zugangsdaten ausgeben.

## Lokale Hilfsmittel für die Fortsetzung

- `work/start-poi-test.py`: neue isolierte synthetische Installation samt Loopback-Tunnel erstellen; Zugang nur aus `.local/preview-test-access.json` lesen, nicht in Chat/Git dokumentieren.
- `work/sync-poi-test.py`: öffentliche Dateien aus diesem Worktree in Testinstallation aktualisieren.
- `work/remote.py`: bestehende Serververbindung. PHP und Node waren lokal nicht verfügbar, Tests liefen remote.
- GitHub CLI: `work/github-cli/bin/gh` vom Hauptordner aus.
- SSH-Fetch scheiterte am 1Password-Agenten; öffentliches HTTPS-Fetch funktioniert. Für Push bestehenden gh-Credential-Helper nutzen, niemals Token ausgeben.
- Testserver/Tunnel werden für die Pause beendet. Nach Neustart neu starten; alte Browserbindung nicht voraussetzen.

## Weitere Anforderungen bleiben erhalten

Grid, Helix und Fassadenflug, QGIS-/OSM-Umrisse, Überlappung und KMZ-Export sowie bestehende DEM-Geländeanpassung. DEM ist ein Rastermodell und keine Hindernisprüfung; An-/Rückflug bleibt separat zu prüfen. Diese Pause ist kein Abschluss der Gesamtentwicklung.
