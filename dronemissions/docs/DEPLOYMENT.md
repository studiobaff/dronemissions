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

## Updates und Backups

Vor Updates Datenbank und `blobs/` gemeinsam sichern. Bei laufender Anwendung für SQLite die SQLite-Backup-API oder `VACUUM INTO` verwenden; nicht einfach eine aktive Datenbankdatei kopieren. Konfiguration separat verschlüsselt sichern. Zugriffsrechte des Backups wie beim Original beschränken.

Updates ersetzen nur Anwendungsdateien; private Daten nie überschreiben. Die aktuelle Version verändert das Schema nicht automatisch. Bei späteren Schemaänderungen müssen explizite Migrationen ergänzt werden. Nach dem Update PHP-Syntax und Login/Downloads prüfen.

Archivieren löscht keine Originaldateien. Es gibt bewusst keinen öffentlichen API-Endpunkt zum endgültigen Löschen von Missionen oder Versionen. Abgebrochene Uploads können nicht referenzierte Blobs hinterlassen; deren Bereinigung ist eine administrative Aufgabe nach geprüftem Backup.

## Zugang und Freigaben

Eigentümer haben Zugriff auf die ganze Bibliothek. Lesefreigaben erlauben Projektansicht und Downloads, Bearbeitungsfreigaben zusätzlich Änderungen innerhalb des Projekts und seiner Unterordner. Bearbeiter können keine Freigaben verwalten und das freigegebene Hauptprojekt nicht verschieben. Archivierung entzieht keinen Zugriff; dafür Freigabe widerrufen. Ein Widerruf sperrt auch bereits angemeldete Freigabesitzungen bei der nächsten API-Anfrage. Bereits heruntergeladene Dateien können nicht zurückgerufen werden.

Freigaben lassen sich jederzeit in „Freigaben“ widerrufen und laufen nach 30 Tagen ab. Der Link wird nur beim Erstellen angezeigt. Keine Freigabelinks in öffentlichen Screenshots speichern.

Für einen Schlüsselwechsel die Konfiguration administrativ aktualisieren und bestehende Sitzungen ungültig machen; dafür gibt es aktuell keinen Webdialog. Produktionszugang niemals für Integrationstests verwenden.
