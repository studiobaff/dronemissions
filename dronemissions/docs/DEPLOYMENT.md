# Deployment und Betrieb

## Verzeichnisstruktur

```text
HTTPS-Webroot/dronemissions/      Inhalt von public/
privat/dronemissions/            config.json, missions.sqlite
privat/dronemissions/blobs/      unveränderte Original-KMZ und JPEG-Vorschauen
privat/dronemissions/sessions/   PHP-Sitzungen
privat/dronemissions/tmp/        temporäre ZIP-Exporte
```

Der Standardpfad des privaten Verzeichnisses ist in `public/lib.php` definiert. Für andere Installationen `DRONEMISSIONS_PRIVATE` im CLI- und PHP-FPM-Prozess setzen. Der Cookie-Pfad ist `/dronemissions/`; bei Installation unter anderem URL-Pfad in `api.php` anpassen. Betrieb über HTTPS ist erforderlich. Nur `public/` veröffentlichen; insbesondere `tools/`, Tests und private Daten bleiben außerhalb.

## Einmalige Einrichtung

1. PHP-Erweiterungen und Upload-Limits prüfen.
2. Privaten Ordner für den PHP-Benutzer vorsehen. Verzeichnisse Modus 0700, sensible Dateien 0600; keine Schreibrechte für andere Benutzer.
3. Einen zufälligen Zugangsschlüssel mit mindestens 24 Zeichen über einen Passwortmanager oder kryptographischen Zufall erzeugen. Sicher verwahren.
4. Eine JSON-Zugangsdatei außerhalb des Webroots mit Modus 0600 anlegen. Den Schlüssel über stdin an das CLI-Setup übergeben, nie als Kommandozeilenargument.

```sh
env DRONEMISSIONS_PRIVATE=/absolute/private/dronemissions \
  php /absolute/source/dronemissions/tools/setup.php < /private/setup-access.json
```

Das Setup verweigert die Änderung einer bestehenden Konfiguration. Die Zugangsdatei nach sicherer Übernahme in den Passwortmanager entfernen oder geschützt aufbewahren. Nicht in Tickets, Chat oder Git kopieren.

5. Den Inhalt von `public/` einschließlich `vendor/images/` in das Zielverzeichnis kopieren.
6. HTTPS-Aufruf, Login, Secure-/HttpOnly-Cookie und leere Bibliothek prüfen. Keine realen Kundendaten für öffentliche Screenshots verwenden.

## Eigener Name

Nach der Anmeldung unter **Einstellungen → Autor / Betreiber** den eigenen Namen eintragen. Alternativ kann die JSON-Eingabe des Setups neben `password` ein optionales `authorName` enthalten. Standard ist ein leeres Feld und damit eine neutrale Oberfläche. Neue Archivpakete enthalten diesen Namen im Manifest-Feld `author`. Bestehende Originaldateien werden dadurch nicht verändert.

## Updates und Backups

Vor Updates Datenbank und `blobs/` gemeinsam sichern. Bei laufender Anwendung für SQLite die SQLite-Backup-API oder `VACUUM INTO` verwenden; nicht einfach eine aktive Datenbankdatei kopieren. Konfiguration separat verschlüsselt sichern. Zugriffsrechte des Backups wie beim Original beschränken.

Updates ersetzen nur Anwendungsdateien; private Daten nie überschreiben. Die aktuelle Version verändert das Schema nicht automatisch. Bei späteren Schemaänderungen müssen explizite Migrationen ergänzt werden. Nach dem Update PHP-Syntax und Login/Downloads prüfen.

Archivieren löscht keine Originaldateien. Es gibt bewusst keinen öffentlichen API-Endpunkt zum endgültigen Löschen von Missionen oder Versionen. Abgebrochene Uploads können nicht referenzierte Blobs hinterlassen; deren Bereinigung ist eine administrative Aufgabe nach geprüftem Backup.

## Zugang und Freigaben

Eigentümer haben Zugriff auf die ganze Bibliothek. Lesefreigaben erlauben Projektansicht und Downloads, Bearbeitungsfreigaben zusätzlich Änderungen innerhalb des Projekts und seiner Unterordner. Bearbeiter können keine Freigaben verwalten und das freigegebene Hauptprojekt nicht verschieben. Archivierung entzieht keinen Zugriff; dafür Freigabe widerrufen. Ein Widerruf sperrt auch bereits angemeldete Freigabesitzungen bei der nächsten API-Anfrage. Bereits heruntergeladene Dateien können nicht zurückgerufen werden.

