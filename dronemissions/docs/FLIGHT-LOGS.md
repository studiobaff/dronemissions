# Fluglogs und Missionsvergleich

Der Import liest vollständige OpenDroneLog-CSV-/JSON-Exporte. Unabhängig implementierter Formatadapter; kein Quellcode aus OpenDroneLog übernommen. Formatquelle: https://github.com/arpanghosh8453/open-dronelog/blob/main/src/lib/exportUtils.ts (buildCsv/buildJson, geprüft am 22.11.2026).

Im Webarchiv „Fluglogs“ öffnen, Projekt auswählen und bis zu 20 Dateien prüfen. Importieren speichert Originalexport und normalisierte Daten im privaten Archiv. Die Prüfung allein speichert nichts. Kein Versand an DJI/OpenDroneLog. Aktuell keine native DJI-TXT-Entschlüsselung oder direkte DJI-Cloud-Anmeldung.

Gemeldete Flugdauer wird getrennt vom Telemetriezeitraum gehalten. JSON-Strecken in Fuß werden in Meter umgerechnet; CSV-Metadaten total_distance_m bleiben SI. Akkuverbrauch ist Start minus Ende in Prozentpunkten, optional mAh; fehlende Abdeckung oder ein großer Anstieg verhindern eine verlässliche Verbrauchszahl. Keine Summierung von Prozentwerten unterschiedlicher Akkus. Fotoereignisse sind steigende isPhoto-Flanken, keine garantierte Zahl gespeicherter Bilder.

Automatische Zuordnung nur bei genau einem räumlichen Kandidaten, identischem Namen und mindestens 95 % der ausgewerteten Missionspunkte innerhalb 35 m der Logspur. Die Vorschau zeigt Zuordnung und Alternativen vor dem Import. Das ist eine Heuristik, kein Nachweis der Flugausführung. Andere Fälle bleiben manuell zuordenbar. Mehrere Logs können derselben Mission zugeordnet werden. Jeder Link hält die konkrete KMZ-Version und deren Planzeit/Strecke fest. Spätere Dateiversionen ändern den historischen Vergleich nicht. Die GPS-Anzeige ist auf maximal etwa 1200 Punkte reduziert, die numerische Akkuauswertung verwendet alle eingelesenen Samples.

Grenzen: maximal 16 MB/Datei, 50.000 Samples; Zusammenfassungs-CSV und fremde Formate werden abgelehnt. Wiederholte Importe werden pro Projekt über Zeit/Drohne/Akku/Dauer/Spur erkannt, ohne Startzeit nur über Dateiinhalt. Zeitangaben werden unverändert aus dem Export angezeigt; keine angenommene Zeitzone. Flugzeit einschließlich An-/Rückflug ist nicht direkt mit reiner KMZ-Routenzeit gleichzusetzen. Keine automatische Anpassung der Akkuplanung.

Zugriff: Eigentümer und berechtigte Projekteditoren. Kundenansichten und Bridge-Geräteschlüssel erhalten keine Fluglogs. Zuordnung prüft Log- und Missionsrechte. Originalmissionen und -versionen bleiben unverändert.

Validierung: synthetische API-Tests für CSV/JSON, Einheiten, Akkuwerte/Lücken, Duplikate, mehrdeutige Routen, Versionsbindung und Freigabegrenzen. Browsertest für Prüfen, Import, manuelle Zuordnung und Kartenvergleich. Noch keine echten Fluglogs bereitgestellt; kein DJI-Konto verbunden und kein echter Flug damit abgeglichen.

DJI Cloud: https://github.com/arpanghosh8453/Drone-Cloud-Sync ist eine Tauri/Rust-Desktop-Anwendung, keine direkt installierbare PHP-Webkomponente. Serverbetrieb benötigt zusätzlich einen Authentifizierungs-/Download-Dienst, interaktive CAPTCHA-Anmeldung, geschützte Sitzungsablage und einen DJI-TXT-Parser. Diese Erweiterung ist nicht Bestandteil des Dateiimports.
