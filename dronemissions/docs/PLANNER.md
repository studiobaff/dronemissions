# Web-Missionsplaner · erste Fassung

Unter **Mission planen** einen Umriss wählen, Flugmuster/Kamera einstellen, Route berechnen und prüfen. Der Planer ist für Eigentümer und Bearbeitungsfreigaben verfügbar; Kundenlinks erhalten keine Planungen oder Flugrouten.

## Grundlagen und Muster

- Projektbezogene Kartenreferenzen einschließlich QGIS-Umrissen als Grundlage auswählen. GeoJSON, KML oder KMZ direkt laden; QGIS zuvor nach **WGS84/EPSG:4326** exportieren. Eine fremde Projektion wird nicht automatisch geraten. Multi-Geometrien werden für die Auswahl in Einzelobjekte aufgeteilt.
- Polygon, offene Linie oder Kreis auf der Karte zeichnen. Beim Kreis Mittelpunkt und Radiuspunkt anklicken. Leaflet-Geoman 2.20.6 (MIT, lokal ausgeliefert) übernimmt Zeichnen und Bearbeiten. Polygon am ersten Punkt oder per Abschließen beenden; Bearbeiten ausdrücklich einschalten, Ecken ziehen, Zwischenmarker für neue Ecken ziehen, Rechtsklick löscht Ecken. Mindestzahl bleibt erhalten. Rücknahme und Abbrechen erhalten den vorherigen Umriss.
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

Pro Aufnahmepunkt: anhalten, Gimbal ausrichten, kurz warten, ein Foto, Fotopause. Foto- und Wegpunktzahl stimmen in diesem Exportmodell bewusst überein; Zeitserien/Mehrfachbelichtungen werden nicht vorgetäuscht. Einstellbare Fotoobergrenze bis 200 je Abschnitt (Vorgabe 150), bis zehn wiederholte Aufnahmen an Übergängen. Geometrisch getrennte Wände/Helices erhalten keine automatische Verbindung. Anzahl, Strecke und geschätzte Zeit erscheinen gesamt und pro Abschnitt; Pausen sind berücksichtigt, An-/Rückflug nicht.

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
