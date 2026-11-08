# Planer-Oberfläche · Gestaltungsregeln für den Abgleich mit dem KMZ-Editor

Stand: 8. November 2026, Branch `claude/planner-ui-litchi`. Vorbild für die Bedienung ist Litchi Hub v2 (große Karte, kompakte Werkzeuggruppen an der Karte, kontextbezogene Seitenleiste); es wurden keine Litchi-Assets oder Texte übernommen. Alle Regeln liegen gekapselt unter `.mission-planner` am Ende von `public/style.css`; die Archiv-Oberfläche ist unverändert. Markup und Zusammenbau stehen in `public/planner.js`.

## Aufbau des Dialogs

| Bereich | Element | Maße und Verhalten |
| --- | --- | --- |
| Dialog | `dialog.mission-planner` | 98 vw × 97 dvh, Grundschrift 13 px, Flex-Spalte: Kopf · Körper · Fuß. Kein globaler Scrollweg; nur die Seitenleiste scrollt. |
| Kopf | `.pl-head` | Titel 17 px, Badge „Geräteprüfung offen“, Schrittwahl `.pl-steps` als Pillenpaar (Planen · Prüfen & Exportieren) mittig, Schließen rechts (`#pl-close`, Esc). |
| Obere Werkzeugleiste | `.pl-main-controls` | Eine Zeile: Flugart, Kamera, Aufnahme (Foto/Video), Abstände als Selects (min 150 px, max 260 px); rechts `.pl-top-tools` mit Kreuzraster-Checkbox, „Längste Kante“ und „+90°“ (Icon + Text, nur bei Grid sichtbar). |
| Slider-Leiste | `.pl-flight-controls` | Grau unterlegt (`--surface-2`), Radius 8 px, Raster mit 6 Spalten (≤1100 px: 4, ≤700 px: 2). Je Feld: Beschriftung 11 px fett, Slider 20 px hoch, Zahlenfeld 60 px breit und 26 px hoch. Ausrichtung mit ±1°-Knöpfen (`.pl-degree-step`, 22 px). Welche Felder erscheinen, bestimmt die Flugart (`data-pl-types`). |
| Seitenleiste | `aside.pl-options` | 310 px breit (min 250, max 560), per `resize: horizontal` am rechten unteren Griff änderbar, scrollt intern, weißer Hintergrund, Rand `--line`, Radius 10 px. Knopf „Seitenleiste“ (`#pl-options-toggle`) blendet sie aus; die Karte nimmt dann die volle Breite. |
| Abschnitte | `details.pl-section` | Kopf 11 px, Versalien, Laufweite 0,08 em, Farbe `--ink-2`, Chevron rechts; Inhalt `.pl-section-body` mit 0,8 rem Seitenabstand. Reihenfolge: Planung & Projekt · Aufnahme & Kamera · Muster & Objekt · Gelände & Start · Erkundungsflug · Höhenreferenz. Seltene Felder unter „Erweitert“. |
| Zahlenfelder | `.pl-stepper` | Zahlenfeld mittig, links/rechts 26 px breite −/+ Knöpfe mit der Schrittweite des Feldes; Einheit steht in der Beschriftung. Slider darüber, wo ein Bereich sinnvoll ist. |
| Karte | `.pl-canvas` | Flex 1, Radius 12 px, Rand `--line`; Karte, 3D-Canvas und Höhenprofil füllen die Fläche absolut. Zoom unten rechts, Maßstab unten links. |
| Werkzeuggruppen auf der Karte | `.pl-tool-group` | Weiß (94 %), Blur 8 px, Rand `--line`, Radius 10 px, Schatten `--shadow`, Icons 18 px, Knöpfe 32 × 32 px. Links oben senkrecht `.pl-draw-tools`: Polygon, Linie, Kreis · Ecken bearbeiten (gedrückt = editierbar), Rückgängig, Umriss verwerfen; beim Zeichnen zusätzlich Fertig (dunkel) und Abbrechen. Rechts oben waagrecht `.pl-view-tools`: Karte, 3D, Höhenprofil (aktive Ansicht gedrückt), Footprint, Seitenleiste; in 3D zusätzlich Drehen/Neigen. |
| Ergebnisleiste | `#pl-live-status` | Pille unten mittig in der Karte: Zeile 1 Fotos/Wegpunkte · Strecke · Höhen; Zeile 2 Abstände/Überdeckung. Fehlertexte erscheinen dort und im Fuß (`#pl-status.error`). |
| Prüfseite | `.pl-review` | Ersetzt im Schritt „Prüfen & Exportieren“ die Seitenleisten-Abschnitte; Werkzeuggruppe Umriss wird ausgeblendet, Ansichtsschalter bleiben. Zusammenfassung als Schlüssel-Wert-Liste, Abschnittsliste, Geräteprofil, Knöpfe DJI-KMZ (primär), Archiv, Planungsdatei. |
| Fuß | `.dialog-foot` | Status links (eine Zeile, Fehler umbrechend), „Entwurf speichern“, „Vorschau“ (erneuter Versuch) und „Prüfen & Exportieren“ bzw. „Zurück zum Planen“ als primärer Knopf. |

## Farben und Zustände

- Auswahl/aktiv: `--ink` (dunkelgrün) mit weißem Text, sowohl für Schritt-Pillen als auch für gedrückte Icon-Knöpfe (`aria-pressed="true"`).
- Umriss orange `#e58a24`, Routenabschnitte in `ROUTE_COLORS`, Referenzflug gestrichelt `#b55326`, ausgewählte Referenzpunkte orange, ausgeschlossene grau, Startpunkt blau `#195acc`, Startort (nur Reihenfolge) blauer Ring `#245da0`, Footprint violett `#8557c7`.
- Veraltete Vorschau: `.pl-stale` dimmt Route und 3D auf 50 %; Export und Speichern sind gesperrt, bis eine gültige Vorschau vorliegt.

## Schmale Fenster (≤ 850 px, iPad hochkant, Telefon)

Karte oben, Seitenleiste darunter (42 % Höhe, `resize: vertical`), Schrittwahl in eigener Zeile, obere Werkzeugleiste als 2-Spalten-Raster, Umriss-Werkzeuge als Zeile oben links, Ansichtsschalter unten rechts über dem Zoom, Ergebnisleiste über die ganze Breite. iPad quer (1180 × 820) nutzt die Desktop-Anordnung.

## Für den KMZ-Editor übernehmen

Gleiche Dialogmaße, Kopf mit Schrittwahl, Werkzeuggruppen (`.pl-tool-group`, 32-px-Knöpfe, 18-px-Icons), Seitenleistenbreite 310 px mit Abschnitten im Stil `.pl-section`, Stepper `.pl-stepper`, Ergebnis-Pille und die Zustandsfarbe `--ink`. Undo bleibt ein echter Knopf mit Funktion; Redo nur mit Zustandstests. Keine simulierte Telemetrie.
