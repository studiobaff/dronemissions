# Übergabe: Oberfläche, Gestaltung und offene Punkte

Stand: 7. November 2026, Branch `claude/drone-missions-ui-handoff-4nsj6e`. Enthält den Merge des lokalen Stands des Eigentümers (Branch `lokaler-stand`: Geozonen, Adresssuche, Standortansicht, Mehrfachauswahl, Projektdateien, MPROJ, Kundenfreigaben, Ordner löschen, Bridge-Quellcode).

Diese Datei ist die Übergabe für die nächste Sitzung, egal ob Mensch oder Agent. Sie beschreibt, was an der Web-Oberfläche geändert wurde, nach welchen Regeln, wie geprüft wird, und was offen ist. Die ursprüngliche Übergabe-ZIP (`.local/claude-ui-handoff/`) liegt nur lokal auf dem Mac des Eigentümers und ist nicht im Repository; ihre Inhalte konnten in dieser Sitzung nicht gelesen werden.

## Was geändert wurde

Nur die drei Oberflächendateien in `public/` wurden überarbeitet. `api.php`, `lib.php`, `index.php`, das SQLite-Schema, die Blob-Ablage, Freigaben und Tests sind unverändert. Alle bestehenden Funktionen bleiben erhalten; die API-Aufrufe sind identisch.

| Datei | Vorher | Nachher |
| --- | --- | --- |
| `public/view.html` | Unicode-Zeichen als Icons, einzeilig | SVG-Sprite mit 35 Strich-Icons, Topbar und Schublade für Mobil, Filterchips, Sortierung, Bestätigungsdialog, Ergebniszeile, Fortschrittsbalken |
| `public/style.css` | Minifiziert, Schriftgrößen bis 8 px, feste Pixelmaße | Design-Tokens (Farbe, Radius, Schatten, Easing, Dauer), Bausteine `.btn`, `.field`, `.badge`, `.chip`, `.segmented`, `.notice`, `.dialog`; kleinste Schrift 11 px, Eingabefelder 16 px; `100dvh`, sichere Ränder, `prefers-reduced-motion`, `prefers-reduced-transparency`, `prefers-contrast` |
| `public/app.js` | Minifiziert, `confirm()`, keine Ladeanzeige | Lesbar gegliedert; Pfadnavigation (Breadcrumb), Filter und Sortierung, Ein-/Mehrzahl, relative Datumsangaben bis sieben Tage, Skeleton beim ersten Laden, Fortschrittsbalken bei jeder Anfrage, Schaltflächen mit Ladezustand, eigener Bestätigungsdialog, Höhenprofil mit Hover-Fadenkreuz und Tooltip, Prüfsumme kopieren, Datei-Drop-Zonen, Tastenkürzel `/` für die Suche |

Aus dem lokalen Stand des Eigentümers übernommen und in die neue Oberfläche eingebaut: Mehrfachauswahl mit Verschieben (Dialog und Ziehen auf Ordner), „Ohne Projekt“ als Ansicht, Unterordner ein-/ausblenden, MPROJ-Upload und Zuordnung von Projektdateien zu KMZ-Missionen, Punkt für die Projektkarte und Litchi-Hub-Link je Mission, Navigationslinks (Google Maps, Apple Maps, KML), Kundenansicht für Lesefreigaben (nur Standorte und Navigation), leere Ordner löschen, einklappbare Seitenleiste, Kartenpanel mit Hintergrundkarte, Adresssuche und Geozonen (`zones.js`, unverändert übernommen und über die Klassennamen neu gestaltet), Standortansicht mit Zonen, Wetter und Geländehöhe. Dazu `dm_migrate()` in `lib.php`, damit bestehende Datenbanken die neuen Spalten automatisch bekommen.

Neue, kleine Funktionen (keine API-Änderung nötig): Typfilter (KMZ, CSV, Litchi, Punkte), Sortierung (zuletzt geändert, Name, längste Route), Ergebniszeile, Zähler für Planungspunkte, Größenangabe und Änderungsdatum in den Dateifakten, geschätzte Flugzeit aus `estimatedSeconds`, eigener Leer-Zustand für „keine Treffer“ und „Archiv leer“.

Bewusst nicht gemacht: Dark Mode (siehe offene Punkte), Listen-/Tabellenansicht, Mehrfachauswahl, Drag-and-drop von Missionen zwischen Ordnern.

## Gestaltungsregeln

Die Regeln stammen aus den im Projekt installierten Skills (`.claude/skills/`, Quelle `emilkowalski/skills`, MIT) sowie dem Dataviz-Skill für das Höhenprofil. Sie gelten für alle weiteren Änderungen:

