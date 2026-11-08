# Arbeitsstand und nächste Übergabe

Stand: 8. November 2026. Diese Übersicht unterscheidet ausgelieferte Funktionen, gepushten Quellcode und noch nicht veröffentlichte Arbeit.

## Ausgeliefert und geprüft

- Mac-App und privater Webarchiv-Download: **dronemissions-bridge 0.6.1**, Quellstand `55bbdaa`, 109 isolierte Tests. Einstellungen und Schlüsselbund-Kennungen bleiben erhalten.
- Auf dem echten iPad wurde der komplette Ablauf über die App bestätigt: eine Mission mit zwölf Wegpunkten ins Webarchiv sichern, KMZ-Prüfsumme vergleichen, lokal entfernen und als neue Mission aus dem Archiv zurückübertragen. Der Nutzer bestätigte das Ergebnis in DJI Fly. Archivversion und Originaldatei blieben unverändert. Details: [BRIDGE.md](BRIDGE.md).
- Web-Veröffentlichungen erfolgen aus geschütztem `main` über Pull Request, erfolgreiche Checks und GitHub Actions. Ein Push auf Claudes Arbeitsbranch veröffentlicht nicht automatisch.

## Claude: gepusht, separat zu integrieren

Branch: `claude/drone-missions-ui-handoff-4nsj6e`, letzter überprüfter Stand **`c185a2a`**.

- `378ab87`: Wegpunktmarker im Vorschaueditor, weltweite Kartenquellen, Kartenleiste, Referer-Korrektur für OSM und Navigationsanker.
- `d1513bc`: eigene Kachelquellen mit API-Schlüssel, WMTS-Import, Vektor-Upload und zusätzliche Geozonenkategorie.
- `c185a2a`: gespeicherte Ebenenreihenfolge. Vektor-Ebenen liegen über Geozonen und unter Missionsrouten/Wegpunkten. Weiter unten gelistete Overlays liegen weiter oben auf der Karte. Ab der 19. Vektor-Ebene teilen sich weitere Ebenen eine Stapelstufe.

Die Kartenebenen dieses Stands gelten installationsweit. Claudes Testbericht nennt erfolgreiche Integrations- und Browserprüfungen; das ersetzt nicht die erneute Prüfung des zusammengeführten Release-Stands. Diese Dokumentationsänderung veröffentlicht die drei Codeänderungen noch nicht.

## Noch fertigzustellen

1. **Projektbezogene Kartenreferenzen:** vorhandene Kartenebenen um Projektzuordnung ergänzen, statt ein zweites Ebenensystem einzubauen. Eine My-Maps-KMZ mit Linie ist eine Kartenreferenz und keine ausführbare DJI-Mission. Originaldatei erhalten, Projektwechsel und Unterordnerverhalten prüfen. Kundenrechte ausdrücklich prüfen; private Linien nicht automatisch freigeben. Eine reine NetworkLink-KMZ enthält keine lokale Geometrie und wird nicht automatisch aus dem Internet nachgeladen.
2. **POIs in beiden Vorschauen:** Bridge und Webarchiv sollen vorhandene aktive WPML-POIs unterscheiden und beschriften. `waypointPoiPoint` verwendet Breite, Länge, Höhe; inaktive Platzhalter und reine Kameraausrichtungen erzeugen keine erfundenen POIs. Mehrfache Verweise zusammenfassen und Bildausschnitt um POIs erweitern. Ein Höhenbezug darf nicht geraten werden. Lokale Änderungen sind begonnen, aber noch nicht als getestete Version veröffentlicht.
3. Anschließend Parser-, Rechte-, Darstellungs- und Regressionstests ausführen; Web-Code per PR nach `main`, Bridge separat bauen, signieren, installieren und Download mit Prüfsumme aktualisieren. Vor neuen Geräte-Schreibtests DJI Fly schließen lassen.

## Zusammenarbeit und Erhalt bestehender Arbeit

- Claudes Branch nicht überschreiben oder zurücksetzen. Integration auf einem eigenen `codex/`-Branch, Konflikte gezielt lösen.
- **PR #15** (`codex/ipad-mission-removal` → Claude) enthält die getestete iPad-Aufräumfunktion und den ADB-Verpackungsfix; beides muss in jedem neuen Bridge-Build erhalten bleiben.
- Ein lokaler Integrationsversuch im Worktree `work/roundtrip-device-proof` ist bei `HANDOFF.md` unterbrochen. Dort liegen zusätzlich uncommittete POI-Änderungen und ein Sicherungs-Stash. Vor Fortsetzung Status prüfen, keine pauschalen Reset-/Clean-Befehle verwenden.
- Private Missionsdateien, Gerätekennungen, echte Screenshots, Zugangsschlüssel, Datenbanken und Journale bleiben außerhalb von GitHub. Öffentliche Beispiele müssen synthetisch sein.

Weitere Anleitungen: [UPDATE.md](UPDATE.md), [PREVIEWS.md](PREVIEWS.md), [BRIDGE.md](BRIDGE.md).
