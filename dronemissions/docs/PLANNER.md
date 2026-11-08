# Web-Missionsplaner · erste Fassung

Unter **Mission planen** einen Umriss wählen, Flugmuster/Kamera einstellen, Route berechnen und prüfen. Der Planer ist für Eigentümer und Bearbeitungsfreigaben verfügbar; Kundenlinks erhalten keine Planungen oder Flugrouten.

## Grundlagen und Muster

- Projektbezogene Kartenreferenzen einschließlich QGIS-Umrissen als Grundlage auswählen. GeoJSON, KML oder KMZ direkt laden; QGIS zuvor nach **WGS84/EPSG:4326** exportieren. Eine fremde Projektion wird nicht automatisch geraten. Multi-Geometrien werden für die Auswahl in Einzelobjekte aufgeteilt.
- Polygon, offene Linie oder Kreis auf der Karte zeichnen. Beim Kreis Mittelpunkt und Radiuspunkt anklicken. Eckpunkte lassen sich verschieben.
- OSM-Gebäude im aktuellen Ausschnitt bis 4 km² laden. Erst der ausdrückliche Knopfdruck sendet den Ausschnitt an den öffentlichen Overpass-Dienst (bei Ausfall für höchstens 0,25 km² die OpenStreetMap-API). OSM ist für bestehende, erfasste Gebäude gedacht; zukünftige Baukörper aus QGIS übernehmen. Nur geschlossene Gebäude-Ways, keine vollständigen Multipolygon-Relationen. Quelle und ODbL-Hinweis bleiben sichtbar. Der Rückfall auf die OpenStreetMap-API wurde mit einem kleinen öffentlichen Ausschnitt geprüft; die Verfügbarkeit des externen Dienstes bleibt abhängig vom Anbieter.
- **Grid:** Nadir-Raster auf Polygonen, einschließlich Löchern. Punkte werden innerhalb der Fläche erzeugt. Verbindungen, die durch ausgesparte Flächen führen würden, erzeugen getrennte Abschnitte; An-/Rückflug bleibt gesondert zu prüfen.
- **Kreis, Helix, Doppelhelix:** Zentrum aus Punkt oder Umriss, Radius manuell oder aus Umriss plus Abstand. Ein Zylinder behält seinen Radius bei Höhenänderung. Die Halbkugel bindet ausdrücklich die obere Höhe an untere Höhe plus Radius; ihr Radius und Baukörperabstand werden nach oben kleiner. Doppelhelix erzeugt getrennte Aufwärts-/Abwärtsflüge, um 180° versetzt. Zusätzliche Abtastung begrenzt auch am Scheitel den räumlichen Fotoabstand.
- **Fassade / POI-Polygon:** versetzte Bahnen an Linien bzw. Polygonseiten, Höhenreihen und Kamera zur Wand oder zum Mittelpunkt. Bei offenen Linien Flugseite ausdrücklich wählen; bei Polygonen wird außen geplant. Jede Wand ist getrennt, Ecken werden nicht automatisch umflogen.

## Kamera, Überlappung und Höhen