- **Bewegung nur mit Zweck.** Dialoge öffnen in 220 ms mit `ease-out` ab `scale(.97)`, nie ab `scale(0)`. Schaltflächen reagieren beim Drücken mit `scale(.97)` in 110 ms. Tastaturaktionen (`/`, Escape) sind nicht animiert. Nichts dauert länger als 300 ms.
- **Hover nur bei echtem Zeiger.** Alle `:hover`-Regeln stehen in `@media (hover:hover) and (pointer:fine)`. Touch bekommt `:active`.
- **Mobil wie eine App.** `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation`, `user-select: none` nur auf Bedienelementen, Eingaben mindestens 16 px (sonst zoomt iOS), `100dvh` statt `100vh`, `env(safe-area-inset-*)` mit `viewport-fit=cover`, Seitenleiste als Schublade mit Scrim.
- **Typografie.** Systemschrift. Große Titel mit negativem Letter-Spacing (−0.025 em), Fließtext bei 0. Zahlen mit `font-variant-numeric: tabular-nums`. Lauftext maximal 65 Zeichen breit.
- **Worst-Case-Daten einplanen.** Titel auf zwei bis drei Zeilen begrenzen, Pfade mit Auslassung, Dateinamen und Hashes mit `overflow-wrap: anywhere`, `min-width: 0` auf Textspalten, Zähler mit korrekter Mehrzahl. Testdaten dafür stehen in `tests/`-nahem Skript (siehe Prüfung).
- **Höhenprofil.** Eine Linie pro Flugroute mit fester Farbreihenfolge (`ROUTE_COLORS`), 2 px, zurückhaltendes Raster, Legende nur bei mehr als einer Route, Hover-Fadenkreuz mit Tooltip. Text trägt Textfarbe, nie die Serienfarbe.
- **Bestätigungen nur für Unumkehrbares.** Löschen eines Planungspunkts und Widerruf einer Freigabe. Archivieren braucht keine Bestätigung, weil es umkehrbar ist.
- **Wegweisung.** Jede Ansicht zeigt Pfad (Breadcrumb, klickbar), Titel, Untertitel und Zähler. Leer-Zustände erklären, was fehlt und was zu tun ist.

## Prüfung

```sh
# Testinstanz (leer!) vorbereiten
export DRONEMISSIONS_PRIVATE=/pfad/zu/privat-test
php tools/setup.php < /pfad/zu/test-access.json
php -S 127.0.0.1:8080 -t /pfad/zum/docroot   # docroot/dronemissions -> public/
python3 tests/integration.py --base http://127.0.0.1:8080/dronemissions --access /pfad/zu/test-access.json --allow-test-writes
php tests/parser.php
```

Der Browser-Durchlauf ist in `docs/QA.md` beschrieben. Er wurde in dieser Sitzung mit Playwright und headless Chromium ausgeführt; das Skript lag außerhalb des Repositorys. Wer ihn wiederholen will, braucht: Login falsch/richtig, Suche, Filter, Sortierung, Detaildialog mit Speichern, Karte mit Punkt setzen, Punkt löschen über Bestätigung, Upload, Projekt anlegen, Freigabe erstellen und als zweite Sitzung öffnen, Archiv, mobile Schublade. Kriterium: keine `pageerror`, kein Konsolenfehler außer dem 401 des falschen Logins.

Nicht geprüft, weil in der Cloud-Umgebung nicht möglich: echte Kartenkacheln (Server nicht erreichbar), echte Telefone (Hover-Haftung, Tastatur, sichere Ränder), DJI Fly.

## Offene Punkte Web-UI

1. **Icons.** Das Sprite in `view.html` ist handgezeichnet. Der Eigentümer möchte ein Set vom Noun Project (Konto vorhanden). Engere Auswahl aus dieser Sitzung: „Drone Outline“ (izwarm, Collection 298719), „Map and Navigation Line Detailed“ (dinosoftlab, 101091), „Interface Essentials (Light)“ (mmriz16, 272540). Vorgehen: SVGs mit dem Konto herunterladen, auf 24-px-Raster und Strichstärke 1,75 normalisieren, als `<symbol>` ins Sprite übernehmen, Lizenz in `public/vendor/` ablegen.
2. **Dark Mode.** Tokens sind vorbereitet (alle Farben in `:root`), aber es gibt noch keine zweite Palette. Beim Einbau: Leaflet-Kacheln und Routenfarben mitprüfen, `theme-color` pro Schema setzen, Dataviz-Palette gegen die dunkle Fläche validieren.
3. **Screenshots in `docs/screenshots/`** zeigen neutrale Platzhalter statt basemap.at-Kacheln. Auf einer Installation mit Internetzugang neu aufnehmen.
4. **Listenansicht** für große Bibliotheken (Tabelle mit Sortierung nach Spalten) fehlt; die Kartenansicht skaliert über etwa 100 Missionen nicht mehr gut.
5. **Litchi LCHM/LCHZ** werden weiter nur archiviert, nicht dargestellt (Backend-Thema).
6. **Freigabe-Dialog**: nach dem Erstellen bleibt der Link sichtbar, Liste wird aktualisiert. Ein Ablaufdatum frei wählen zu können, wäre die nächste sinnvolle Ergänzung (API-Änderung nötig).

