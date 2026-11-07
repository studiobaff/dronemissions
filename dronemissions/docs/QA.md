# Prüfung

Stand: 7. November 2026. PHP 8.3.36 auf FreeBSD, getrennte Entwicklungsdatenbank. Oberflächen-Überarbeitung geprüft mit PHP 8.3.6 (Linux, eingebauter Webserver) und headless Chromium über Playwright.

## Automatisierte API-Prüfung

`tests/integration.py` verwendet nur die Python-Standardbibliothek und erzeugt synthetische WPML-KMZ-Dateien. Geprüft werden:

- Autoreneinstellung: nur Eigentümer, HTML-Escaping, Manifest-Autor, neutrale Standardeinstellung.
- Nicht angemeldeter Zugriff und ungültiger Zugangsschlüssel.
- Projekte, Unterordner und Ablehnung zyklischer Ordnerbeziehungen.
- WPML-Einlesen, Wegpunktzahl, Routenlänge, SVG-Vorschau und Ablehnung defekter KMZ.
- Native LCHM/LCHZ: Dateisignatur, beide ZIP-Offset-Varianten von LCHZ, Originaldownload, Platzhalter ohne erfundene Route und exakter Inhalt im Archivpaket.
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

Desktop (1440 px), Tablet (1280 px) und iPhone-13-Viewport werden mit der tatsächlichen PHP-Anwendung und headless Chromium geprüft; Testdaten sind synthetisch. Skriptgesteuert durchlaufen: Login mit falschem und richtigem Schlüssel, Bibliothek mit Ergebniszeile, Suche, Typfilter und Sortierung, leere Zustände (keine Treffer, leeres Archiv), Missionsdialog mit Route, Höhenprofil-Hover und Dateifakten, Speichern von Metadaten, Übersichtskarte, Planungspunkt per Kartenklick anlegen und über den Bestätigungsdialog löschen, Upload per Dateiauswahl mit automatischem Namen, Projektordner anlegen, Freigabelink erstellen und in einer zweiten Sitzung als Lesefreigabe öffnen (Upload-Schaltflächen ausgeblendet), Archivansicht, mobile Seitenleiste als Schublade. Dabei dürfen keine JavaScript-Fehler auftreten; der einzige erwartete Konsoleneintrag ist der HTTP-401 des absichtlich falschen Logins.

Zusätzlich ein Härtetest mit Worst-Case-Daten: 150 Zeichen langer Missionsname mit Emoji, 150 Zeichen langer Dateiname ohne Leerzeichen, 100 Zeichen langer Projektordnername mit Unterordner, 1 000 Zeichen Notizen, 3 000 Zeichen Punktbeschreibung, Mission ohne Projektordner mit einem Buchstaben als Namen, 400 Wegpunkte, Höhe 1234,5 m, Koordinaten auf der Südhalbkugel. Titel werden auf zwei bis drei Zeilen begrenzt, Pfade mit Auslassung gekürzt, Dateinamen und Prüfsummen umbrechen innerhalb des Wortes, Zähler werden korrekt in Einzahl und Mehrzahl ausgegeben.

Kartenkacheln von basemap.at, OpenStreetMap und Esri wurden in der Cloud-Prüfumgebung durch neutrale Platzhalter ersetzt, weil die Kachelserver dort nicht erreichbar sind. Kachelladung und Quellenangabe müssen vor einem Release auf einer Installation mit Internetzugang und auf echten Telefonen geprüft werden (Hover-Zustände, Tastatur, sichere Bildschirmränder lassen sich nicht emulieren).

Diese Prüfungen ersetzen keinen Test in DJI Fly, an einem Controller oder im Flug. Es wurde keine USB-Übertragung oder Flugausführung geprüft.
