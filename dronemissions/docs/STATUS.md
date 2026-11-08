# Arbeitsstand und nächste Übergabe

Stand: 8. November 2026. Diese Übersicht unterscheidet ausgelieferte Funktionen, gepushten Quellcode und noch nicht veröffentlichte Arbeit.

## Ausgeliefert und geprüft

- Mac-App und privater Webarchiv-Download: **dronemissions-bridge 0.6.2**, Quellstand `618aa5a`, 113 isolierte Tests. Einstellungen und Schlüsselbund-Kennungen bleiben erhalten.
- Auf dem echten iPad wurde der komplette Ablauf über die App bestätigt: eine Mission mit zwölf Wegpunkten ins Webarchiv sichern, KMZ-Prüfsumme vergleichen, lokal entfernen und als neue Mission aus dem Archiv zurückübertragen. Der Nutzer bestätigte das Ergebnis in DJI Fly. Archivversion und Originaldatei blieben unverändert. Details: [BRIDGE.md](BRIDGE.md).
- Web-Veröffentlichungen erfolgen aus geschütztem `main` über Pull Request, erfolgreiche Checks und GitHub Actions. Ein Push auf Claudes Arbeitsbranch veröffentlicht nicht automatisch.

## Claude: gepusht, separat zu integrieren

Branch: `claude/drone-missions-ui-handoff-4nsj6e`, letzter überprüfter Stand **`c185a2a`**.

- `378ab87`: Wegpunktmarker im Vorschaueditor, weltweite Kartenquellen, Kartenleiste, Referer-Korrektur für OSM und Navigationsanker.
- `d1513bc`: eigene Kachelquellen mit API-Schlüssel, WMTS-Import, Vektor-Upload und zusätzliche Geozonenkategorie.
- `c185a2a`: gespeicherte Ebenenreihenfolge. Vektor-Ebenen liegen über Geozonen und unter Missionsrouten/Wegpunkten. Weiter unten gelistete Overlays liegen weiter oben auf der Karte. Ab der 19. Vektor-Ebene teilen sich weitere Ebenen eine Stapelstufe.

Die Kartenebenen dieses Stands gelten installationsweit. Claudes Testbericht nennt erfolgreiche Integrations- und Browserprüfungen; das ersetzt nicht die erneute Prüfung des zusammengeführten Release-Stands. Die drei Codeänderungen wurden mit Projektkarten und POIs über PR #19 in `main` übernommen und per GitHub Actions veröffentlicht.

## Projektkarten und POIs: veröffentlicht

- Projektkarten verwenden Claudes bestehende Vektor-Ebenen mit einer Projektzuordnung. Im Projekt öffnet „Projektkarte …“ den Upload mit vorausgewähltem Ordner. Originaldatei mit Prüfsumme bleibt privat erhalten. Unterordner erben die Referenz; andere Projekte zeigen sie nicht. Kundenlinks können projektbezogene Vektoren weder sehen noch herunterladen. Details: [PROJECT-MAPS.md](PROJECT-MAPS.md).
- Aktive WPML-POIs sind in der Web-Missionskarte, SVG-Vorschau sowie im 3D-/Karteneditor sichtbar. Alte KMZs werden bei Bedarf ohne neue Version nachgelesen. Bridge **0.6.2**, Quellstand `618aa5a`, enthält dieselbe POI-Auswertung für 3D und Luftbild. Bestehende eigene Fotos/Archivbilder bleiben unverändert. POIs zeigen die Lage; der Höhenbezug wird nicht geraten.
- Prüfung: Archiv-Integration, Vorschaugeschichte und neue API-Rechte-/Projekt-/POI-Tests auf isolierter synthetischer Installation; Browserprüfung von Editor, Projektvorwahl, automatischer Referenzanzeige und Ausblendung beim Projektwechsel. Bridge: **113 isolierte Tests** einschließlich 3D- und Luftbildrendering mit Kachel-Fakes.
- Veröffentlichung: PR #19 ist nach erfolgreichen Checks gemerged und live. Bridge 0.6.2 wurde gebaut, installiert, gestartet und visuell geprüft. Mac-ZIP und Anleitung sind im authentifizierten Webarchiv aktualisiert; der vollständige Download ist per SHA-256 geprüft. Neue Übertragungs-/Ersetzen-Gerätetests bleiben getrennt.

## Zusammenarbeit und Erhalt bestehender Arbeit

- Claudes Branch nicht überschreiben oder zurücksetzen. Integration auf einem eigenen `codex/`-Branch, Konflikte gezielt lösen.
- **PR #15** (`codex/ipad-mission-removal` → Claude) enthält die getestete iPad-Aufräumfunktion und den ADB-Verpackungsfix; beides muss in jedem neuen Bridge-Build erhalten bleiben.
- Die Kartenänderungen werden auf `codex/poi-project-maps` integriert; der frühere Dokumentationskonflikt ist gelöst. Bridge-POIs liegen auf `codex/poi-preview`. Sicherungs-Stashes und private Testdaten nicht ungeprüft löschen.
- Private Missionsdateien, Gerätekennungen, echte Screenshots, Zugangsschlüssel, Datenbanken und Journale bleiben außerhalb von GitHub. Öffentliche Beispiele müssen synthetisch sein.

Weitere Anleitungen: [UPDATE.md](UPDATE.md), [PREVIEWS.md](PREVIEWS.md), [BRIDGE.md](BRIDGE.md).

## Web-Missionsplaner · erster Stand

Branch `codex/web-mission-planner`: QGIS-/Projektreferenzen, Zeichnen und OSM-Gebäude; Grid, Kreis, Helix/Doppelhelix, POI-Polygon und Fassadenbahnen; sechs DJI-Hauptkameraprofile plus eigene Eingaben; nominelle Überlappung, Fotoaufteilung und 3D-Prüfung. Planungen mit Konfliktschutz, referenzbasiertes WPML/KMZ und wiederholsichere Archivierung im selben Projekt. Rechen-/API-/Browser-Rundlauf geprüft, 496-Foto-ZIP vom Bridge-Parser gelesen. Kein neuer Geräte-/Flugtest und keine automatische DEM-/AGL-Anpassung. Vollständige Bedienung und Grenzen: [PLANNER.md](PLANNER.md).

### Webplaner 0.2 · Geländeanpassung und Zeicheneditor

Leaflet-Geoman ersetzt die manuellen Zeichenmarker. Expliziter Bearbeitungsmodus, Zwischenpunkte, Löschen/Rücknahme, Slider und weitere Flugparameter. Grid/Kreis/Helix: DEM-Höhen relativ zum gewählten Startpunkt, Navigationspunkte ohne Fotos, Höhenprofil und private Snapshots. Details und Genauigkeitsgrenzen: [PLANNER.md](PLANNER.md). Kein Geräte-/Flugtest der neu erzeugten Exporte.