## Offene Punkte Bridge

Die Bridge ist eine eigenständige Desktop-App (PySide6, GPL-3.0-or-later) mit ADB-Übertragung auf Android-Controller, iPad/iPhone-Import über pymobiledevice3, Titelvorschau und Build-Skript. Der Quellcode liegt jetzt im Repository unter `bridge/` (`desktop.py`, `core.py`, `ios.py`, `preview.py`, `map_preview.py`, `cli.py`, `build_desktop.py`, Tests, `INVESTIGATION.md` mit dem Stand der Gerätetests). Installiert ist sie als `/Applications/Drone Missions Bridge.app`. Die Oberfläche wurde in dieser Sitzung auf 0.4 umgebaut (vier Tabs: Gerät & Missionen, Webarchiv, Übertragen, Protokoll; große Missionsliste mit Vorschaubildern, großes Titelbild, Aktionen „Neu anlegen“ und „Ersetzen“; Webarchiv-Anbindung über `bridge/archive.py` mit geprüftem KMZ-Download); siehe `bridge/README.md`. `bridge/tests/test_desktop.py` prüft die Bestätigungsgrenze, den Ersetzen-Pfad und das Verwerfen bei Geräte- oder Eingabewechsel. Alle 31 Bridge-Tests bestehen (offscreen, ohne Gerät); der Archiv-Client wurde zusätzlich gegen die laufende PHP-Testinstanz geprüft.

Anforderungen des Eigentümers für die Bridge-Oberfläche (unverändert übernommen):

- Vorhandene Gerätefunktionen erhalten (ADB-Übertragung, iPad-Import ist praktisch erfolgreich getestet; spätere Erweiterungen teilweise ungeprüft).
- Tabs statt einer einzigen Ansicht.
- Eine große Missionsliste.
- Deutlich größere Vorschaubilder.
- Klare Aktionen „Neu anlegen“ und „Ersetzen“.

Nächste Schritte: Auf dem Mac `python bridge/build_desktop.py` ausführen, die App am iPad („Neu anlegen“) und an der RC Pro 2 („Ersetzen“) durchspielen, Rückmeldung zur Logik einarbeiten. Windows-11-Paket auf einem Windows-Rechner bauen (siehe `bridge/README.md`). Gerätetests kann nur der Eigentümer machen. Erst danach den Hinweis „USB-Übertragung über die Bridge-App“ in der Web-UI um einen echten Download- oder Kopplungsweg ergänzen.

## Web-App Nachtrag 2026-11-08 (Branch `claude/drone-missions-ui-handoff-4nsj6e`)

Nur `public/` geändert, kein Schema, keine privaten Daten:

- **Vorschau-Editor** (`previews.js`): Route in 3D mit Umriss, Höhenfärbung und Wegpunktmarkern wie in Web-Karte und Bridge (Start „1“, Ende mit Nummer, kleine Punkte dazwischen, bei vielen Punkten ausgedünnt), Beschriftung „3D · Höhe … · N Wegpunkte“. Karte/Luftbild weltweit: in Österreich basemap.at (Luftbild mit Beschriftungs-Overlay), sonst OpenStreetMap (Karte) bzw. Esri World Imagery (Luftbild), Quellenangabe im Bild. Kartenzoom wird beim Öffnen so gewählt, dass die ganze Route sichtbar ist. Titel im Band vertikal zentriert. Die Server-Validierung (`provider` map|aerial) bleibt unverändert.
- **Kartenleiste „Karte & Zonen“** (`zones.js`, `style.css`): „Hintergrundkarte“ ist standardmäßig aufgeklappt und hat einen Akkordeon-Pfeil; die Leiste begrenzt ihre Höhe auf die Kartenhöhe und scrollt statt über den Kartenrand zu laufen.
- **OpenStreetMap „Access blocked“**: Ursache war `Referrer-Policy: no-referrer` in `index.php`; OSM sperrt Kachelanfragen ohne Referer. Jetzt `strict-origin-when-cross-origin`, zusätzlich `referrerPolicy` an Leaflet-Kacheln und Editor-Bildern. Freigabe-Token stehen nur im `#`-Teil der Adresse und werden nie übertragen.
- **Adresszeile** (`app.js`): `#projekt=<id>`, `#ansicht=archiv|ohne`, `#mission=<id>` werden beim Navigieren gesetzt und beim Laden bzw. Login wieder angewendet; Kundenlinks (`#share=`) unverändert. Fenstertitel und Kopf heißen `dronemissions`.
- Geprüft: `tests/integration.py` gegen eine frische lokale Installation (alle PASS) und Browserlauf mit Kachel-Fakes (Editor 3D/Karte/Luftbild, Kartenleiste, Deep Links).

