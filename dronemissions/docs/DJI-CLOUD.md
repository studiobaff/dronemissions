# DJI Cloud im Webarchiv

Unter **Fluglogs → DJI Cloud verbinden / abrufen** meldet sich der Eigentümer mit DJI-E-Mail, Passwort und selbst abgelesenem CAPTCHA an. Der Server lädt die Flugliste; **Neue Flüge importieren** verarbeitet noch nicht importierte bzw. fehlgeschlagene Einträge. Während dieses vom Browser angestoßenen Durchlaufs bleibt das Fenster offen. Es gibt keinen Hintergrund-Zeitplan. Ein Stop beendet nach dem laufenden Flug. Nur bereits in DJI Cloud vorhandene Flüge sind abrufbar.

Für verschlüsselte Logs ab Version 13 muss unter **DJI-App-Key einrichten** ein aktivierter DJI Open API App Key liegen. Dieser ist vom DJI-Kontopasswort und vom Mac-Bridge-Schlüssel unabhängig. Der Server holt die flugspezifischen Keychains von `dev.dji.com` und entschlüsselt mit `dji-log-parser-js` 0.5.7 (MIT, eingebettetes WASM). Die npm-Archivintegrität ist SHA-512 `Yx6eE79jgmqzZWoL8LmKXYkdAUwJa5PLJlADkkRvxt276PcTAtrj2sdJMWktmfQ7yIA5xompcGrZGu7idc441A==`. ESM-Exportdeklarationen wurden für CommonJS angepasst; WASM unverändert. Lizenz im vendorten JS und in DJI-PARSER-LICENSE.md.

## Ablauf und Zuordnung

Jeder Flug wird separat heruntergeladen, SHA-256-geprüft gespeichert, entpackt und entschlüsselt. Eine vorhandene DJI-MD5 wird gegen Download bzw. entpacktes TXT geprüft. Rohdatei und erfolgreich verwendete Keychains bleiben unter `dm_private()/dji-cloud`, damit ein Fehler ohne erneuten Download wiederholt werden kann. Normalisierte Daten verwenden dieselbe Struktur wie der Dateiimport. Das System führt keine Flüge aus und verändert keine KMZ-Dateien.

Automatische Cloud-Zuordnung benötigt genau einen Kandidaten: mindestens 95 % der ausgewerteten Missionspunkte innerhalb 35 m der Logspur, mindestens 75 % der angezeigten Logpunkte innerhalb 35 m der Missionssegmente und eine gemeldete Gesamtstrecke zwischen 85 % und 150 % der Planstrecke. Projektwahl begrenzt die Kandidaten; „Alle Projekte“ durchsucht das Archiv. Bei eindeutigem Treffer wird der Flug im Missionsprojekt gespeichert und an die konkrete KMZ-Version gebunden. Andere Flüge bleiben unzugeordnet. Das ist eine räumliche Heuristik, kein Flugnachweis; identische Routen, stark abweichende An-/Rückwege oder Teilflüge können manuelle Zuordnung brauchen. Höhen werden nicht als gemeinsame Referenz vorausgesetzt.

Mehrere reale Flüge können derselben Mission zugeordnet werden. Zeit und Akku werden pro Log verglichen; Batterie-Prozentwerte verschiedener Flüge werden nicht summiert. Der Decoder übernimmt gemeldete Flugdauer und SI-Strecke. Fehlende Batterietelemetrie wird nicht als 0 % ausgegeben. Neue/ungewöhnliche Logversionen können abgelehnt werden; dann bleiben Original und Fehlerstatus erhalten. Aktuell maximal 16 MB und 50.000 normalisierte Frames pro Flug.

## Authentifizierung und Betrieb

Nur Eigentümersitzungen dürfen Cloud-Anmeldung/Abruf ausführen; Projekteditoren, Kunden und Bridge-Schlüssel haben keinen Zugriff auf Cloud-Zugangsdaten. POST benötigt CSRF und bestehende Origin-Prüfung. CAPTCHA ist an die Browsersitzung gebunden, einmal verwendbar und fünf Minuten gültig. CAPTCHA/Login sind auf zehn Versuche pro fünf Minuten begrenzt.

Das DJI-Passwort wird nicht gespeichert. Der Sitzungstoken liegt AES-256-GCM-verschlüsselt mit separatem 0600-Masterschlüssel im privaten Verzeichnis. Der API-Schlüssel und erfolgreich erhaltene Keychains liegen mit Modus 0600 außerhalb des Webroots; sie sind nicht zusätzlich verschlüsselt. Private Backups müssen entsprechend geschützt bleiben. Statusantworten enthalten keine Schlüssel oder Tokens. „Verbindung trennen“ entfernt den gespeicherten Cloud-Token, nicht die importierten Logs. Eindeutige DJI-Sitzungsablehnung beendet die DJI-Sitzung, nicht die Webarchiv-Anmeldung. Ein ungültiger Decoder-App-Key trennt die Cloud-Sitzung nicht.

Downloads verwenden ausschließlich HTTPS zu DJI-/DJI-CDN-/AWS-Hosts, ohne automatische Weiterleitungen. Jede Weiterleitung wird erneut geprüft; DNS muss öffentliche IPv4-Adressen liefern und wird für den cURL-Aufruf festgehalten. Es gibt Größen-, Zeit- und Weiterleitungslimits. ZIPs werden im Speicher gelesen, keine enthaltenen Pfade extrahiert. Node erhält keine API-Zugangsdaten; Keychains nur über stdin. Subprozessdiagnostik und Upstream-Antworten werden nicht an den Browser durchgereicht. Ein globaler privater Lock verhindert parallele Konto-/Sync-Änderungen.

PHP benötigt cURL, OpenSSL, ZIP, SQLite und `proc_open`; Node >=18. Der vorhandene FreeBSD-Server hat Node 22; Decoder- und Core-Tests liefen dort isoliert erfolgreich. Kein Rust-Compiler und keine Mac-/Windows-App erforderlich.

## Validierung und Grenzen

Tests erzeugen einen synthetischen AES-verschlüsselten DJI-v13-Binärlog mit erfundenen Koordinaten/Seriennummern und bekannten Schlüsseln. Die echte WASM-Bibliothek liest daraus 960 Sekunden, 100→60 % und 5000→3000 mAh. API-Integration ersetzt ausschließlich den DJI-Netztransport in einer temporären Webkopie; sie prüft CAPTCHA, Anmeldung, Flugliste, Download, echte Entschlüsselung, Zuordnung zur KMZ-Version, Wiederholung ohne erneuten Download, Duplikate, verschlüsselte Tokenablage, Ablauf und Berechtigungen. Der Browserablauf verwendet simulierte DJI-Antworten. Netzwerk-/Pfadgrenzen und Mehrdeutigkeit sind separat geprüft.

Ein erfolgreicher Test mit einem echten DJI-Konto bzw. echten Mavic-3/Mavic-4-Logs ist erst nach der Anmeldung des Nutzers möglich. Die private DJI-Konto-Schnittstelle kann sich ändern; Erreichbarkeit des CAPTCHA allein beweist keinen vollständigen Kontoabruf. Keiner der synthetischen Tests wird als echter Kontotest ausgegeben.

Protokollreferenz: https://github.com/arpanghosh8453/Drone-Cloud-Sync . Eigenständiger PHP-Adapter; keine Desktop-Anwendung oder deren Quelltext übernommen. Decoder: https://github.com/lvauvillier/dji-log-parser . Entwicklerregistrierung: https://github.com/dji-sdk/FlightRecordParsingLib/blob/master/README.md .
