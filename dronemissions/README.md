# Drone Missions

Private Web-Bibliothek für DJI-WPML-Missionen aus Litchi Hub oder Map Creator sowie ältere Litchi-CSV-Exporte. PHP 8.3, SQLite und Vanilla JavaScript; kein Node-Build erforderlich.

![Bibliothek mit synthetischen Missionen](docs/screenshots/library.png)

## Funktionen

- Projekte und Unterordner, Suche, Notizen, Archivieren und Wiederherstellen.
- DJI-KMZ und Litchi-CSV mit unveränderter Originaldatei und SHA-256-Prüfsumme; getrennte Versionen mit Konflikterkennung.
- Routen und gespeicherte Missionshöhen aus `wpmz/waylines.wpml`; mehrere Flugrouten werden getrennt dargestellt.
- basemap.at und österreichisches Luftbild, OpenStreetMap und Esri-Satellit als weitere Kartenebenen.
- Originaldatei (KMZ/CSV) und ZIP-Archiv mit Vorschau, Manifest und Prüfsummen herunterladen.
- Widerrufbare Projektfreigaben für Lesen/Download oder Bearbeiten, gültig für 30 Tage inklusive Unterordnern.
- Wiederverwendbare Planungspunkte mit Höhe, Höhenbezug, Blickrichtung, Gimbalwinkel und gewünschter Panoramaaufnahme.

![Route und Höhenprofil auf basemap.at; synthetische Daten](docs/screenshots/mission-basemap.png)

## Eigener Autor / Betreiber

Unter **Einstellungen → Autor / Betreiber** trägt der Eigentümer seinen eigenen Namen oder Firmennamen ein. Der Name erscheint auf dieser Installation und als Autor in neuen Archivpaketen. Ein leeres Feld zeigt die neutrale Oberfläche. Neue Installationen übernehmen keinen fest eingebauten Autor; optional kann beim CLI-Setup `authorName` mitgegeben werden. Die Einstellung liegt ausschließlich in der privaten Konfiguration.

## Grenzen

Dies ist ein Archiv und eine Vorschau, keine Flugfreigabe. Dateiintegrität bestätigt weder DJI-Fly-Kompatibilität noch Flugsicherheit. Das Höhenprofil zeigt gespeicherte Missionshöhen, keine Geländehöhen. Für ältere Litchi-CSV-Dateien wird der Höhenbezug ausdrücklich als nicht verifiziert angezeigt; die ursprünglichen Einstellungen bleiben in der Originaldatei erhalten. Die Strecke berücksichtigt weder Start-/Rückflug noch Aktionspausen. Planungspunkte erzeugen noch keine ausführbaren DJI-Flug- oder Panoramaaktionen. Die USB-/DJI-Fly-Bridge wird separat entwickelt; es werden hier noch keine Bridge-Downloads angeboten.

## Installation

Siehe [Deployment und Betrieb](docs/DEPLOYMENT.md). Nur `public/` wird über HTTPS ausgeliefert. Konfiguration, SQLite-Datenbank, Originaldateien und Sitzungen müssen außerhalb des Webroots liegen. Der PHP-Prozess benötigt Schreibzugriff auf dieses private Verzeichnis.

Voraussetzungen: PHP 8.3+ mit PDO SQLite, ZipArchive, SimpleXML und GD. Webserver-Limits: `upload_max_filesize=16M`, `post_max_size=20M` oder höher. Das Backend begrenzt KMZ auf 16 MiB und optionale Vorschauen auf 3 MiB/16 Megapixel.

## Prüfung

[Tests und Prüfbericht](docs/QA.md) beschreiben automatisierte API-Tests und Browser-QA. Der Integrationstest schreibt synthetische Daten und darf nur auf einer separaten, anfangs leeren Testinstallation laufen.

```sh
python3 tests/integration.py --base http://127.0.0.1:8080/dronemissions \
  --access /private/path/test-access.json --allow-test-writes
```

Die Zugangsdatei enthält `{"password":"<langer Testzugangsschlüssel>"}` und gehört weder ins Repository noch in den Webroot.

## Sicherheit und Kartenquellen

Zugangsschlüssel werden mit PHP `password_hash` gespeichert. Eigentümersitzungen laufen nach acht Stunden ab; Projektfreigaben werden bei jeder Anfrage erneut geprüft. Freigabelinks sind Zugangsdaten: Ihr Token wird im URL-Fragment übertragen, anschließend aus der Adresszeile entfernt und serverseitig nur als SHA-256-Hash gespeichert. Die Anwendung verwendet HttpOnly-/SameSite-Cookies, CSRF-Schutz und Begrenzung fehlgeschlagener Anmeldeversuche.

Kartenkacheln werden direkt von den jeweiligen Anbietern geladen; diese erhalten dabei IP-Adresse und angefragte Kartenausschnitte. Es werden keine kompletten KMZ-Dateien an Kartenanbieter gesendet. Quellen: [basemap.at](https://basemap.at/#lizenz), [OpenStreetMap](https://www.openstreetmap.org/copyright), [Esri](https://www.esri.com/). Leaflet 1.9.4 ist lokal eingebunden; Lizenz siehe `public/vendor/leaflet-LICENSE`.

Alle Beispiele und Screenshots verwenden synthetische Missionen. Kundendaten, Zugangsschlüssel und Serverkonfiguration gehören nicht in dieses Repository.