Vorgaben für die Hauptkameras von Mini 4 Pro, Mini 5 Pro, Air 3, Air 3S, Mavic 3 Series und Mavic 4 Pro; zusätzlich eigenes Profil. Quellen sind die verlinkten DJI-Spezifikationen:
[Mini 4](https://www.dji.com/mini-4-pro/specs), [Mini 5](https://www.dji.com/mini-5-pro/specs), [Air 3](https://www.dji.com/air-3/specs), [Air 3S](https://www.dji.com/air-3s/specs), [Mavic 3](https://www.dji.com/mavic-3/specs), [Mavic 4](https://www.dji.com/mavic-4-pro/specs).

Das nominelle DJI-FOV wird als diagonales Bildfeld interpretiert und mit dem gewählten Bildseitenverhältnis auf Breite/Höhe aufgeteilt. Für eine ebene, senkrecht aufgenommene Fläche gilt: Bildfeld-Diagonale = `2 × Abstand × tan(FOV/2)`; Foto-/Bahnenabstand = passende Bildfeldseite × `(1 − Überlappung)`. Bei Nadir-Rastern zählt die Höhe über der eingegebenen ebenen Aufnahmefläche; bei Fassaden der Wandabstand. Bildformat, Crop, Verzeichnung und anderes Objektiv brauchen ein angepasstes Profil. GSD und Bildabdeckung sind nominelle Modellwerte.

Für Kreis/Helix und schräge POI-Aufnahmen sind die Abstände Richtwerte. Eine echte 3D-Überlappung ist ohne Objektoberflächenmodell nicht nachgewiesen; Prozentwerte dürfen nicht als gemessene Oberflächenüberdeckung verstanden werden. Der Planer zeigt zusätzlich den größten tatsächlichen Wegpunktabstand und die erzeugte Höhenspanne.

**Alle Exporthöhen sind relativ zum tatsächlichen Startpunkt.** Keine automatische DEM-/AGL-Anpassung in dieser ersten Fassung. Aufnahmeflächenhöhe, Flug-/Zielhöhen und Radius sind getrennte Parameter. Das 3D-Bild enthält Route und Grundriss, kein Gelände-/Gebäudemodell. Der Rückkehr-/Startablauf verwendet die Geräteeinstellungen; er ist nicht als geprüfte Hindernisroute enthalten. An-/Rückflug und Hindernisfreiheit werden nicht automatisch berechnet.

## Abschnitte, Speichern und Export

Pro Aufnahmepunkt: anhalten, Gimbal ausrichten, kurz warten, ein Foto, Fotopause. Foto- und Wegpunktzahl stimmen in diesem Exportmodell bewusst überein; Zeitserien/Mehrfachbelichtungen werden nicht vorgetäuscht. Einstellbare Fotoobergrenze bis 200 je Abschnitt (Vorgabe 150), bis zehn wiederholte Aufnahmen an Übergängen. Geometrisch getrennte Wände/Helices erhalten keine automatische Verbindung. Anzahl, Strecke und geschätzte Zeit erscheinen gesamt und pro Abschnitt; Pausen sind berücksichtigt, An-/Rückflug nicht.

**Planung speichern** erhält Umriss, Kamera und Parameter mit Konflikterkennung sowie Generatorversion und Routenprüfsumme. Eine abweichende Neuberechnung muss erneut gespeichert werden, bevor sie archiviert werden kann. Gespeicherte Planungen sind über die Liste und bei erzeugten Archivmissionen über **Planung bearbeiten** erreichbar. Eine `.dmplan.json` lässt sich herunterladen und erneut öffnen. `mission_plans` und `mission_plan_runs` liegen in der privaten SQLite-Datenbank und werden bei der ersten Verwendung angelegt. Projektordner mit Planungen lassen sich nicht versehentlich löschen.

Für den DJI-WPML/KMZ-Export eine vorhandene, passende DJI-KMZ aus dem Archiv als **Geräteprofil** wählen. Es werden nur überprüfte Geräte-/Nutzlastkennungen übernommen; keine fremden Wegpunkte oder unbekannten Modellnummern geraten. Kameraprofil und Gerät müssen tatsächlich zusammenpassen. WPML-Referenz: [DJI Common Elements](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html).

Ein Abschnitt liefert KMZ, mehrere liefern ZIP mit einzelnen KMZs, Planungsdatei und Hinweisen. Beim Archivieren entstehen Teilmissionen im **gleichen Projekt**, verknüpft mit der gespeicherten Mutterplanung; keine neuen Projektordner pro Datei. Wiederholtes Archivieren desselben gespeicherten Stands und Geräteprofils erzeugt keine Duplikate. Änderungen der Planung bleiben getrennt von unveränderlichen bisherigen KMZ-Versionen.

## Prüfstand und nächste Schritte

Geprüft: reine Rechenregressionen, Grid-Löcher, Fassadenabstand/-richtung, Kreis/Helix/Doppelhelix/POI-Polygon, unveränderter Zylinderradius, echte Halbkugel, stabiles erneutes Öffnen, adaptive Schrittweite am Scheitel, Fotoaufteilung, Aktionsreihenfolge und lokale Nummern. API-Tests decken gespeicherte Planungen/CAS, Projektgrenzen, Kundenrechte, Archiv-Idempotenz sowie Einzel-KMZ und Abschnitts-ZIP ab. Der Browser-Rundlauf mit synthetischem QGIS-Polygon ergab 496 Fotos in vier Teilen, identisch nach Wiederöffnen. Der heruntergeladene ZIP wurde zusätzlich mit dem strengen Bridge-Parser geprüft.

**Noch kein DJI-Fly-Gerätetest dieser neu erzeugten Exporte und kein Flugtest.** Die frühere erfolgreiche Archiv-Wiederherstellung bestätigt diesen neuen Exporter nicht. DEM-/AGL-Anpassung, schräges perspektivisches Grid, direkter CRS-Transformator, Video-/Zeitserien und ein Hindernismodell bleiben weiterer Ausbau. Grenzen der ersten Fassung: 5-km-Umriss, 1000-m-Kreisradius, 5000 Aufnahmepunkte und 100 Abschnitte.

Die aktuellen Map-Creator-Anforderungen und Referenzen bleiben in [MISSION-PLANNING.md](MISSION-PLANNING.md). Der neue Rechenkern ist eigenständig implementiert; es wurde kein vollständiger Desktop-App-Code aus einem Installationspaket übernommen.
