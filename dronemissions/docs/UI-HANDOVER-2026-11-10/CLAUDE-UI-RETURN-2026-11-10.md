# Rückgabe an Codex · UI-Handover 10. November 2026

Branch `claude/ui-handover-2026-11-10`, Basis `codex/ui-handover-2026-11-10` (= main `a327f1f` plus Handover-Doku). Nicht gemergt, nicht deployt. Codex übernimmt Review, Regressionen und Veröffentlichung.

Auftrag aus `BRIEFING.txt`: kompakte Liste mit Checkbox rechts und Griff links, klarere Akzente, Deutsch/Englisch/Ukrainisch in Oberfläche und PDF, feinere Linien und Marker, Antrag-PDF mit Legende, Quellen und Punktetabelle, konfigurierbares Branding. Vorher-Bilder liegen unter `beispiele/`, Nachher-Bilder und drei gerenderte PDFs unter `ergebnis/`.

## Geänderte Dateien

| Datei | Änderung |
| --- | --- |
| `public/i18n.js` (neu) | Wörterbuch de/en/uk, `t(key, vars)`, `t.n(key, count)` mit ukrainischer Mehrzahlregel (1 · 2–4 · 5+), `t.locale()`, Übersetzung statischer Texte über `data-i18n`, `data-i18n-title`, `data-i18n-placeholder`, `data-i18n-aria`; Sprache aus `?lang=`, `localStorage dm-lang`, Browser; Ereignis `dm-language`. |
| `public/view.html` | Sprachhooks in Seitenleiste, Kopf, Statistik, Werkzeugleiste, Auswahl, Freigabekarte, Leerzustand, Fuß; Sprachwahl unten in der Seitenleiste (`#language`) und unter Einstellungen (`#settings-language`); neue Sprite-Icons `i-list`, `i-grip`; Script-Einbindung `i18n.js`, `permit-font.js`. |
| `public/app.js` | Dynamische Shell-Texte über `t()`; kompakte Listenzeile neu (`missionListRow`): Griff · Position · Titel + Chips · Öffnen · Checkbox rechts, Touch-Knöpfe hoch/runter (`data-order-up/down`); Flugroute mit heller Kontur (5 px weiß .85 + 2,5 px Farbe) statt dunkler 6-px-Unterlage; Neuzeichnen beim Sprachwechsel. |
| `public/permit-map.js` | Alle Texte über `t()`; `dmPermitLabel` liest Ziffern nach „Pano“ auch mitten im Namen (`Pano010 Ostseite` → 010), sonst Ziffern am Ende, sonst Name; Marker in neuer Formsprache; Zuordnungslinie 4,5 px weiß .9 + 2 px `#243a4d`, Strich 6/7; `dmHighlightMission()` hebt die gewählte Mission hervor (Ring, nach vorn); Klick auf Marker wählt die Mission; Kartenlink trägt `lang`. PDF-Aufruf übergibt `{title, kind, subtitle, file}`. |
| `public/permit-font.js` (neu) | WOFF-Leser (zlib je Tabelle über `DecompressionStream`), cmap Format 4/12, hmtx-Breiten, TrueType-Subset mit Komponenten zusammengesetzter Glyphen, PDF-Objekte Type0/CIDFontType2/FontDescriptor/FontFile2 (Flate, wenn `CompressionStream` vorhanden) und ToUnicode. |
| `public/permit-pdf.js` | Neu aufgebaut: Canvas mit Markern der Oberfläche; PDF A4 quer, Kopf mit Logo (`favicon.png`), Wortmarke und Betreiber (Name aus Einstellungen, serverseitig im Kopf gerendert), Titel, Untertitel; Karte; Legende nur für vorhandene Elemente; Quellen (Kartengrundlage aus der Attribution, Schutzgebiete, Geozonen, Hinweis); ab Seite 2 Tabellen mit fester Spaltenbreite, Umbruch in der Zelle, wiederholter Kopfzeile, Seitenzahl; Dateiname je Sprache. Keine Status-, Bedien- oder Entwicklerhinweise. |
| `public/nature.js`, `public/zones.js` | Beschriftungen des Kartenpanels, der Naturschutz-Steuerung und der Statusmeldungen über `t()`; Verhalten unverändert (Autoload wie auf main). |
| `public/style.css` | Tokens `--select`, `--start`, `--capture`, `--link`; Block „Freigabekarte · Marker, Linien, kompakte Liste“ ersetzt die alten Marker-/Listenregeln; Wegpunkte weiß mit dunklem Rand; Kachel-Nummer rechts oben klein, Kachel-Checkbox darunter rechts. |
| `public/vendor/fonts/DejaVuSans.woff`, `DejaVu-LICENSE` (neu) | DejaVu Sans 2.37 unverändert im WOFF-Container (379 kB), Lizenz Bitstream Vera. |
| `deploy/package.py`, `deploy/receiver.php`, `deploy/tests/test_package.py` | Allowlisten um `vendor/fonts/DejaVu-LICENSE` erweitert (`.woff` war bereits erlaubt), Test ergänzt. |
| `docs/UPDATE.md` | Eintrag 10.11.2026. |