Freigaben lassen sich jederzeit in „Freigaben“ widerrufen und laufen nach 30 Tagen ab. Der Link wird nur beim Erstellen angezeigt. Keine Freigabelinks in öffentlichen Screenshots speichern.

Für einen Schlüsselwechsel die Konfiguration administrativ aktualisieren und bestehende Sitzungen ungültig machen; dafür gibt es aktuell keinen Webdialog. Produktionszugang niemals für Integrationstests verwenden.

### Geozonen und Adresssuche

`zones.php` lädt den zum aktuellen Datum gültigen ED-269-Datensatz ausschließlich von der offiziellen Austro-Control-Seite. Die Originaldaten liegen im privaten Cache, nicht im öffentlichen Repository. Die Quelle wird beim Einschalten geprüft und höchstens stündlich erneut abgefragt; bei Ausfall wird ein vorhandener Stand ausdrücklich als nicht aktualisiert angezeigt. Die Karte berücksichtigt Datumsbereiche, wertet tägliche Aktivierungszeiten und NOTAMs aber nicht live aus. Sie erteilt keine Flugfreigabe. Abgelaufene und künftige Zeiträume sind standardmäßig ausgeblendet.

Die ausdrücklich ausgelöste Adresssuche verwendet Photon / OpenStreetMap für Österreich. Keine Autovervollständigung: Der Suchbegriff wird erst beim Absenden an den Dienst übertragen. Antworten werden 24 Stunden privat zwischengespeichert; gleichzeitige Anfragen und mehr als eine neue Anfrage pro Sekunde werden abgewiesen. `geocoderURL` in der privaten `config.json` kann auf eine eigene HTTPS-Photon-Instanz zeigen. Keine Zugangsdaten in die öffentliche Konfiguration schreiben. Die öffentlichen Photon-Server bieten keine Verfügbarkeitsgarantie; siehe https://github.com/komoot/photon#demo-server.

Prüfungen: `php tests/zones.php`, `php tests/address.php`, `node tests/zones.js` (PHP-Zonentest benötigt eine dedizierte Installation über `DRONEMISSIONS_PRIVATE`).

### Standortdetails, Wetter und Geländehöhe

`location.php` verwendet für die Wetterprognose GeoSphere Austria C-LAEF AlpeAdria 1 km (CC BY 4.0) und für die Geländehöhe Open Topo Data / Copernicus EU-DEM 25 m. Koordinaten werden für Wetter auf drei, für die Höhe auf vier Nachkommastellen gerundet. Suchtreffer öffnen die Standortansicht; vorhandene Missionen bleiben unverändert. Wetterangaben sind Modellwerte, Wind/Böen gelten für 10 m über Grund. Angezeigte Tages-Minima und -Maxima beziehen sich nur auf die ausdrücklich angegebenen verfügbaren Prognosestunden. Niederschlag wird als Menge, nicht als Wahrscheinlichkeit dargestellt.

Wetter wird privat eine Stunde, Gelände einen Monat zwischengespeichert. Open Topo Data wird auf eine neue Abfrage pro Sekunde und höchstens 1.000 pro UTC-Tag begrenzt. Beide Dienste können unabhängig ausfallen; die Zonendetails bleiben nutzbar. Gespeicherte Rückfallwerte werden als solche gekennzeichnet. EU-DEM ist ein Geländemodell, keine Startplatzvermessung.

Zonenstatus wird ausschließlich aus auswertbaren ED-269-Datums- und Wochenzeitplänen abgeleitet. UTC-Zeitpläne werden für die Anzeige in Europe/Vienna umgerechnet. Fehlende Betriebszeiten (z.B. MCTR LOXT im ED-269-Datensatz) bleiben ausdrücklich unbekannt. Es werden keine AIP-Betriebszeiten aus Drittseiten übernommen. Feiertage, NOTAMs und Sonderaktivierungen werden nicht automatisch ausgewertet; die aktuelle AIP und DroneSpace sind verlinkt.

### Ordner löschen und Seitenleiste

Nur Eigentümer können einen leeren Projektordner endgültig löschen. Der Server prüft direkte Unterordner, alle zugeordneten Missionen einschließlich archivierter und Planungspunkte sowie Name/Elternordner gegen den geöffneten Stand. Die Löschung widerruft Freigaben dieses Ordners innerhalb derselben Transaktion. Befüllte Ordner können weiterhin archiviert werden. Die einklappbare Icon-Leiste speichert ihre Ansicht ausschließlich lokal im Browser.


### Naturschutz-Freigabekarte

