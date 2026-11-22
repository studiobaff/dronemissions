# Fluglogs und Missionsvergleich

Der Import liest vollständige OpenDroneLog-CSV-/JSON-Exporte. Unabhängig implementierter Formatadapter; kein Quellcode aus OpenDroneLog übernommen. Formatquelle: https://github.com/arpanghosh8453/open-dronelog/blob/main/src/lib/exportUtils.ts (buildCsv/buildJson, geprüft am 22.11.2026).

Im Webarchiv „Fluglogs“ öffnen, Projekt auswählen und bis zu 20 Dateien prüfen. Importieren speichert Originalexport und normalisierte Daten im privaten Archiv. Die Prüfung allein speichert nichts. Kein Versand an DJI/OpenDroneLog. Alternativ steht der direkte DJI-Cloud-Abruf mit serverseitiger TXT-Entschlüsselung bereit; siehe [DJI-CLOUD.md](DJI-CLOUD.md).

Gemeldete Flugdauer wird getrennt vom Telemetriezeitraum gehalten. JSON-Strecken in Fuß werden in Meter umgerechnet; CSV-Metadaten total_distance_m bleiben SI. Akkuverbrauch ist Start minus Ende in Prozentpunkten, optional mAh; fehlende Abdeckung oder ein großer Anstieg verhindern eine verlässliche Verbrauchszahl. Keine Summierung von Prozentwerten unterschiedlicher Akkus. Fotoereignisse sind steigende isPhoto-Flanken, keine garantierte Zahl gespeicherter Bilder.

Automatische Zuordnung nur bei genau einem räumlichen Kandidaten, identischem Namen und mindestens 95 % der ausgewerteten Missionspunkte innerhalb 35 m der Logspur. Die Vorschau zeigt Zuordnung und Alternativen vor dem Import. Das ist eine Heuristik, kein Nachweis der Flugausführung. Andere Fälle bleiben manuell zuordenbar. Mehrere Logs können derselben Mission zugeordnet werden. Jeder Link hält die konkrete KMZ-Version und deren Planzeit/Strecke fest. Spätere Dateiversionen ändern den historischen Vergleich nicht. Die GPS-Anzeige ist auf maximal etwa 1200 Punkte reduziert, die numerische Akkuauswertung verwendet alle eingelesenen Samples.

Grenzen: maximal 16 MB/Datei, 50.000 Samples; Zusammenfassungs-CSV und fremde Formate werden abgelehnt. Wiederholte Importe werden pro Projekt über Zeit/Drohne/Akku/Dauer/Spur erkannt, ohne Startzeit nur über Dateiinhalt. Zeitangaben werden unverändert aus dem Export angezeigt; keine angenommene Zeitzone. Flugzeit einschließlich An-/Rückflug ist nicht direkt mit reiner KMZ-Routenzeit gleichzusetzen. Keine automatische Anpassung der Akkuplanung.

Zugriff: Eigentümer und berechtigte Projekteditoren. Kundenansichten und Bridge-Geräteschlüssel erhalten keine Fluglogs. Zuordnung prüft Log- und Missionsrechte. Originalmissionen und -versionen bleiben unverändert.

Validierung: synthetische API-Tests für CSV/JSON, Einheiten, Akkuwerte/Lücken, Duplikate, mehrdeutige Routen, Versionsbindung und Freigabegrenzen. Browsertest für Prüfen, Import, manuelle Zuordnung und Kartenvergleich. Noch keine echten Fluglogs bereitgestellt; kein DJI-Konto verbunden und kein echter Flug damit abgeglichen.

DJI Cloud: Implementierung, Bedienung, Datenschutz und Testgrenzen stehen in [DJI-CLOUD.md](DJI-CLOUD.md).


## Map cards and reference flights

The map flyout and flight-log overview share searchable geographic cards. Multiple reference tracks have independent colors and visibility; choices are stored per project in browser storage. Source, capture mode, drone, project, date and distance filters narrow the cards. Current-project results sort first, then distance to the map center. Distances use the simplified track (approximately 120 sampled points, preserving gaps), not just takeoff. Card maps are local schematic geographic previews; the main map provides the selected basemap. Full stored tracks are fetched only when selected.

`flight-log-label` accepts `id`, `revision`, `name` and `captureType` (`unknown`, `photo`, `video`, `panorama`, `mixed`). Labels are revision-checked and scope-protected, stored separately in `flight_log_labels`, and never rewrite original files, telemetry or deduplication fingerprints. Log capture labels are explicitly manual; linked planned capture and available photo events remain separate evidence. Logs without a confirmed label remain unknown.

Validation includes API original-data preservation, stale-revision rejection, access denial and browser coverage for multiple references, distance-to-segment/viewport intersections, cards, mode filters, rename, persistence, delayed responses and narrow layouts. Existing import and mission assignment use the same underlying log records.
