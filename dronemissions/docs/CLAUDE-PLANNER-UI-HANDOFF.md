# Übergabe an Claude · Missionsplaner-Oberfläche

Stand: 8. November 2026. Auftrag von Florian: ausschließlich den Bereich **Mission planen** aufräumen, kompakter und intuitiver machen; danach zur Prüfung und Veröffentlichung an Codex zurückgeben.

## Arbeitsbasis und Umfang

Repository: https://github.com/studiobaff/dronemissions

Aktueller geprüfter Produktionsstand: `main`, Commit `e9c63cc525d650c0b0f255a8510d2fed4a3357c3` (PR #31). Generator 0.5.2. Vor Arbeitsbeginn aktuellen `main` holen und einen eigenen `claude/...`-Branch davon erstellen. Keine alte UI-Branch-Version über den neuen Stand kopieren. Dieser Dokumentationsbranch enthält nur die Übergabe.

Nur Planerdialog einschließlich Planen, Umriss, Flugparameter, Karten-/3D-/Höhenprofilansicht und Prüfen/Exportieren ändern. **Nicht** Bibliothek, Freigaben, Benutzerverwaltung, Bridge, Geräteübertragung oder Deployment umbauen. Die offenen Bridge-PRs #15/#18 gehören nicht zu diesem Auftrag. Keine Änderung an Fluggeometrie, Höhen-/FOV-Berechnung, Sicherheitsprüfungen, Exportaktionen oder gespeicherten Datenformaten als beiläufige UI-Korrektur.

## Gestaltungsreferenz: Litchi Hub v2

Florian wünscht ausdrücklich Litchi Hub als Vorbild für die Bedienung: https://hub.flylitchi.com/ . Bitte die aktuelle Oberfläche selbst ansehen; kein pixelgenauer Nachbau und keine fremden Assets übernehmen. Die offizielle Hub-Seite beschreibt unter anderem ein größenveränderliches Einstellungsfeld, Marker-Tooltips und Wegpunktnavigation. Die folgenden Anforderungen sind unsere Produktvorgabe, keine Behauptung über sämtliche Litchi-Funktionen.

- Große Karte als Hauptarbeitsfläche; Werkzeuge nehmen wenig Raum ein.
- Schmale obere Werkzeugleiste mit Flugart, Kamera und Foto/Video. Kompakte verständliche Icons mit Tooltip/zugänglichem Namen; keine Reihen riesiger Knöpfe.
- Wichtige Slider über der Karte: Höhe, Ausrichtung, Foto-/Bahnenabstand bzw. zur Flugart passende FOV-Parameter. Zahlenfelder direkt daneben. Einheit und Höhenbezug immer eindeutig.
- Kontextbezogene, ein-/ausklappbare und möglichst größenveränderliche Seitenleiste. Relevante Einstellungen erscheinen bei passendem Flugmuster; seltene Details unter „Erweitert“.
- Klare Gliederung: Planung/Projekt, Aufnahmen/Kamera, Gelände/Start, Erkundungsflug-Höhenreferenz. Kein verschachteltes Durcheinander aus Hinweisen, Feldern und Aktionen.
- Zweizeilige kompakte Ergebnisleiste an der Karte: Strecke/Zeit/Foto- oder Wegpunktzahl sowie Abstände/Überdeckung. Lange Erläuterungen in aufklappbare Details; relevante Fehlermeldungen bleiben sichtbar.
- Karte, 3D und Höhenprofil gut erreichbar. Kartenwerkzeuge für Polygon/Linie/Kreis, Bearbeiten, Undo und Löschen deutlich getrennt von Ansicht und Export.
- Speichern und Prüfen/Exportieren eindeutig; Schließen jederzeit erreichbar. Kein globaler Scrollweg, der Werkzeugleiste oder Schließen verschwinden lässt. Innenbereiche dürfen gezielt scrollen.
- Bei 1280×720 und 1440×900 ohne Überlagerungen nutzbar; iPad quer und schmales Browserfenster ebenfalls prüfen. Bedienelemente kompakt, aber für Touch weiter bedienbar. Keine abgeschnittenen Dropdowns, Werte, Tooltips oder Texte.

## Bestehendes Verhalten unbedingt erhalten

1. Automatische Vorschau nach Parameter-/Umrissänderung; serialisierte Berechnung, veraltete Antworten verwerfen. Export/Speichern bei veralteter oder ungültiger Vorschau sperren. Umriss bleibt bearbeitbar: ziehen, Zwischenpunkt ergänzen, Ecke entfernen, Undo.
2. Grid, Kreuzraster, Linie, Korridor, Kreis, Helix/Doppelhelix, POI-Polygon, Fassade. Helix-Halbkugel mit Nadir; Doppelhelix auf-/abwärts. Bestehende Zylinderentwürfe weiter laden.
3. Foto-/Bahnenabstand in Metern, Überlappungsmodus und Helix-FOV-Modus; Verketten, ±1°, längste Kante und +90°. Nominale Überdeckung nicht als nachgewiesene 3D-Abdeckung bezeichnen.
4. Foto/Video-Umschaltung: Video-Grid nur Bahnanfang/-ende, außer nötigen Geländestützpunkten. Fotoabstand/Längsüberlappung dort ausblenden. Kurvenstützpunkte der Helix bleiben. Video zeigt Wegpunkte statt Fotos; keine Foto-GSD als Videoauflösung ausgeben. Zusatzpause nur erweitert, standardmäßig 0.
5. Startort nur zur Wahl der Routenreihenfolge ist **nicht** der tatsächliche Startpunkt/Höhennullpunkt für Gelände. Beide Rollen sichtbar auseinanderhalten.
6. Terrain-Folgen mit DEM, POI-AGL/Offset, Footprint, Projektkarten/Referenzumrisse und Höhenprofil. Gelände-Kalotte funktioniert inzwischen über Z-Anpassung; alte pauschale Sperrmeldung nicht zurückbringen. Starres Kippen ist nicht implementiert.
7. „Höhenpunkte aus Erkundungsflug“: lokale DJI-KMZ oder Archivmission mit Projektpfad wählen. Neueste KMZ-Version als feste Referenz in Entwurf übernehmen; Original bleibt unverändert. Punkte auswählen, Startbezug explizit bestätigen oder bekannten Versatz angeben, Sicherheitsabstand einstellen, Mindesthöhe übernehmen/prüfen. Keine automatische Interpolation oder vermeintliches Hindernismodell.
8. Hover/Antippen der Referenzpunkte und gestrichelten Referenzsegmente zeigt Höhe und Höhenbezug. Segment zeigt beide Endhöhen, mehrzeilig. AGL nur bei verfügbarer Bodenreferenz; aus KMZ-Flughöhe allein kein AGL ableiten. Geplante DEM-Punkte zeigen „ca. … m AGL (über DEM)“; sonst relativ Start/AGL unbekannt.
9. Entwurf speichern/wiederöffnen, Projektzuordnung, Archivieren, KMZ/Abschnitts-ZIP, Geräteprofil, Rechte und Versionskonflikte vollständig erhalten. Höhenreferenz und Aufnahmeart müssen weiter persistieren.

## KMZ bearbeiten: gesonderter Folgeauftrag

Eigene gespeicherte Planungsentwürfe sind editierbar. Ein allgemeiner Editor für beliebige importierte DJI-KMZ ist **noch nicht umgesetzt**. Florian möchte künftig wie in Litchi einzelne/mehrere Wegpunkte auswählen, Position/Höhe/Geschwindigkeit/POI/Kameraaktionen bearbeiten und das Ergebnis als **neue Missionsversion** ablegen, ohne das Original zu überschreiben.

Beim UI-Entwurf eine spätere kontextbezogene Wegpunkt-Seitenleiste mitdenken. Jetzt keine funktionslosen Editor-Schaltflächen und keinen scheinbar fertigen KMZ-Importeditor hinzufügen. Das wird separat implementiert und mit Roundtrip-Erhalt von Aktionen, POIs, Indexverweisen, Höhenbezügen und Geräteprofilen geprüft. Litchi-Projektdatei, Kartenreferenz-KMZ und ausführbare DJI-Waypoint-KMZ bleiben unterschiedliche Dateitypen.

## Einstieg in den Code

- `dronemissions/public/planner.js`: Dialog-Markup, Zustände, Ereignisse, Leaflet-/Geoman-Bearbeitung, Vorschau und Höhenreferenz-UI. Dynamisch erzeugte IDs und Eventbindungen beim Umbau erhalten oder vollständig nachführen.
- `dronemissions/public/style.css`: Planer-Stile; Änderungen unter Planer-Selektoren kapseln, Archiv nicht global verändern.
- `dronemissions/public/planner-live.js`: Vorschau-Scheduler, fachliches Verhalten erhalten.
- `planner-core.php`, `planner-terrain.php`, `planner-heights.php`, `planner.php` im selben Verzeichnis: Berechnung, Gelände, Höhenimport und API. Für diesen UI-Auftrag normalerweise unverändert.
- `dronemissions/docs/PLANNER.md`, `UPDATE.md`, `PLANNER-NEXT.md`: Funktion, Grenzen und offene Arbeiten. Historische UPDATE-Abschnitte beschreiben alte Stände; neueste Abschnitte und Code haben Vorrang.

## Abnahme und Rückgabe an Codex

Mit synthetischen Daten testen, keine privaten Missionen, Schlüssel oder Konfiguration ins öffentliche Repo aufnehmen. Keine Produktion für Tests verändern.

- `node --check dronemissions/public/planner.js`
- `node dronemissions/tests/planner-live.cjs`
- `php dronemissions/tests/planner.php`
- Planner-API-Lebenszyklus auf isolierter Testinstallation wie in `.github/workflows/web-deploy.yml` und alle GitHub-Checks.
- Browser: Grid zeichnen, Ecke ziehen/einfügen/löschen/Undo; Parameter verändern und automatische Vorschau prüfen; Helix/Doppelhelix; Foto→Video; Entwurf speichern/laden; Höhenreferenz aus Archiv mit Punkt-/Linientooltip; Offset/Mindesthöhe; Karten/3D/Profil; ungültige Eingabe sperrt Export und erholt sich nach Korrektur.
- Screenshots mit synthetischen Daten: Grid, Helix/FOV, Video, Höhenreferenz und Prüfen/Exportieren; mindestens Desktop 1280×720 und iPad quer. Keine Browser-Konsolenfehler. Screenshots lesbar, ohne Layoutüberlagerung.

Fertigen Branch pushen, eigenen PR nach `main` öffnen und **zurückgeben, nicht selbst mergen/deployen**. Codex prüft und veröffentlicht danach. Kein manuelles rsync; Produktion wird durch geprüften Merge nach main automatisch aktualisiert.

Rückgabeformat:

```text
Branch:
Commit (vollständig):
PR:
Geänderte Dateien:
UI-Änderungen:
Unveränderte fachliche Logik / etwaige bewusst vorgeschlagene Abweichungen:
Tests (Befehl + Ergebnis):
Browsergrößen + Screenshots:
Bekannte Einschränkungen / nicht geprüft:
Was Codex als Nächstes tun soll:
```

README/PLANNER/UPDATE passend zur tatsächlich gelieferten Bedienung aktualisieren. Keine Flug-/Geräteprüfung behaupten: Die neue Planergeneration und insbesondere Video haben weiterhin offene reale Geräte-/Flugtests. Bridge muss für reine Web-UI-Änderungen nicht neu gebaut werden.
