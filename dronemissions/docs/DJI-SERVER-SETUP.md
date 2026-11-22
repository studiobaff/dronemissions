# DJI-Fluglogs: Servereinrichtung vorbereiten

Stand 22.11.2026: OpenDroneLog-CSV/JSON-Import und Missionsvergleich sind implementiert. Der direkte DJI-Cloud-Sync ist noch nicht implementiert. Das Speichern eines App Keys aktiviert keinen Sync.

## Entwicklerkonto

1. https://developer.dji.com/user/apps/ öffnen, anmelden und gegebenenfalls die Entwicklerregistrierung abschließen.
2. Create App → **Open API**. Dies registriert einen Dienst, installiert keine Desktop-App. Für die Flight-Record-Entschlüsselung ist dieser Typ vorgesehen.
3. Vorgeschlagener Name: **Studio Baff Flight Logs**. Beschreibung: **Private server-side analysis of our DJI flight records to compare mission duration and battery usage.** Die angebotene Kategorie passend auswählen.
4. DJI-Bedingungen selbst prüfen/bestätigen; Anwendung per Aktivierungs-E-Mail freischalten.
5. App Key in den Anwendungsdetails holen. Im Webarchiv **Fluglogs → DJI-Zugang vorbereiten** hinterlegen. Kein Passwort und keinen Bridge-Geräteschlüssel verwenden.

Quelle: https://github.com/dji-sdk/FlightRecordParsingLib/blob/master/README.md (DJI, Abschnitt App Key). Logversionen ab 13 benötigen Keychains: https://github.com/lvauvillier/dji-log-parser/blob/master/dji-log-parser/src/lib.rs .

## Ablage und Zugriffsgrenzen

Der App Key liegt in `dji-log-key.json` unter `dm_private()`, außerhalb des Webroots, mit Dateimodus 0600. Atomarer Austausch und Revisionsprüfung schützen parallele Änderungen. Keine zusätzliche Verschlüsselung dieser Datei; Dateisystemschutz und private Backups müssen sie wie die vorhandene Serverkonfiguration schützen. Die API liefert nur Konfigurationsstatus und Revision, nie den Schlüssel. Nur Eigentümersitzungen dürfen speichern/entfernen. Projektfreigaben und Bridge-Schlüssel haben keinen Zugriff. Die Einrichtung sendet noch nichts an DJI und validiert den Schlüssel nicht extern.

## Geprüfte Servervoraussetzungen

FreeBSD mit PHP, cURL, OpenSSL, SQLite und ZIP vorhanden; Rust/Cargo nicht vorhanden. Ein unauthentifizierter Abruf des DJI-CAPTCHA-Endpunkts vom Server lieferte HTTP 200 und image/jpeg. Kein Login versucht, kein Passwort empfangen, keine Kontodaten geladen. Erreichbarkeit ist kein Nachweis eines funktionierenden Konto-Syncs.

## Noch umzusetzen und abzunehmen

Browseranmeldung mit selbst gelöstem CAPTCHA, geschützte serverseitige Sitzungsablage, paginierte Logauswahl, begrenzte Downloads mit geprüften Weiterleitungen und Prüfsummen, Decoder für DJI-TXT inklusive Keychain-Abruf sowie Konvertierung in die vorhandene Vergleichsstruktur. Cloud-Login und Decoder-App-Key sind getrennte Berechtigungen. Nur bereits zu DJI synchronisierte Flüge können heruntergeladen werden. Fehlende DJI-Freigaben und abgelaufene Sitzungen müssen sichtbar bleiben.

Referenz: https://github.com/arpanghosh8453/Drone-Cloud-Sync (Tauri/Rust, AGPL-3.0-only). Bisher wurde kein Quellcode daraus übernommen. Keine Desktop-App ist für die vorgesehene Browserbedienung erforderlich, aber der Server-Connector muss noch gebaut und mit einem echten Konto getestet werden.
