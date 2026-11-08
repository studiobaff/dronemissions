# Rückgabe an Codex · Planer-Oberfläche nach Litchi-Vorbild

Stand: 8. November 2026. Antwort auf `CLAUDE-PLANNER-UI-HANDOFF.md` einschließlich Zusatz „Litchi-Editor als gemeinsames Bedienvorbild“. Nur die Bedienung von **Mission planen** wurde geändert.

```text
Branch: claude/planner-ui-litchi
Commit (vollständig): siehe PR-Kopf; Umbau 8b0b194e75e23b9fc9360e4fbaa6a071ddb6cf11,
  danach Merge von main (KMZ-Editor, PR #32) und diese Rückgabedatei
PR: https://github.com/studiobaff/dronemissions/pull/33
Geänderte Dateien: public/planner.js (Markup und Zusammenbau, alle IDs und
  Ereignisbindungen erhalten; Zoom unten rechts), Planer-Regeln am Ende von
  public/style.css (gekapselt unter .mission-planner), docs/PLANNER.md,
  docs/UPDATE.md, neu docs/PLANNER-UI-DESIGN.md, docs/screenshots/planner/*.png
UI-Änderungen: Kopf mit Schrittwahl „Planen · Prüfen & Exportieren“ als Pillen,
  Schließen immer erreichbar, kein globaler Scrollweg. Obere Werkzeugleiste
  Flugart, Kamera, Aufnahme, Abstände; rechts Kreuzraster, Längste Kante, +90°.
  Slider-Leiste mit Zahlenfeldern, Ausrichtung ±1°, Abstände verketten.
  Seitenleiste 310 px, größenveränderbar und ausblendbar, fünf Abschnitte:
  Planung & Projekt · Aufnahme & Kamera (Erweitert: Kameramodell, Zusatzpause) ·
  Muster & Objekt · Gelände & Start (tatsächlicher Startpunkt getrennt vom
  Startort für die Reihenfolge) · Erkundungsflug · Höhenreferenz; Zahlenfelder
  mit −/+ Schrittknöpfen. Karte füllt die Fläche: Umriss-Werkzeuge als Icon-Gruppe
  links oben (Fertig/Abbrechen nur beim Zeichnen, Ecken bearbeiten als gedrückter
  Zustand), Ansichtsschalter rechts oben (Karte, 3D, Profil, Footprint,
  Seitenleiste; in 3D Drehen/Neigen), zweizeilige Ergebnis-Pille unten in der
  Karte. Prüfseite in der Seitenleiste bei sichtbarer Karte. Schmale Fenster:
  Karte oben, Seitenleiste darunter, Werkzeuge unten an der Karte.
Unveränderte fachliche Logik / bewusste Abweichungen: Berechnung, API, Export,
  Datenformate unverändert. Nicht umgesetzt: Redo (nur mit Zustandstests),
  Punktnavigation für generierte Punkte, simulierte Telemetrie, funktionslose
  Schalter aus dem Vorbild.
Tests (Befehl + Ergebnis):
  find dronemissions/public -name '*.js' | xargs -n1 node --check → ok
  find dronemissions/public deploy -name '*.php' | xargs -n1 php -l → ok
  node dronemissions/tests/planner-live.cjs → PASS
  php dronemissions/tests/planner.php → PASS · php dronemissions/tests/parser.php → PASS
  python3 -m unittest discover -s deploy/tests → OK
  Frische Loopback-Installation (setup-preview-test.php, php -S): integration.py,
  previews.py, project-maps-pois.py, planner-api.py → PASS, nach dem Merge erneut
  Browser (Playwright, synthetische Daten, Kacheln gestubbt): Grid zeichnen mit
  Ecken/Undo, automatische Vorschau, Helix per Kreis (FOV), Foto→Video, 3D/Profil,
  ungültige Höhe sperrt Export und erholt sich, Entwurf speichern/laden,
  Höhenreferenz aus Archivmission mit Tooltip auf Punkt und gestricheltem Segment,
  Geländemodus → ohne Konsolenfehler außer erwarteten 400-Antworten
  GitHub-Check „check“ auf dem PR → grün
Browsergrößen + Screenshots: 1280×720, 1440×900, iPad quer 1180×820, 430×860
  ohne Überlagerungen; docs/screenshots/planner/ (inkl. vorher-1280-grid.png)
Bekannte Einschränkungen / nicht geprüft: kein DJI-Fly-Geräte- oder Flugtest;
  DEM nur gegen gestubbte Antworten; Litchi Hub nur als Startseite und über die
  gelieferten Screenshots gesehen, kein Nachbau; ab dem 19. Abschnitt teilen
  sich keine Elemente eine Stufe (nicht betroffen), Redo offen.
Was Codex als Nächstes tun soll: PR #33 prüfen, KMZ-Editor nach
  docs/PLANNER-UI-DESIGN.md angleichen, mergen und veröffentlichen.
```

## Für Codex relevante Stellen in `planner.js`

- Template am Anfang (`dlg.innerHTML`), danach der Zusammenbau: Slider-Leiste (`.pl-flight-controls`), obere Werkzeuge (`.pl-top-tools`), Stepper (`.pl-stepper`), Startort-Panel, Footprint- und Prüfen-Knopf. `setStage()` blendet in Schritt 3 Werkzeugleisten und Umriss-Gruppe aus und setzt `pl-stage-review`.
- `editState()` hält den Zustand von „Ecken bearbeiten“ (`aria-pressed`, Tooltip). `syncViewButtons()` markiert die aktive Ansicht.
- Keine neuen API-Aufrufe; `input()`, `showResult()`, `typeFields()` und die Höhenreferenz-Funktionen sind unverändert.
