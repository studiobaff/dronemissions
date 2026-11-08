# Web-Missionsplaner · erste Fassung

Unter **Mission planen** einen Umriss wählen, Flugmuster/Kamera einstellen, Route berechnen und prüfen. Der Planer ist für Eigentümer und Bearbeitungsfreigaben verfügbar; Kundenlinks erhalten keine Planungen oder Flugrouten.

## Grundlagen und Muster

- Projektbezogene Kartenreferenzen einschließlich QGIS-Umrissen als Grundlage auswählen. GeoJSON, KML oder KMZ direkt laden; QGIS zuvor nach **WGS84/EPSG:4326** exportieren. Eine fremde Projektion wird nicht automatisch geraten. Multi-Geometrien werden für die Auswahl in Einzelobjekte aufgeteilt.
- Polygon, offene Linie oder Kreis auf der Karte zeichnen. Beim Kreis Mittelpunkt und Radiuspunkt anklicken. Leaflet-Geoman 2.20.6 (MIT, lokal ausgeliefert) übernimmt Zeichnen und Bearbeiten. Polygon am ersten Punkt oder per Abschließen beenden; Ecken sind nach dem Zeichnen/Import direkt bearbeitbar; bei Bedarf fixieren. Ecken ziehen, Zwischenmarker für neue Ecken ziehen, Rechtsklick löscht Ecken. Mindestzahl bleibt erhalten. Rücknahme und Abbrechen erhalten den vorherigen Umriss.
- OSM-Gebäude im aktuellen Ausschnitt bis 4 km² laden. Erst der ausdrückliche Knopfdruck sendet den Ausschnitt an den öffentlichen Overpass-Dienst (bei Ausfall für höchstens 0,25 km² die OpenStreetMap-API). OSM ist für bestehende, erfasste Gebäude gedacht; zukünftige Baukörper aus QGIS übernehmen. Nur geschlossene Gebäude-Ways, keine vollständigen Multipolygon-Relationen. Quelle und ODbL-Hinweis bleiben sichtbar. Der Rückfall auf die OpenStreetMap-API wurde mit einem kleinen öffentlichen Ausschnitt geprüft; die Verfügbarkeit des externen Dienstes bleibt abhängig vom Anbieter.
- **Grid:** Nadir-Raster auf Polygonen, einschließlich Löchern. Punkte werden innerhalb der Fläche erzeugt. Verbindungen, die durch ausgesparte Flächen führen würden, erzeugen getrennte Abschnitte; An-/Rückflug bleibt gesondert zu prüfen.
- **Kreis, Helix, Doppelhelix:** Zentrum aus Punkt oder Umriss, Radius manuell oder aus Umriss plus Abstand. Ein Zylinder behält seinen Radius bei Höhenänderung. Die Halbkugel bindet ausdrücklich die obere Höhe an untere Höhe plus Radius; ihr Radius und Baukörperabstand werden nach oben kleiner. Doppelhelix erzeugt getrennte Aufwärts-/Abwärtsflüge, um 180° versetzt. Zusätzliche Abtastung begrenzt auch am Scheitel den räumlichen Fotoabstand.
- **Fassade / POI-Polygon:** versetzte Bahnen an Linien bzw. Polygonseiten, Höhenreihen und Kamera zur Wand oder zum Mittelpunkt. Bei offenen Linien Flugseite ausdrücklich wählen; bei Polygonen wird außen geplant. Jede Wand ist getrennt, Ecken werden nicht automatisch umflogen.

## Kamera, Überlappung und Höhen

