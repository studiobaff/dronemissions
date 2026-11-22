# DJI-Fluglogs: Servereinrichtung vorbereiten

Stand 22.11.2026: Dateiimport und direkter DJI-Cloud-Abruf sind implementiert. Der App Key dient der Entschlüsselung; das DJI-Konto wird separat im Browser verbunden. Ablauf, Tests und Grenzen: [DJI-CLOUD.md](DJI-CLOUD.md).

## Entwicklerkonto

1. https://developer.dji.com/user/apps/ öffnen, anmelden und gegebenenfalls die Entwicklerregistrierung abschließen.
2. Create App → **Open API**. Dies registriert einen Dienst, installiert keine Desktop-App. Für die Flight-Record-Entschlüsselung ist dieser Typ vorgesehen.
3. Vorgeschlagener Name: **Studio Baff Flight Logs**. Beschreibung: **Private server-side analysis of our DJI flight records to compare mission duration and battery usage.** Die angebotene Kategorie passend auswählen.
4. DJI-Bedingungen selbst prüfen/bestätigen; Anwendung per Aktivierungs-E-Mail freischalten.
5. App Key in den Anwendungsdetails holen. Im Webarchiv **Fluglogs → DJI-App-Key einrichten** hinterlegen. Kein Passwort und keinen Bridge-Geräteschlüssel verwenden.

Quelle: https://github.com/dji-sdk/FlightRecordParsingLib/blob/master/README.md (DJI, Abschnitt App Key). Logversionen ab 13 benötigen Keychains: https://github.com/lvauvillier/dji-log-parser/blob/master/dji-log-parser/src/lib.rs .

## Ablage und Zugriffsgrenzen

Der App Key liegt in `dji-log-key.json` unter `dm_private()`, außerhalb des Webroots, mit Dateimodus 0600. Atomarer Austausch und Revisionsprüfung schützen parallele Änderungen. Keine zusätzliche Verschlüsselung dieser Datei; Dateisystemschutz und private Backups müssen sie wie die vorhandene Serverkonfiguration schützen. Die API liefert nur Konfigurationsstatus und Revision, nie den Schlüssel. Nur Eigentümersitzungen dürfen speichern/entfernen. Projektfreigaben und Bridge-Schlüssel haben keinen Zugriff. Das Speichern allein sendet nichts an DJI. Der Schlüssel wird beim ersten verschlüsselten Fluglog gegen die DJI-Keychain-API verwendet.

## Geprüfte Servervoraussetzungen

FreeBSD mit PHP, cURL, OpenSSL, SQLite und ZIP vorhanden; Rust/Cargo nicht vorhanden. Ein unauthentifizierter Abruf des DJI-CAPTCHA-Endpunkts vom Server lieferte HTTP 200 und image/jpeg. Kein Login versucht, kein Passwort empfangen, keine Kontodaten geladen. Erreichbarkeit ist kein Nachweis eines funktionierenden Konto-Syncs.

## Noch mit dem Nutzer abzunehmen

Nach Aktivierung des App Keys: DJI Cloud im Webarchiv verbinden, CAPTCHA selbst lösen, Flugliste laden und einen Importdurchlauf starten. Erst damit ist der reale Kontozugang und die Verarbeitung echter Mavic-Logs geprüft. Die bisherigen Tests verwenden synthetische verschlüsselte Logs und simulierte DJI-Antworten.