Nicht angefasst: `api.php`, `lib.php`, Datenbank, Freigaben, Planer, KMZ-Editor, Bridge. Keine API-Namen geändert, keine Schutzprüfungen entfernt. Naturschutz-Autoload bleibt wie auf main; die Rücknahme liegt getrennt auf `claude/nature-overlay-opt-in` (57d7f15).

## Gestaltungsregeln (für den Abgleich mit Kacheln, Planer und Editor)

- **Formsprache Karte.** Startplatz am Boden: weißer Kreis 34 px, Rand 2,5 px `--start` (#1f5fbf), „H“ 15 px fett. Aufnahmepunkt: Quadrat 30 px, Radius 8, Füllung `--capture` (#c4551c), weißes Symbol 18 px für Foto, Video, Panorama, Kugel. Kennung als eigenes Schild (Pille, 9,5 px, weiß, Rand `--line-2`, bei Aufnahme orange) mittig unter dem Marker, nie im Symbol. Wegpunkte: weiße Kreise 22 px, Rand 1,5 px `--ink`, Nummer 10 px. Auswahl: Ring 4 px in Marker-Farbe mit 30 % Deckung, Marker nach vorn.
- **Linien.** Zuordnung Startplatz → Aufnahmepunkt: gestrichelt 6/7, 2 px `#243a4d` auf 4,5 px Weiß. Flugroute: durchgezogen 2,5 px Routenfarbe auf 5 px Weiß, runde Enden. Beide lesbar auf Orthofoto; die Zuordnung ist dünner und gestrichelt, die Route breiter und durchgezogen.
- **Akzente.** Grün bleibt Marke und Routen; Blau (`--select`, `--start`) für Auswahl, Checkboxen und Startplatz; Orange (`--capture`) für Aufnahmepunkte. Schutzgebietsfarben bleiben fachlich (nature.js).
- **Kompakte Liste.** Raster `auto auto 1fr auto auto`: Griff 30 × 38 px (`--surface-2`, sechs Punkte), Position rechtsbündig tabellarisch, Titel 15 px/600 einzeilig mit Ellipse, darunter Chips (Projekt mit Ordner-Icon, Typ in `--accent-soft`, Archiv gedämpft), Öffnen als `btn-sm`, Checkbox 20 px rechts in 40-px-Feld. Zustände: Hover Rand `--line-2` + Schatten, Auswahl `--select-soft`, Drop-Ziel Umriss `--select`, Ziehen 45 %. Unter 700 px: Öffnen unter den Chips, Checkbox bleibt rechts. Bei groben Zeigern (Touch) erscheinen Hoch/Runter-Knöpfe neben dem Griff.
- **Kacheln.** Nummer rechts oben als Pille 12 px, Checkbox rechts darunter.
- **PDF.** A4 quer, Rand 36 pt. Kopf: Logo 22 pt, Wortmarke 13 pt („drone“ fett), rechts Betreiber; Titel 17 pt fett, Untertitel 9 pt grau, Trennlinie. Karte füllt die Breite, darunter Legende (zwei Spalten, 7,5 pt) und Quellen (6,8 pt). Tabellen: Kopfzeile hellgrau 8 pt fett, Zeilen 8 pt mit 0,4-pt-Linien, Spaltenbreiten fest, Umbruch in der Zelle, Kopfzeile auf Folgeseiten, Fußzeile mit Dokumentart, Erstellungszeit und „Seite n von m“. Fettschrift über Textmodus 2 (Kontur 3 % der Schriftgröße), eine Schriftdatei.

## Sprachen

- Umschalten über die Auswahl unten in der Seitenleiste oder unter Einstellungen; gespeichert je Browser (`dm-lang`), `?lang=de|en|uk` überschreibt, Kartenlinks übernehmen die aktive Sprache.
- Übersetzt: Seitenleiste, Kopf, Statistik, Werkzeugleiste, Auswahl, Ergebniszeile, Leerzustände, Fuß, kompakte Liste, Freigabekarte samt Zeilentabelle, Einzelmissionskarte, Kartenpanel (Karte & Zonen, Adresse, Hintergrund, Geozonen), Naturschutz-Steuerung und -Status, PDF vollständig.
- Noch deutsch: Dialoge für Upload, Missionsdetails, Ordner, Freigaben, Einstellungen (außer Sprachfeld), Planer, KMZ-Editor, Kartenebenen-Einstellungen, Toasts außerhalb der Freigabekarte. Die Schlüssel in `i18n.js` sind so angelegt, dass diese Bereiche nachgezogen werden können (`t()` in JS, `data-i18n` in HTML).
- Namen von Personen, Missionen, Projekten und Kennungen werden nie übersetzt. Ukrainischer Sprachcode: `uk`.
- Schrift im Browser: Systemschriften (Kyrillisch vorhanden). Schrift im PDF: DejaVu Sans eingebettet; `pdffonts` meldet `DejaVuSans CID TrueType Identity-H`, Subset.

## Prüfung

Alle Prüfungen auf diesem Branch, Stand des Commits:

- `php -l` für alle PHP-Dateien, `node --check` für alle JS-Dateien: fehlerfrei.
- `python3 -m unittest discover -s deploy/tests`: 5 Tests OK (neu: Font-Lizenz erlaubt, `.txt` abgelehnt). `deploy/package.py` baut das Release mit Schrift und Lizenz.
- `php deploy/tests/receiver.php`, `php tests/parser.php`, `php tests/planner.php`, `php tests/kmz-editor.php`, `node tests/zones.js`, `node tests/planner-live.cjs`: PASS.
- Frische Testinstallation (`tests/setup-preview-test.php`, PHP-Server auf 127.0.0.1:18764): `integration.py --allow-test-writes`, `previews.py`, `project-maps-pois.py`, `planner-api.py`, `kmz-editor-api.py`, `permit_map.py --allow-test-writes`, `panorama_api.py --allow-test-writes`: alle PASS.
- Playwright (Chromium, Kacheln und Naturschutz-API synthetisch, fünf synthetische Missionen „Demo.Pano.001/002/008/010“ und „Pano010 Langer Missionsname …“): Desktop 1280 × 800, Tablet 1024 × 768, Telefon 430 × 860 mit Touch. Geprüft: Checkbox rechts (13 px vom Rand), Griff links (11 px), natürliche Reihenfolge 001 · 002 · 008 · 010 · Pano010, Pfeiltaste hoch/runter am Griff ändert und speichert die Reihenfolge, Mehrfachauswahl zählt in allen drei Sprachen, Marker tragen Kennungen 001/002/008/010, gewählte Mission bekommt den Ring, Projekt-PDF (de) und Missions-PDF (uk, en) werden erzeugt und mit `pdftoppm` gerendert; keine Konsolen- oder Seitenfehler.
- Bekannte Grenze der Sandbox: echte basemap.at-Kacheln und der UBA-Dienst sind nicht erreichbar, deshalb synthetische Kacheln und Flächen in den Bildern. Orthofoto-Lesbarkeit bitte beim Codex-Review auf dem Live-System gegenprüfen (Linienstärken sind dafür ausgelegt: helle Kontur unter jeder Linie).

## Ergebnisse unter `ergebnis/`

- `liste-de.png`, `liste-en.png`, `liste-uk.png`, `liste-auswahl.png`, `kacheln.png`
- `projektkarte-auswahl.png`, `einzelkarte-uk.png`, `zeilen-tabelle.png`, `tablet-projektkarte.png`, `telefon-liste.png`, `telefon-projektkarte.png`
- `Projektkarte-de.pdf` (Projekt, 2 Seiten), `Missionskarte-uk.pdf` und `Missionskarte-en.pdf` (Einzelmission, je 2 Seiten) plus gerenderte Seiten `pdf-*.png`

## Offen / Hinweise für Codex

- Browser-Voraussetzung fürs PDF: `DecompressionStream` (Chrome 80+, Safari 16.4+, Firefox 113+). Fehlt sie, meldet der Export „Die PDF-Schrift konnte nicht geladen werden.“ statt ein PDF ohne Kyrillisch zu liefern.
- Betreiber im PDF-Kopf kommt aus Einstellungen → Name (bereits vorhandenes Feld, serverseitig im Markenkopf). Ohne Eintrag bleibt der Kopf neutral (nur Logo und Wortmarke). Eigenes Logo je Installation wäre ein neues Feld in `settings` und `config.json`; nicht umgesetzt, da API-Änderung.
- Kennungen bei Namensdubletten (z. B. „Demo.Pano.010“ und „Pano010 Ostseite“) sind beide „010“, wie in den Beispieldaten sichtbar. Das ist gewollt (Kennung aus dem Namen), sollte aber beim Benennen beachtet werden.
- Die übrigen Dialoge sind nicht übersetzt (siehe Sprachen). Benutzerverwaltung und RC-Tests unverändert offen bei Codex.
