# Nächster Ausbau: Missionsplanung auf künftigen Projektumrissen

Anforderung des Eigentümers, 8. November 2026: Missionen müssen anhand geplanter, noch nicht gebauter Objekte entstehen können. Aktuelle Satellitenbilder zeigen diese Umrisse nicht. Projektbezogene Kartenreferenzen sind deshalb die Planungsgrundlage, nicht nur Dekoration.

## QGIS als Vorbereitung

QGIS kann die vorhandenen Planungsdaten vorbereiten und georeferenzierte Geometrien als WGS84-GeoJSON oder KML/KMZ liefern. Diese Referenzen lassen sich bereits projektbezogen importieren. Der aktuelle Shapefile-Import erwartet WGS84; er transformiert UTM-/Landeskoordinaten noch nicht selbst. Ein zukünftiger direkter Shapefile-Import benötigt nachvollziehbare CRS-Erkennung aus `.prj` und eine geprüfte Transformation. Unbekannte Koordinatensysteme nicht raten.

Der spätere Planer soll Linien/Flächen aus einer Referenz als Planungsgeometrie auswählen können: freie Wegpunkte und Panorama-Ziele, Raster entlang geplanter Flächen, Trassenkorridore sowie Kreis/Helix um geplante Baukörper. Satellitenbilder bleiben optionaler Hintergrund. Flughöhen, Startbezug, POI-Höhen und An-/Rückflug sind getrennte Parameter; eine 2D-Planlinie enthält diese Angaben nicht automatisch.

## Map-Creator als mögliche Grundlage

Geprüftes öffentliches Repository: https://github.com/hdrpano/map-creator . `code/map_creator.py` enthält Geometriehilfen, Raster- und POI-Kreisgenerator sowie KML-/Litchi-CSV-Export. `LICENSE.txt` ist MIT mit Copyright Kilian Eisenegger; bei Übernahme Lizenz und Hinweis erhalten. Das README unterscheidet die offenen Beispiele von der vollständigen Desktop-Anwendung mit möglicherweise separaten Bedingungen. Die öffentliche Beispielimplementierung ist kein vollständiger DJI-WPML/KMZ-Webplaner.

Noch nicht implementiert: Browser-Planungswerkzeuge, direkte Referenzgeometrie-Übernahme, ein neuer geprüfter DJI-KMZ-Exporter, Trassen-/Helixgenerator und eigene CRS-Transformation. Planungsergebnis später als editierbares Projekt plus ausführbare KMZ im selben Archiveintrag speichern, mit bestehenden Vorschauen und Bridge-Übertragung. Diese Notiz verspricht keinen bereits fertigen Planer.