Vorgaben für die Hauptkameras von Mini 4 Pro, Mini 5 Pro, Air 3, Air 3S, Mavic 3 Series und Mavic 4 Pro; zusätzlich eigenes Profil. Quellen sind die verlinkten DJI-Spezifikationen:
[Mini 4](https://www.dji.com/mini-4-pro/specs), [Mini 5](https://www.dji.com/mini-5-pro/specs), [Air 3](https://www.dji.com/air-3/specs), [Air 3S](https://www.dji.com/air-3s/specs), [Mavic 3](https://www.dji.com/mavic-3/specs), [Mavic 4](https://www.dji.com/mavic-4-pro/specs).

Das nominelle DJI-FOV wird als diagonales Bildfeld interpretiert und mit dem gewählten Bildseitenverhältnis auf Breite/Höhe aufgeteilt. Für eine ebene, senkrecht aufgenommene Fläche gilt: Bildfeld-Diagonale = `2 × Abstand × tan(FOV/2)`; Foto-/Bahnenabstand = passende Bildfeldseite × `(1 − Überlappung)`. Bei Nadir-Rastern zählt die Höhe über der eingegebenen ebenen Aufnahmefläche; bei Fassaden der Wandabstand. Bildformat, Crop, Verzeichnung und anderes Objektiv brauchen ein angepasstes Profil. GSD und Bildabdeckung sind nominelle Modellwerte.

Für Kreis/Helix und schräge POI-Aufnahmen sind die Abstände Richtwerte. Eine echte 3D-Überlappung ist ohne Objektoberflächenmodell nicht nachgewiesen; Prozentwerte dürfen nicht als gemessene Oberflächenüberdeckung verstanden werden. Der Planer zeigt zusätzlich den größten tatsächlichen Wegpunktabstand und die erzeugte Höhenspanne.

**Alle Exporthöhen sind relativ zum tatsächlichen Startpunkt.** Optional folgt Grid/Kreis/Helix dem DEM; siehe Geländeanpassung unten. Ohne DEM gelten Aufnahmeflächenhöhe und Flug-/Zielhöhen relativ Start. Radius bleibt ein eigener Parameter. Das 3D-Bild und das Höhenprofil zeigen die gelesenen Geländehöhen, kein Gebäudemodell. Der Rückkehr-/Startablauf verwendet die Geräteeinstellungen; er ist nicht als geprüfte Hindernisroute enthalten. An-/Rückflug und Hindernisfreiheit werden nicht automatisch berechnet.

## Abschnitte, Speichern und Export

Pro Aufnahmepunkt: anhalten, Gimbal ausrichten, kurz warten, ein Foto. Eine zusätzliche Pause nach dem Foto ist optional (neue Planungen: 0 s) und liegt unter „Erweiterte Aufnahme-Einstellungen“. Bestehende gespeicherte Pausen bleiben erhalten. Foto- und Wegpunktzahl stimmen in diesem Exportmodell bewusst überein; Zeitserien/Mehrfachbelichtungen werden nicht vorgetäuscht. Einstellbare Fotoobergrenze bis 200 je Abschnitt (Vorgabe 150), bis zehn wiederholte Aufnahmen an Übergängen. Geometrisch getrennte Wände/Helices erhalten keine automatische Verbindung. Anzahl, Strecke und geschätzte Zeit erscheinen gesamt und pro Abschnitt; Pausen sind berücksichtigt, An-/Rückflug nicht.

**Planung speichern** erhält Umriss, Kamera und Parameter mit Konflikterkennung sowie Generatorversion und Routenprüfsumme. Eine abweichende Neuberechnung muss erneut gespeichert werden, bevor sie archiviert werden kann. Gespeicherte Planungen sind über die Liste und bei erzeugten Archivmissionen über **Planung bearbeiten** erreichbar. Eine `.dmplan.json` lässt sich herunterladen und erneut öffnen. `mission_plans` und `mission_plan_runs` liegen in der privaten SQLite-Datenbank und werden bei der ersten Verwendung angelegt. Projektordner mit Planungen lassen sich nicht versehentlich löschen.

Für den DJI-WPML/KMZ-Export eine vorhandene, passende DJI-KMZ aus dem Archiv als **Geräteprofil** wählen. Es werden nur überprüfte Geräte-/Nutzlastkennungen übernommen; keine fremden Wegpunkte oder unbekannten Modellnummern geraten. Kameraprofil und Gerät müssen tatsächlich zusammenpassen. WPML-Referenz: [DJI Common Elements](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html).

Ein Abschnitt liefert KMZ, mehrere liefern ZIP mit einzelnen KMZs, Planungsdatei und Hinweisen. Beim Archivieren entstehen Teilmissionen im **gleichen Projekt**, verknüpft mit der gespeicherten Mutterplanung; keine neuen Projektordner pro Datei. Wiederholtes Archivieren desselben gespeicherten Stands und Geräteprofils erzeugt keine Duplikate. Änderungen der Planung bleiben getrennt von unveränderlichen bisherigen KMZ-Versionen.

## Prüfstand und nächste Schritte

Geprüft: reine Rechenregressionen, Grid-Löcher, Fassadenabstand/-richtung, Kreis/Helix/Doppelhelix/POI-Polygon, unveränderter Zylinderradius, echte Halbkugel, stabiles erneutes Öffnen, adaptive Schrittweite am Scheitel, Fotoaufteilung, Aktionsreihenfolge und lokale Nummern. API-Tests decken gespeicherte Planungen/CAS, Projektgrenzen, Kundenrechte, Archiv-Idempotenz sowie Einzel-KMZ und Abschnitts-ZIP ab. Der Browser-Rundlauf mit synthetischem QGIS-Polygon ergab 496 Fotos in vier Teilen, identisch nach Wiederöffnen. Der heruntergeladene ZIP wurde zusätzlich mit dem strengen Bridge-Parser geprüft.

**Noch kein DJI-Fly-Gerätetest dieser neu erzeugten Exporte und kein Flugtest.** Die frühere erfolgreiche Archiv-Wiederherstellung bestätigt diesen neuen Exporter nicht. Schräges perspektivisches Grid, direkter CRS-Transformator, Video-/Zeitserien und ein Hindernismodell bleiben weiterer Ausbau. Grenzen der ersten Fassung: 5-km-Umriss, 1000-m-Kreisradius, 5000 Aufnahmepunkte und 100 Abschnitte.

Die aktuellen Map-Creator-Anforderungen und Referenzen bleiben in [MISSION-PLANNING.md](MISSION-PLANNING.md). Der neue Rechenkern ist eigenständig implementiert; es wurde kein vollständiger Desktop-App-Code aus einem Installationspaket übernommen.

## Geländeanpassung · Generator 0.2.0

1. Unter „Flugmuster & Kamera → Gelände & Startpunkt“ **Gelände folgen** wählen.
2. Tatsächlichen Startpunkt auf der Karte setzen (oder WGS84-Koordinaten eingeben). Alle Teilmissionen müssen von diesem Referenzpunkt starten.
3. EU-DEM 25 m für Europa oder SRTM 30 m (60°S–60°N) wählen. Fehlende Daten sperren Berechnung/Export; es gibt keinen stillen Ersatz durch Null oder Meereshöhe.
4. Grid-Flughöhe bzw. Helix unten/oben gelten nun über lokalem DEM. Zusätzlich expliziter Höhenzuschlag (Standard 5 m), Stützpunktabstand 5–30 m (Standard 10 m), Steig-/Sinkgrenze 0,2–5 m/s (Standard 2).
5. Route berechnen und Höhenprofil prüfen: Grün = DEM relativ Start, Gelb = exportierte Flugroute.

Formel: **Exporthöhe = DEM am Flugpunkt − DEM am Startpunkt + geplante AGL-Höhe + Zuschlag**. POIs erhalten die DEM-Höhe am Zielort, nicht am Flugpunkt. Helix-Radien bleiben erhalten; lokal versetzte Höhen verformen eine Halbkugel am Hang ausdrücklich. Manuelle Kameraneigung bleibt erhalten; automatisch wird die Neigung zum höhenkorrigierten POI neu berechnet.

Die Route wird zwischen Fotopunkten auf den gewählten Abstand verdichtet. Zusätzliche Navigationspunkte haben **keine Fotoaktionsgruppe**. Höhen sind in template.kml und waylines.wpml eingebrannt, weiterhin `relativeToStartPoint`, kein ungeprüfter `realTimeFollowSurface`-Modus. Steig-/Sinktempo wird über segmentbezogene Geschwindigkeit begrenzt. Höchstens 200 Flugpunkte je Abschnitt; Fotolimit zusätzlich 20–200. Wiederholungen enthalten die dazwischenliegenden Flugpunkte; bei sehr langen Zwischenstrecken werden höchstens 50 vorherige Flugpunkte wiederholt.

**Genauigkeitsgrenze:** 25/30 m sind nominelle DEM-Rasterweiten, keine zugesicherte Höhengenauigkeit. Engere Flugpunktabstände erhöhen nicht die DEM-Auflösung. Zwischen den Stützpunkten wird gerade geflogen; Bodenfreiheit zwischen Samples ist nicht nachgewiesen. Gebäude, Bäume, Kräne und künftige Bauzustände fehlen. Überlappung bleibt nominal; Hangneigung und schräge Aufnahmeflächen sind kein vollständiges photogrammetrisches Oberflächenmodell. An-/Rückflug und Rückkehrhöhe bleiben ungeprüft. Exporthöhen außerhalb 1–500 m relativ Start oder Abschnitte steiler als 45° werden abgelehnt.

OpenTopoData erhält erst bei Berechnen/Speichern/Export einer DEM-Planung die Start-/Routen-/POI-Koordinaten. Fester HTTPS-Endpunkt, 100 Positionen je Anfrage, mindestens 1,1 Sekunden Abstand und installationsweites Tagesbudget unter 1000 Anfragen. Höchstens 6000 verdichtete Flugpunkte; öffentliche Dienste können ausfallen. Private, unveränderliche Snapshots unter `terrain/` außerhalb des Webroots machen Wiederholung, Speichern und Export reproduzierbar. Neue Positionslisten erhalten einen neuen Snapshot. Keine DEM-Dateien oder echten Flugkoordinaten ins Repository übernehmen.

## Parameter und Ansichten

Zahlenfelder und zugehörige Slider für Überlappung, Höhen, Radius, Wandabstand, Winkel, Tempo, Pausen, Abschnittsgröße, DEM-Zuschlag und Stützpunkte. Zusätzlich Windungszahl (0 = aus Überlappung), Drehrichtung und automatische/manuelle Gimbal-Neigung. Karte bleibt beim Scrollen der Parameter sichtbar. Höhenprofil ergänzt 2D und 3D.

## Quellen und Prüfung

- [Leaflet-Geoman Zeichnen](https://geoman.io/docs/leaflet/modes/draw-mode) und [Bearbeiten](https://geoman.io/docs/leaflet/modes/edit-mode); MIT-Lizenz und feste Version in `docs/third-party/leaflet-geoman-LICENSE.md` und den lokal ausgelieferten JS-/CSS-Dateien unter `public/vendor/geoman/`.
- [OpenTopoData API](https://www.opentopodata.org/api/) und [Datensätze/Limits](https://www.opentopodata.org/).
- [Map Creator Desktop](https://map-creator.com/windows.htm) als Funktionsreferenz.
- Regression: synthetischer schiefer Boden, Grid-AGL, Helix-Radius/POI, Navigation ohne Fotos, Exporthöhen und Aktionsindizes, fehlende DEM-/Startdaten und Steilhang. Echter DEM-Abruf, Polygon-Abschluss/Eckpunkt-Löschen/Rücknahme, Grid-Speichern und Helix-Export im isolierten Browser-Testarchiv geprüft. Die zwei exportierten Helix-Abschnitte wurden zusätzlich vom Bridge-Parser akzeptiert. Keine Geräte- oder Flugprüfung dieser Exporte.

## Interaktive Planung

Umriss und Flugparameter stehen gemeinsam unter „Planen“. Fertige und importierte Umrisse sind sofort bearbeitbar. Änderungen an Geometrie, Kamera, Flugart oder Reglern berechnen die Vorschau nach 650 ms Eingabepause automatisch neu; die Ansicht und der Kartenausschnitt bleiben erhalten. Währenddessen ist die alte Route als veraltet markiert und Export/Speichern gesperrt. Es läuft höchstens eine Berechnung gleichzeitig, nachfolgende Änderungen werden zusammengefasst und überholte Antworten verworfen. DEM-Abfragen folgen denselben Regeln; je nach Dienst dauern sie länger. „Vorschau aktualisieren“ erlaubt einen manuellen Wiederholungsversuch nach Fehlern.

### Aufnahmeabstände und Überlappung (Generator 0.3.0)

Neue Planungen starten mit „Direkt in Metern“: Fotoabstand entlang der Route und Abstand zwischen Rasterbahnen beziehungsweise Höhenreihen/Windungen. Die Werte sind Obergrenzen; ein Abschnitt wird gleichmäßig eingepasst. Alternativ berechnet „Über gewünschte Überlappung“ diese Abstände. Alte Planungen ohne `spacingMode` bleiben im bisherigen Überlappungsmodus.

Die Anzeige trennt Vorgaben, eingepasste Abstände und nominale Überlappung. Formel: `100 × (1 − Abstand / Bildfeldausdehnung)`. Das volle diagonale Bildfeld ist `2 × Abstand zur Aufnahmefläche × tan(FOV / 2)`; Breite/Höhe ergeben sich aus dem Bildseitenverhältnis. Beim Nadir-Grid liegt die kurze Bildseite in Flugrichtung. Kamera, Fotoformat, Höhe über Aufnahmefläche und Bahnenrichtung müssen beim Vergleich übereinstimmen. Nominale Prozentwerte bei schrägem Blick, Helix oder unebener Oberfläche sind kein Nachweis tatsächlicher 3D-Bildüberlappung. Quellen: [Pix4D Bildrate und Frontalüberlappung](https://support.pix4d.com/hc/en-us/articles/202557479), [Pix4D – Prüfung gilt für Nadirbilder](https://support.pix4d.com/hc/en-us/articles/203756125); Kameradaten sind im jeweiligen Profil verlinkt.

Das Raster verteilt mindestens zwei Bahnen über den gesamten Umriss, mit einem halben Bahnenabstand zum Rand. Es reduziert kleine Gebiete nicht mehr auf eine einzelne Bahn, nur weil das nominale Bildfeld größer als das Gebiet ist. Bei concaven Umrissen und Löchern bleibt das Clipping samt separaten Abschnitten erhalten. Eine ältere gespeicherte Planung kann durch Generator 0.3.0 mehr Bahnen bekommen; vor erneutem Export wird sie neu berechnet und als geänderter Planungsstand gespeichert. Bestehende KMZ-Dateien werden nicht geändert.

Bedienvergleich mit Map Creator am 8.11.2026: Fotoabstand 13 → 20 m änderte die angezeigte nominale Überlappung 75,3 → 61,9 %; „Calculate Grid“ änderte die Route. Beim Ziehen einer Ecke wurde die Route neu erzeugt; Undo stellte den Umriss wieder her. Teständerungen wurden zurückgenommen, keine Mission gespeichert/exportiert. Dessen numerische Bildfeldwerte werden nicht ungeprüft kopiert.


## Kompakte Werkzeuge und Kalotte · Generator 0.4.0

Missionsart, Kamera und Abstandsmodus stehen in einer schmalen oberen Leiste. Darunter die zur Flugart passenden Slider mit direkt editierbaren Zahlen. Zeichenwerkzeuge sowie Karte/3D/Höhenprofil liegen unmittelbar über der Vorschau. Planung/Name/Projekt und Import sind links einklappbar; „Seitenleiste“ gibt die gesamte Breite für die Karte frei. Änderungen berechnen weiterhin automatisch neu. Die feste Werkzeugleiste ersetzt große Zeichenknöpfe im Seitenpanel.

- **Halbkugel** ist ab Generator 0.5.0 der Standard neuer Helix-/Doppelhelixplanungen; die abgeflachte **Kalotte** bleibt wählbar. Mit Basisradius `r`, Unterhöhe `b` und Oberhöhe `t` gilt `h=t-b`, `R=(r²+h²)/(2h)`, Kugelmittelhöhe `t-R`. Es gilt `0<h≤r`. Die Route liegt auf dieser Kugelfläche und endet über der Objektmitte mit Pitch −90°. Doppelhelix ergänzt eine um 180° versetzte absteigende Bahn als eigenen Abschnitt. Das ist eine eigenständige Konstruktion, keine Behauptung exakter Map-Creator-Parität.
- Die Kamera zielt auf die **Objektmitte mit POI-Höhe**, nicht zwangsläufig auf den geometrischen Kugelmittelpunkt. POI muss mindestens 1 m unter dem Scheitel liegen. Radius und Unter-/Oberhöhe sind direkt einstellbar. Windungsabstand wird entlang des Kalottenmeridians gemessen; „Windungen > 0“ überschreibt dessen automatische Ableitung.
- **POI-Höhenbezug:** relativ zum tatsächlichen Start oder AGL über DEM am POI. Zusätzlich eigener Offset. Für AGL gilt `POI relativ Start = DEM(POI) − DEM(Start) + Zielhöhe + Offset`. Flugroute und POI-Höhenbezug sind getrennt. Fehlende DEM-Werte/Startdaten sperren den Vorgang. DEM-Dienste erhalten die Start- und POI-Koordinaten. Diese Funktion verändert nicht die Flugbahnhöhen.
- Ab Generator **0.5.1** ist „Gelände folgen“ auch für Kalotte und FOV-Halbkugel verfügbar. Die horizontale Route bleibt erhalten; exportierte Höhe = Ausgangshöhe + DEM am Flugpunkt − DEM am Start + Zuschlag. Die resultierende Form ist auf unebenem Gelände keine exakte Kugel mehr. Das ist keine starre Neigung/Rotation der gesamten Kalotte. Ohne DEM bleibt die bisherige Kugelgeometrie unverändert.
- **Linienflug:** exakt entlang eines gezeichneten/importierten Linienzuges, Nadir, Fotoabstand in Metern, keine Querüberlappung.
- **Korridor:** symmetrische Gesamtbreite um eine Mittellinie, parallele Bahnen mit begrenztem Abstand. Gehrungsverbindungen an Ecken; scharfe Kehren und selbstschneidende Einzelbahnen werden abgelehnt. Verbindungswege und Querungen zwischen Bahnen bleiben in der Vorschau zu prüfen. DEM-Folgen wie beim Grid verfügbar.
- Bei Kalotten dient der kleinste Abstand der Bahn zum gewählten POI als konservativer **Rechenabstand für das Kameramodell**. Die tatsächliche Oberfläche ist unbekannt. Angezeigte Prozentwerte sind keine gemessene 3D-Überdeckung und garantieren keine Qualität eines Gaussian-Splatting-Modells. Grid-Überlappung gilt nominal für eine ebene, nadir aufgenommene Fläche. Mehr Höhe ist kein Muss: kleinere Foto-/Bahnenabstände erhöhen die Überlappung ebenfalls.

Geprüft: Kugelgleichung, exakt senkrechter Scheitelblick, Zielhöhe/Offset und DEM-Datum, unveränderte Flughöhen bei POI-AGL, Doppelhelix-Endpunkte, räumliche Fotoabstände, Linie/Korridor, Fehlereingaben, Speichern/Neuberechnen und KMZ-Aktionen ohne optionale Nachpause. Keine reale Flugprüfung dieser neuen Muster.

## Höhenreferenz-KMZ · Generator 0.5.0

Unter **Höhenpunkte aus Erkundungsflug** eine DJI-Waypoint-KMZ (maximal 8 MB, 1000 Punkte) importieren. Unterstützt werden explizite `executeHeight`-Werte mit `relativeToStartPoint` in jeder Route. Fehlende/absolute/gemischte Höhenmodi werden abgelehnt. Original bleibt unverändert; die Planung speichert die normalisierten Referenzpunkte, Auswahl und Quellprüfsumme, nicht die Originaldatei als Archivanhang.

1. Punkte auswählen. Ihre Höhen sind **Drohnenpositionen**, keine automatisch gemessenen Gebäude- oder Baumhöhen.
2. Gleichen tatsächlichen Startpunkt bestätigen oder bekannten Höhenversatz eintragen: `Höhe alter Start minus Höhe neuer Start`. Der Versatz wird auf alle Referenzhöhen addiert; unbekannte Bezugssysteme werden nicht geraten.
3. Sicherheitsabstand einstellen. Globale Mindesthöhe = höchste ausgewählte Referenz + Startversatz + Sicherheitsabstand.
4. **Mindesthöhe übernehmen** hebt Grid-Höhe bzw. Helix-Unterhöhe an; bei der Kalotte werden Unter-/Oberhöhe gemeinsam verschoben. Alle berechneten Exportpunkte müssen mindestens auf der aktivierten Untergrenze liegen. Eine niedrigere Route sperrt Vorschau, Speichern und Export. Im DEM-Modus ist die automatische Übernahme deaktiviert; die Untergrenze prüft weiterhin exportierte Höhen relativ Start.

Die ursprüngliche Referenzroute liegt gestrichelt unter der neuen Route. Getrennte KMZ-Routen werden nicht verbunden. Ausgewählte Punkte sind orange, ausgeschlossene grau. Keine Höheninterpolation entlang dieser Linie. Ausgewählte Höhen erscheinen in 3D, die Untergrenze im Höhenprofil. Vier Punkte belegen keine Hindernisfreiheit im gesamten Gebiet.

## FOV, schräge Aufnahmefläche und Bedienung · 0.5.0

- **Halbkugel/Kalotte, FOV-Modus:** Aus diagonalem FOV und Bildseitenverhältnis werden horizontaler/vertikaler Öffnungswinkel berechnet. Ziel-Winkelabstand entlang = horizontales FOV × (1 − gewünschte Winkelüberdeckung); Windungsabstand = vertikales FOV × (1 − gewünschte Winkelüberdeckung). Route wird anhand der Blickrichtungen zum POI abgetastet. Bei geometrisch ähnlicher Skalierung bleibt die Fotozahl gleich, die Meterabstände ändern sich. Explizite Windungszahl überschreibt die automatische Ableitung; tatsächliche Winkelüberdeckung wird angezeigt. Diese Prozente sind **keine gemessene Oberflächenüberdeckung**.
- **Grid/Korridor/Linie mit manueller Neigung**, etwa −70°: Strahlen werden auf die ebene Aufnahmefläche projiziert. Es entsteht ein Trapez. Dessen Tiefe bestimmt den Längsabstand, seine schmalste Breite den Querabstand. Bis zum Horizont reichende Bildfelder werden abgelehnt. Verschobener Bildausschnitt, reale Oberflächen, Verdeckung und vollständige Randabdeckung sind nicht automatisch gelöst; GSD ist nur nominal.
- **Footprint** blendet das berechnete Bildfeld eines Fotopunkts auf dieser Ebene ein. Andere Fotopunkte anklicken. Im DEM-Modus fehlt ein Oberflächenschnitt, deshalb wird kein irreführendes Footprint-Polygon gezeigt.
- **Kreuzraster** erzeugt zwei vollständige Rasterdurchgänge mit 90° Unterschied als getrennte Abschnitte. Keine automatische Verbindung zwischen den Durchgängen.
- **Längste Kante** richtet Grid an der längsten Außenkante aus, auch beim ersten Übernehmen eines Umrisses. Beim Ziehen von Ecken bleibt der gesetzte Winkel erhalten. `− / +` ändern um 1°, `+90°` dreht rechtwinklig.
- **Abstände verketten** hält das aktuelle Verhältnis Foto/Bahn in beiden Richtungen fest. Nur direkte Meterabstände; im FOV-Modus steuern die Winkelüberdeckungen. Die Verknüpfung wird mit der Planung gespeichert.
- **Startort für Routenbeginn** wählt das nähere der beiden Routenenden (Grid, Linie, Korridor). Kein zusätzlicher Fotopunkt, kein automatisch berechneter Anflug, keine Änderung des Höhenbezugs. Noch keine Optimierung aus vier Startvarianten. Neue Planung setzt diesen Startort zurück.
- **Geschwindigkeit:** neue UI-Vorgaben Grid 2,6 m/s und Helix/Doppelhelix 4,3 m/s, aus den expliziten Wegpunktwerten der bereitgestellten Wunderlgasse-KMZs. Die Helix hat abweichend global 2,5 m/s; andere Referenz-Helices 5–6,1. Daher sind dies editierbare Vergleichswerte, keine universelle Optimierung. Manuelle Werte bleiben bei Flugartwechsel bestehen; „Geschwindigkeitsvorgabe“ setzt sie zurück. API-Vorgabe 3 m/s bleibt für bestehende Aufrufer erhalten.
- Status über der Karte in zwei Zeilen: Fotozahl/Strecke/Höhen und Abstände/Überdeckung. Ausführliche Modellangaben unter „Bildfeld & Berechnung“.

## Prüfung und verbleibende Ausbauschritte

Geometrie, Höhenbezug/Untergrenze, FOV-Skalierung, −70°-Projektion, Kreuzraster/Abschnittsgrenzen, Umkehrung der Route, gespeicherte Planung und WPML-Export sind durch Regressionstests abgedeckt. API-Tests prüfen Save/Reopen, Export/Archiv und Verweigerung für Kunden/fremde Projekte. Browserprüfung auf isolierter Installation bei 1280×720: Import, Ecke löschen/ziehen, automatische Reaktion, Abstandskette beidseitig, Winkelknöpfe, Höhenimport mit Fehlerfall unter Mindesthöhe, Save/Reopen, Halbkugel, Footprint, Startort und Zurücksetzen. Kein DJI-Fly-Geräte- oder Flugtest der neuen Exporte.

Offen bleiben ein Editor für beliebige vorhandene Missions-KMZs mit Erhalt aller Aktionen und neuen Archivversionen, Vermessungs-/Hindernismodelle samt Unsicherheiten sowie Kreisraster/Circlegrammetry. Die [UgCS-Referenz](https://www.sphengineering.com/news/ugcs-circlegrammetry-drone-mapping-efficiency-dalhousie-research) beschreibt überlappende Kreise mit nach innen gerichteten Schrägaufnahmen; die berichtete Zeitersparnis ist kein Leistungsversprechen für unseren Wegpunkt-Einzelbildablauf. Benutzerverwaltung/Publisher-Anmeldung folgt getrennt.

**Entwürfe:** „Entwurf speichern“ sichert die bearbeitbare Planung mit Revision, Umriss, Kamera, Parametern, Projekt und Höhenreferenzen. Unter „Planung, Name & Projekt“ wieder öffnen. Dabei entsteht noch keine Missions-KMZ; Export oder „KMZ-Abschnitte ins Archiv“ sind eigene Aktionen.

## Kalotte und Gelände · 0.5.1

- POI bleibt ein gemeinsames Ziel: entweder relativ zum tatsächlichen Start oder über DEM am **POI**, plus Offset. Kameraneigung wird nach der Höhenanpassung neu berechnet; die Scheitelaufnahme bleibt senkrecht nach unten. Fehlt der Start/DEM oder liegt der Scheitel nicht über dem POI, wird abgelehnt.
- Die FOV-Abtastung erfolgt auf der Ausgangskalotte. Nach DEM wird die größte Blickwinkeländerung zwischen aufeinanderfolgenden Fotopunkten erneut berechnet und als kleinste Winkelüberdeckung entlang angezeigt. Windungsüberdeckung ist ausdrücklich ein **Vor-Gelände-Wert**; es gibt keinen falschen nachträglichen Prozentnachweis. Bei unterschrittener Zielüberdeckung erscheint ein Hinweis.
- Zusätzliche Gelände-Stützpunkte lösen keine Fotos aus. Vorhandene Grenzen für Steigen/Sinken, Hangwinkel, Exporthöhe, Abschnittslänge und importierte Mindesthöhe gelten weiterhin. Es gibt keine neue Kurvenglättung oder Beschleunigungsoptimierung; gute Fliegbarkeit ist noch durch Gerätetest zu prüfen.
- Standard bleibt die normale Kalotte ohne DEM. Manuelles Kippen in mehreren Achsen ist **nicht implementiert**. Es würde zusätzlich Bodenabstand, POI-Ausrichtung und eine separate senkrechte Aufnahme erfordern.
- Tests: Helix/Doppelhelix jeweils als Kalotte und Halbkugel auf synthetischem Hang, beide POI-Bezüge, Scheitel/Nadir, FOV-Ausgabe nach DEM, reproduzierbarer Entwurf, fehlende Daten und Mindesthöhen-Unterschreitung. Kein Flugtest.
- Vergleich: [Map Creator Elevation Mode](https://map-creator.com/windows.htm) nennt OpenTopoData, veröffentlicht dort aber keine vollständige Helix-Transformationslogik. Wir behaupten keine identische Implementierung. [DJI Waypoint Flight](https://repair.dji.com/help/content?customId=01700007343&lang=en&re=US&spaceId=17) beschreibt mögliche Höhenabweichungen bei dicht liegenden Wegpunkten und hoher Geschwindigkeit; aus einer Referenz-KMZ übernommene Geschwindigkeit ist deshalb keine Flugfreigabe.

### Map-Creator-Vergleich am Mac · 8.11.2026

Direkt in der geöffneten App getestet: Mavic 4 Pro, Double Helix, 15 m Fotoabstand, gleiche Kreisgeometrie. Kontrollstände wurden mit **Calculate Grid** berechnet und als separate KMZs zurückgelesen. Originaldateien blieben erhalten; private Referenzmissionen sind nicht im Repository.

- Bei 50 m Reglerwert: ohne Elevation 50,0–111,6 m exportierte Höhe; mit Elevation 58,8–174,1 m. Die horizontalen Koordinaten aller 118 Placemarks sind identisch, 117 verschiedene Indizes. Der Höhenbezug im Export ist `relativeToStartPoint`. Das belegt eine Höhenanpassung in diesem Fall, keine starre Rotation. Die vollständige interne Höhenformel wurde nicht hergeleitet.
- Ohne Gelände ergaben die zusätzlich durch Ziehen/Loslassen berechneten 10-/30-m-Stände 10,0–83,6 bzw. 30,0–103,6 m. Die vertikale Form darf deshalb nicht ungeprüft als konstante Halbkugel plus Reglerwert angenommen werden.
- Bloß gesetzte Reglerwerte konnten noch eine alte Route exportieren. Ziehen/Loslassen und explizites **Calculate Grid** vor dem Vergleich vermeiden diesen Testfehler. Unsere automatische Vorschau muss entsprechend immer aus aktuellen Parametern rechnen.
- SkySplat an/aus änderte im verglichenen Export keine Positionen oder Höhen. Mit SkySplat: `startRecord`, initiales `gimbalRotate`, 117 `gimbalEvenlyRotate`, `stopRecord`; ohne SkySplat: 118 `takePhoto`. SkySplat ist hier ein Video-/Kameraaktionsmodus, nicht die Geländeverformung. Unser Planer exportiert weiterhin Einzelbilder; daraus folgt keine SkySplat-Kompatibilitätszusage.
- Referenztempo 4,1 m/s beobachtet, nicht als pauschaler Standard für neu berechnete Routen übernommen. Kein Geräte- oder Flugtest dieser Vergleichsmissionen.

## Aufnahme: Einzelbilder oder Video (Generator 0.5.2)

Oben neben der Kamera **Aufnahme → Video** wählen. Die Auswahl bleibt im Entwurf und in der Planungsdatei erhalten; ältere Entwürfe verwenden weiterhin Einzelbilder. Der Export bleibt eine DJI-Waypoint-KMZ, die Bridge überträgt sie wie bisher.

- **Video-Grid / Kreuzraster:** nur zwei Wegpunkte je Bahn (Anfang/Ende), ohne Foto-Zwischenpunkte. Fotoabstand und Längsüberlappung sind ausgeblendet. Bahnenabstand direkt in Metern oder über nominale Querüberdeckung steuert die Dichte. Löcher und getrennte Durchgänge erzeugen weiterhin getrennte Abschnitte.
- **Gelände:** zusätzliche Navigationspunkte erhalten die exportierten Höhen. Sie sind keine Fotoauslöser. **Helix:** Kurvenstützpunkte bleiben, damit die Bahn ihre Form behält.
- **Abschnittsteilung:** im Video-Modus zählt das Limit alle Wegpunkte inklusive Gelände, höchstens 200. Wiederholung am Übergang bezieht sich auf Wegpunkte. Jeder Abschnitt ist eigenständig mit Aufnahmestart/-stopp, kein automatisch fortlaufender Flug über die Abschnittsgrenzen.
- **Aktionen in beiden KMZ-XMLs:** zuerst `gimbalRotate`, dann `startRecord` am ersten Punkt; `gimbalEvenlyRotate` mit `betweenAdjacentPoints` und Ziel-Pitch am folgenden Punkt; `stopRecord` am letzten Punkt. Keine `takePhoto`-/`hover`-Aktionen. Geräte-/Nutzlastkennung kommt wie bisher aus der Referenzmission. Basis: [DJI-WPML-Aktionsdokumentation](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html) und die bereitgestellte Map-Creator-Video-KMZ. DJI-Cloud-Dokumentation ist kein Nachweis für die Unterstützung jeder Consumer-Drohne.
- **Flugverhalten:** gerade Wegpunktsegmente und bisherige Stopp-Wendemodi bleiben erhalten. Durchgehende Videoaufnahme bedeutet daher noch keinen Flug ohne Abbremsen an Wegpunkten. Zeitangaben sind reine Streckenzeit ohne Beschleunigung, Stopps, Aufnahmestart oder An-/Rückflug. Keine zusätzlichen Fotopausen.
- **Bildabdeckung:** FOV/Seitenverhältnis müssen dem tatsächlichen Videomodus entsprechen. Foto-Kameraprofile sind keine Zusage für Videocrop oder Videoauflösung. Überdeckung zeigt nur die nominale Planungsgeometrie; die spätere Frame-Auswahl hängt von Geschwindigkeit, Bildrate und Extraktion ab. Im Video-Modus wird deshalb keine Foto-GSD als Videoauflösung ausgegeben.
- **Vor dem Einsatz:** Auflösung, Bildrate und Kameraeinstellungen in DJI Fly prüfen. Aufnahme und Gimbal-Aktionen am Zielgerät testen. Bisher sind Parser, Export und UI geprüft, kein echter Video-Flug. Der Planer extrahiert keine Frames; dafür dienen nachgelagerte Programme.

Regressionen decken Einzelbild-Kompatibilität, Bahnendpunkte, Gelände-Stützpunkte, Helix-Geometrie, lokale Aktionsindizes, Aufnahmestart/-stopp je Abschnitt, Modi in gespeicherten Entwürfen und den Archivkonflikt bei geändertem Modus ab. Originalmissionen werden nicht verändert.

### Höhenreferenz aus einer Archivmission

Unter **Höhenpunkte aus Erkundungsflug → DJI-KMZ aus dem Webarchiv** eine Mission mit Projektpfad wählen und **Höhenpunkte übernehmen** anklicken. Alternativ bleibt der lokale KMZ-Upload verfügbar. Es wird die neueste Version gelesen; die Quelle im Dialog trägt deren Nummer (z. B. „Erkundung · V2“). Höhenmodus, Dateigröße und Prüfsumme werden ebenso wie beim Upload geprüft. Kunden und fremde Projektbereiche bleiben ausgeschlossen.

Die Punkte werden zusammen mit Quellname und SHA-256 im Planungsentwurf gespeichert. Es entsteht keine neue Archivmission und kein dynamischer Link: Eine spätere Quellversion überschreibt die übernommene Referenz nicht. Zum Aktualisieren erneut übernehmen; dies setzt Auswahl, Startbezug und Sicherheitsabstand auf die Importvorgaben zurück. Danach Startbezug bestätigen, relevante Punkte auswählen, Sicherheitsabstand einstellen und Mindesthöhe übernehmen/aktivieren.

Höhen beim Darüberfahren: Flugpunkte zeigen die Höhe relativ Start; bei DEM-Anpassung zusätzlich „ca. … m AGL (über DEM)“. Die Punkte des Erkundungsflugs zeigen die Quellstarthöhe beziehungsweise den bestätigten Höhenversatz zum neuen Start. Ohne Bodenhöhe am Punkt steht ausdrücklich „AGL unbekannt“.
Auf gestrichelten Referenzsegmenten nennt der Tooltip beide Endpunkte und deren Höhen (H1 → H2). Er interpoliert keine Höhe zwischen diesen Punkten.


## Oberfläche 0.6 · große Karte, kompakte Werkzeuge, gegliederte Seitenleiste

Umbau der Bedienung nach dem Vorbild Litchi Hub v2 (Branch `claude/planner-ui-litchi`); Fluggeometrie, Höhen-/FOV-Berechnung, Sicherheitsprüfungen, Exportaktionen und Datenformate sind unverändert. Alle Regeln liegen gekapselt unter `.mission-planner` in `style.css`; Markup und Zusammenbau in `planner.js`. Gestaltungsregeln für den Abgleich mit dem KMZ-Editor: [PLANNER-UI-DESIGN.md](PLANNER-UI-DESIGN.md).

- **Kopf:** Titel, Badge „Geräteprüfung offen“, Schrittwahl „Planen · Prüfen & Exportieren“ als Pillen, Schließen immer erreichbar. Kein globaler Scrollweg; nur die Seitenleiste scrollt.
- **Obere Werkzeugleiste:** Flugart, Kamera, Aufnahme (Foto/Video) und Abstandsmodus in einer Zeile; rechts Kreuzraster, „Längste Kante“ und „+90°“ (nur Grid).
- **Slider-Leiste über der Karte:** je Flugart Foto-/Bahnenabstand oder Überlappungen bzw. FOV-Winkelüberdeckungen, Höhe(n), Radius, Ausrichtung mit ±1°, Korridorbreite, Gimbal-Pitch bei manueller Neigung, „Abstände verketten“. Zahlenfelder direkt neben den Slidern; Einheit und Höhenbezug (relativ Start / über Grund) in der Beschriftung.
- **Seitenleiste** (310 px, am Griff in der Breite veränderbar, per Knopf ausblendbar) mit Abschnitten: *Planung & Projekt* (Entwurf, Name, Projekt, Umriss importieren, OSM), *Aufnahme & Kamera* (Abstände, Bildfeld & Berechnung, Kameraneigung, Geschwindigkeit mit Vorgabe, Fotos je Abschnitt, Übergänge, unter „Erweitert“ Kameramodell und Zusatzpause), *Muster & Objekt* (Form, Aufnahmefläche, Abstand, POI-Zielhöhe, Windungen, Drehrichtung, Flugseite, POI-Höhenbezug), *Gelände & Start* (Höhenbezug, tatsächlicher Startpunkt als Höhennullpunkt, DEM-Einstellungen, getrennt davon „Startort für Routenbeginn“ nur für die Reihenfolge), *Erkundungsflug · Höhenreferenz* (Archiv-KMZ oder lokale KMZ, Startbezug, Sicherheitsabstand, Punktauswahl, Mindesthöhe). Zahlenfelder haben −/+ Knöpfe mit der Schrittweite des Feldes.
- **Karte:** Umriss-Werkzeuge als senkrechte Gruppe links oben (Polygon, Linie, Kreis, Ecken bearbeiten, Rückgängig, Umriss verwerfen; beim Zeichnen Fertig/Abbrechen), Ansichtsschalter rechts oben (Karte, 3D, Höhenprofil, Footprint, Seitenleiste; in 3D Drehen/Neigen), Zoom unten rechts. Ergebnis-Pille unten in der Karte: Fotos/Wegpunkte · Strecke · Höhen und Abstände/Überdeckung; Fehler bleiben dort und im Fuß sichtbar.
- **Prüfen & Exportieren:** Seitenleiste zeigt Zusammenfassung, Abschnitte, Geräteprofil und Export (KMZ, Archiv, Planungsdatei); Karte, 3D und Profil bleiben sichtbar, Umriss-Werkzeuge sind ausgeblendet. Umschalten über die Schrittwahl oder den Fußknopf.
- **Schmale Fenster:** Karte oben, Seitenleiste darunter in der Höhe veränderbar; Werkzeuggruppen unten an der Karte. Geprüft bei 1280 × 720, 1440 × 900, iPad quer 1180 × 820 und 430 × 860.

Geprüft im Browser mit synthetischen Daten: Polygon zeichnen, automatische Vorschau, Flugart Helix per Kreis, Foto→Video, 3D/Profil, ungültige Höhe sperrt Export und erholt sich, Entwurf speichern und erneut laden, Höhenreferenz aus Archivmission mit Tooltip auf Punkt und gestricheltem Segment, Geländemodus-Umschaltung. Keine Browser-Konsolenfehler außer erwarteten 400-Antworten auf absichtlich ungültige Eingaben. Weiterhin kein DJI-Fly-Geräte- oder Flugtest dieser Planergeneration.
