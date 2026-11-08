# Vorschaubilder einer Mission

Im Missionsdialog öffnet **Vorschau einstellen** den Bildeditor. Schließen und Speichern bleiben beim Scrollen erreichbar.

* **3D-Ansicht:** Drehen, Neigen, Zoom und Verschiebung X/Y; die gespeicherten Wegpunkthöhen bestimmen die Darstellung. Ohne ausgelesene Route ist ein eigenes Foto erforderlich. Die Zeichnung ist kein Gelände- oder Gebäudemodell.
* **Karte / Luftbild:** basemap.at für Österreich, Kartentyp, Kartenzoom, zusätzlicher Bildzoom und X/Y. Internet erforderlich; die Quellenangabe bleibt im exportierten Bild. Bei einem Ladefehler wird das Speichern gesperrt.
* **Eigenes Foto:** JPEG/PNG bis 8 MB und 16 Megapixel, Zoom und X/Y zum Zuschneiden. Das normalisierte Ausgangsbild bleibt für spätere Anpassungen erhalten.

Der Titel steht unten im dunklen Band, mit Rand und maximal zwei Zeilen. **Als neues Vorschaubild speichern** ergänzt die Bildauswahl und aktiviert das neue Bild. **Als Titelbild verwenden** aktiviert ein bereits gespeichertes Bild. **Einstellungen laden** stellt dessen Parameter wieder her; bei 3D/Karte wird dabei die aktuell geöffnete Missionsroute verwendet. Bilder lassen sich auch einzeln herunterladen.

## Daten und Rechte

Bilder sind unabhängig von `versions`: weder Speichern noch Auswählen legt eine Missionsversion an. KMZ/Projektdateien, ihre Prüfsummen, Wegpunkte und Versionsnummern bleiben unverändert. Eine Missionsrevision wird für Konfliktschutz erhöht; der Sortierzeitpunkt der Mission ändert sich nicht.

`mission_previews` speichert Bild- und optional Ausgangsfoto-Prüfsumme, Einstellungen, Erstellzeit und die zur Generierung verwendete Missionsversion. `mission_preview_selection` enthält die aktive Auswahl. Dateien liegen als normalisierte JPEGs im privaten Blob-Verzeichnis, maximal 100 gespeicherte Bilder pro Mission. Bestehende Bilder in alten Versionsmetadaten bleiben erhalten und dienen ohne neue Auswahl weiterhin als Vorschau.

Die Bibliothek und das aktuelle Archivpaket verwenden das aktive Bild. Explizit angeforderte ältere Missionsversionen verwenden ihre ursprüngliche Vorschau. Kundenlinks bekommen weiterhin nur den freigegebenen Standort, keine private Bildsammlung, Flugroute oder Originale. Eigentümer und berechtigte Bearbeitungslinks dürfen Vorschaubilder verwalten; Quellversionen und Ausgangsfotos müssen zu derselben Mission gehören. Alle Änderungen prüfen Sitzung, CSRF, Projektbereich und Revision.

## Prüfung

`tests/previews.py` führt auf einer ausschließlich synthetischen Loopback-Installation Speicherung, Wechsel, Ausgangsfoto-Wiederverwendung, Prüfsummen/Versionskonstanz, Paketexport, veraltete Revisionen, ungültige Bilder/Einstellungen und Kunden-/Projektgrenzen durch. Die GitHub-Web-Checks starten diese Installation und führen zusätzlich die bestehende Archiv-Integration aus.

Geräteverhalten ist getrennt: DJI Fly kann ein importiertes Titelbild nach dem Speichern durch einen eigenen Kartenausschnitt ersetzen. Dieser Webeditor ändert keine Mission auf einem angeschlossenen Gerät.

## Ordner im Archiv

Archivieren behält die Projektzuordnung bei. Die Archivansicht gruppiert Missionen und archivierte Planungspunkte deshalb nach dem vollständigen Ordnerpfad. Ordnergruppen lassen sich per Maus oder Tastatur auf- und zuklappen; die aufgeklappten Gruppen werden während der Sitzung gemerkt. Eine Namenssuche klappt passende Gruppen auf. Auch leere archivierte Ordner bleiben sichtbar. Aktive Projektansichten weisen auf ausgeblendete archivierte Missionen hin; ein nicht leerer Ordner lässt sich weiterhin nicht versehentlich löschen.