## Bridge 0.6.0 (Branch `claude/drone-missions-ui-handoff-4nsj6e`, Stand 2026-11-08)

Gestaltungsdurchgang nach dem Apple-Design-Skill, Logik unverändert: Systemschrift, helles und dunkles Schema folgen dem System (`bridge/theme.py`), Symbolleiste mit Icon und Beschriftung, Schlüssel-Wert-Infoblock auf der Prüfseite, Projektbaum ohne Fokusrahmen, Vorschaubilder passen sich dem Platz an, Warteschlange zeigt sofort Bilder, Archivbild aus dem Webarchiv als Standard-Titelbild für Archivmissionen. Einstellungsfenster in einer Scrollfläche, damit sich Zeilen auf dem Mac nicht mehr überlagern. Nachtrag: App-Name `dronemissions-bridge` (Bundle umbenannt, Einstellungen/Schlüsselbund unverändert), Wortmarke wie die Website, Symbolleiste mit Kreis-Icons wie macOS 26, Kapsel-Knöpfe, iPad-Titelbilder werden beim Lesen geladen, Archivbild als Rückfall, „Vorschauen ins Webarchiv“ (API `preview-save`), Entfernen per Checkbox in Schritt 3 und 4, Umbenennen bei einer angehakten Mission. Web-App: Fenstertitel `dronemissions`. Bildschirmfotos hell und dunkel unter `bridge/docs/screenshots-0.5/`. 99 Tests ohne Gerät.

## Bridge 0.5.0 (Branch `claude/drone-missions-ui-handoff-4nsj6e`, Stand 2026-11-08)

Umgesetzt nach `bridge/docs/UI-HANDOFF-2026-11-08.md` und PR #6: Einstellungsfenster (`⌘,`) für Archiv, Schlüssel, Konfiguration und ADB; Schritt 2 mit Projektbaum wie die Website, kombinierter Suche/Sortierung, großen Vorschauen und echten Checkboxen (nur KMZ); Pfeilleiste „Gerät wählen → Missionen auswählen → Vorschauen prüfen → Übertragen“; Warteschlange mit getrenntem „Neu anlegen“/„Ersetzen“, eindeutigen Zielen, serieller Übertragung, Fehlerstopp, Anhalten, Fortsetzen ohne Doppelanlage; Wegpunktnummern in beiden Vorschauen; Luftbild mit basemap.at-Beschriftung in Österreich und Esri/OSM-Rückfall weltweit. Details und Bildschirmfotos: `bridge/README.md` (Abschnitte 0.5.0) und `bridge/docs/screenshots-0.5/`.

Nicht geprüft: Übertragung an echte Geräte (iPad neu anlegen, iPad ersetzen, RC Pro 2). Die Gerätewege selbst (`ios.apply_new`, `core.plan/apply`) sind gegenüber 0.4.4 unverändert, nur die Aufrufe laufen jetzt seriell aus der Warteschlange. Das Luftbild wurde nur gegen Kachel-Fakes getestet, weil die Cloud-Umgebung keine Kartenserver erreicht.

## Server-Update

Siehe `docs/UPDATE.md`: Nur `public/` wird auf den Server kopiert, private Daten bleiben unberührt, das Schema wird automatisch ergänzt.

## Umgebung

Für diese Sitzung wurde die persönliche Cloud-Umgebung `dronemissions` angelegt (Hosts: `thenounproject.com`, `static.thenounproject.com`, Paketmanager erlaubt). Sie dient nur der Icon-Suche und kann gelöscht werden, wenn das Icon-Set feststeht.