Pro Mission kann ein unabhängiger Startplatz (`takeoff_lat`, `takeoff_lng`) gesetzt werden. Die Aufnahme bleibt Wegpunkt 2 des aktuellen Originals. Fehlt dieser bei einem nativen Projekt, wird kein Aufnahmepunkt erfunden; die Karte nennt ihn nicht verfügbar. `map_capture_type` speichert ausschließlich das Kartensymbol (Foto, Video, Panorama, Kugelpanorama). Beide Metadatenaktionen prüfen Schreibscope und Missionsrevision; Originale und Versionen bleiben unverändert. Startplätze erscheinen als Kreis mit H, Aufnahmen mit dem gewählten Symbol, verbunden durch eine gestrichelte Zuordnungslinie.

Die neue Eigentümeraktion „Kartenlink erstellen“ erstellt eine 30 Tage gültige, widerrufbare Lesefreigabe mit `presentation=map`. Der Server liefert nur Startplatz/Aufnahmepunkt, Namen und erlaubte projektspezifische Referenzebenen. Weitere Flugwegpunkte, Dateien, Notizen und Anhänge bleiben gesperrt. Alte Bibliotheksfreigaben behalten ihre bisherige Präsentation.

`nature.php` fragt zehn Kategorien des offiziellen UBA-Datensatzes „Naturschutzgebiete Österreich 2025“ über dessen ArcGIS-Dienst ab, seitenweise und auf den sichtbaren österreichischen Ausschnitt beschränkt. Daten liegen sieben Tage im privaten Cache. Bekannte Quelldatenlücken (u.a. UNESCO-/Ramsar-Abgrenzungen) bleiben bestehen. Ab Zoomstufe 9 und bei begrenzter Ausschnittsgröße wird geladen; unvollständige oder gescheiterte Kategorien werden angezeigt. Quelle/Attribution: Umweltbundesamt auf Basis der INSPIRE-Dienste aller neun Bundesländer, CC BY 4.0. Schutzgebiete sind keine pauschalen Drohnenverbote und keine behördliche Freigabe.

„PDF herunterladen“ erzeugt lokal im Browser ein A4-PDF mit dem sichtbaren Kartenausschnitt, aktiven Vektorflächen/Referenzen, H-/Aufnahmesymbolen und gestrichelter Verbindung; Folgeseiten enthalten die WGS84-Koordinatenliste. Die Naturschutzkategorien müssen vollständig für den Ausschnitt geladen sein. Kartenkacheln benötigen CORS-Freigabe für den Export; bei einem nicht exportierbaren fremden Hintergrund erscheint ein Fehler statt eines leeren PDFs. Daten und Bilder werden für den PDF-Export nicht an einen weiteren Server hochgeladen.

Zusätzlich behoben: Die ED-269-Kategorienfunktion rief sich selbst rekursiv auf; eine Filterstelle verwendete `filters.hasdmZoneCategory`. Dies wurde als „Geozonen nicht verfügbar“ abgefangen, obwohl der Server Daten lieferte. Regressionstest prüft Luftfahrt-, Naturschutz- und unbekannte Kategorien.

## Panorama planner and mission list

Flight types `panorama` and `sphere` use two explicitly drawn flight positions:
WP1 is an approach position at mission height, WP2 owns the hovering photo sequence.
The separate ground takeoff marker is never inserted into executable KMZ files.
Panorama exports use sequential WPML `rotateYaw`, `gimbalRotate`, `hover` and
`takePhoto` actions in both XML documents (DJI common-element documentation:
https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html).
Horizontal/vertical sampling follows camera FOV and the selected overlap.
Sphere mode includes nadir and reports the unphotographed zenith gap; stitching is
external. DEM-following panorama approaches are explicitly rejected; plan those
separately rather than silently flattening them. Device/firmware acceptance still
requires controller tests; structural export tests are not flight validation.

`map_sort` is an additive nullable mission column. Reordering is scope-checked,
revision-checked and transactional, with natural filename ordering as the fallback.
List positions `(1)`, `(2)` are distinct from stable mission labels such as `008`.
Reordering, moving a ground marker and refreshing reference layers preserve map
center and zoom. Single-mission maps export only that mission, its original route,
waypoints and optional ground start as PNG or PDF, with nature polygons and credits.

Validation: `tests/planner.php`, `tests/planner-api.py`, `tests/panorama_api.py`,
plus browser checks for grip drag, checkboxes, start-marker drag, unchanged tile
URLs/placement after saving, and a rendered two-page single-mission PDF.
