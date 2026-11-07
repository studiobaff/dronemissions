# Prüfung

Stand: 7. November 2026. PHP 8.3.36 auf FreeBSD, getrennte Entwicklungsdatenbank.

## Automatisierte API-Prüfung

`tests/integration.py` verwendet nur die Python-Standardbibliothek und erzeugt synthetische WPML-KMZ-Dateien. Geprüft werden:

- Autoreneinstellung: nur Eigentümer, HTML-Escaping, Manifest-Autor, neutrale Standardeinstellung.
- Nicht angemeldeter Zugriff und ungültiger Zugangsschlüssel.
- Projekte, Unterordner und Ablehnung zyklischer Ordnerbeziehungen.
- WPML-Einlesen, Wegpunktzahl, Routenlänge, SVG-Vorschau und Ablehnung defekter KMZ.
- Litchi-CSV: Header-/Koordinatenprüfung, Routenvorschau, Originaldownload und ZIP-Manifest.
- Unveränderter Download bytegenau gleich Upload; Originalversion nach neuem Upload erhalten.
- ZIP-Paket mit exaktem Original und korrektem Manifest-Hash.
- Versionsupload und Metadatenänderung mit veralteter Revision abgelehnt (HTTP 409).
- Planungspunkte und Revisionskonflikte.
- Getrennte Lesefreigabe/Bearbeitungsfreigabe, kein Zugriff auf andere Projekte und keine Freigabeverwaltung für Empfänger.
- Widerruf wirkt auf bereits angemeldete Freigabesitzungen.
- Archivstatus ohne Datenverlust.

Zusätzlich wurden drei vom Nutzer bereitgestellte reale KMZ-Dateien erfolgreich geparst (156, 118 und 118 Wegpunkte, jeweils eine Route). Diese Dateien und ihre Koordinaten sind nicht Bestandteil des Repositorys oder der öffentlichen Screenshots.

## Parser-Grenzfälle

`php tests/parser.php` besteht mit dem normalen PHP-Speicherlimit von 128 MiB. Die Prüfung umfasst Litchi-CSV mit gültigen und ungültigen Eingaben, mehrere Flugrouten auch mit gleicher Routenkennung, fehlende Höhen, unterschiedliche Höhenbezüge, XML-Entitäten/DOCTYPE, defektes XML, ungültige Koordinaten, leere Flugrouten, fehlende WPML-Dateien, unzulässige ZIP-Pfade und Überschreitung des Limits für entpackte Daten. Eine große Testdatei wird gestreamt erzeugt und anschließend entfernt.

## Produktionsprüfung

HTTPS-Login, anfangs leere Bibliothek und Abmelden bestanden. Das Sitzungscookie enthält Secure, HttpOnly und SameSite=Strict. Konfiguration, Datenbank, Setup und Blob-Verzeichnis sind nicht im öffentlichen Anwendungsverzeichnis vorhanden (HTTP 404). Die Produktionsbibliothek enthält keine synthetischen Testuploads.

## Browser-QA

Desktop und schmale Bildschirmansicht werden mit der tatsächlichen PHP-Anwendung geprüft. Testdaten sind synthetisch. Bibliothek, Missionsdialog, basemap.at-Kachelladung und Quellenangabe, Kartenwahl, Höhenprofil, KMZ-Upload, CSV-Vorschau und CSV-Originaldownload, Metadatenspeicherung, Archivieren/Wiederherstellen, Planungspunkte, Ordnerdialoge und Sitzungsende werden geprüft.

Diese Prüfungen ersetzen keinen Test in DJI Fly, an einem Controller oder im Flug. Es wurde keine USB-Übertragung oder Flugausführung geprüft.
