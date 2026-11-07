# Drone Missions Bridge 0.3

Lokale Mac-Oberfläche für DJI-KMZ-Dateien. Der Kern verwendet für Android separat installiertes ADB; der iPad/iPhone-Adapter verwendet pymobiledevice3 über USB. Keine Injector-Bibliotheken werden gebündelt.

## iPad / iPhone

1. Gerät per Kabel verbinden, entsperren und diesem Computer vertrauen.
2. DJI Fly vollständig schließen. Andere Übertragungsprogramme für den Vergleich schließen.
3. In der Bridge Geräte suchen und das iPad/iPhone auswählen. Missionen lesen zeigt die DJI-Fly-Namen.
4. Eine gültige DJI-KMZ auswählen, Namen eingeben und optional ein Hintergrundbild wählen. Ohne Bild wird die Route gezeichnet.
5. „Vorschau prüfen“ zeigt den dritten Schritt mit großer Titelvorschau und Zielgerät.
6. DJI Fly vollständig schließen, das im dritten Schritt bestätigen und „Jetzt übertragen“ wählen. Nach vollständiger Sicherung wird ein neuer Eintrag angelegt. Bestehende Missionen werden nicht ersetzt oder gelöscht.
7. DJI Fly öffnen; Mission, Speichern und Cloud-Synchronisation prüfen.

Die automatische Sicherung liegt im Benutzer-Anwendungsdatenordner; der Button in der App öffnet ihn. Datenbank und Missionsdateien werden zurückgelesen. Die Dateiprüfung ist ausdrücklich keine Bestätigung eines nutzbaren Flugplans oder einer erfolgreichen DJI-Cloud-Synchronisation.

Bestätigter Gerätetest vor Einbau der Oberfläche: neue Helix mit 117 Punkten, Name, eigener Titelvorschau, Speichern und Cloud-Synchronisation. Das gebaute App-Paket wurde am angeschlossenen iPad auf Geräteerkennung und lesenden Datenbankzugriff geprüft. Eine erneute vollständige Übertragung aus der Oberfläche muss mit DJI Fly geprüft werden.

Die Vorschau wird vor dem ersten Import erzeugt. DJI Fly kann sie beim Speichern ersetzen; eine nachträglich ausgetauschte Vorschau einer bestehenden Mission wurde im Nutzertest nicht zuverlässig erneut über die Cloud verteilt. WLAN ist noch nicht implementiert.

## Android / RC Pro 2

Zielgerät ausdrücklich auswählen, Missionen lesen und einen entbehrlichen lokalen Testeintrag wählen. Der bestehende Missionsbestand wird vollständig gesichert. Übertragen wird eine geprüfte KMZ plus Titelvorschau; der DJI-Fly-Listenname kann derzeit nicht direkt gesetzt werden. Bei den Gerätetests war nach dem Austausch ein RC-Neustart erforderlich, bevor Speichern und das Erzeugen einer neuen Vorschau funktionierten. Es gibt deshalb keine Erfolgsmeldung allein aufgrund des Dateikopiervorgangs.

Das experimentelle Anlegen einer unregistrierten Android-UUID wird in der Oberfläche nicht mehr angeboten. Keine automatische Cloud-Synchronisation oder Löschung.

## Archiv

Das Webarchiv lässt sich über den Button öffnen. Derzeit KMZ im Browser herunterladen und über die Dateiauswahl der Bridge auswählen. Eine direkte Archiv-API-Verbindung und automatische Updates sind noch nicht eingebaut. LCHM/LCHZ und MPROJ sind bearbeitbare Quellprojekte; für DJI Fly wird ein gültiger DJI-KMZ-Export benötigt.

## Entwickeln und bauen

Python 3.9+, Abhängigkeiten aus requirements-desktop.txt installieren, dann `python bridge/build_desktop.py`. Windows muss unter Windows gebaut und getestet werden; ein Windows-Paket wurde hier nicht gebaut. Der lokale Mac-Build ist ad-hoc signiert und nicht notarisiert.

Tests: `python3 -m unittest discover -s bridge/tests -v`. Die automatisierten Testdaten sind synthetisch. Die iOS-Tests prüfen unter anderem die Wiederherstellung nach einer unklaren Datenbank-Umbenennung und das unveränderte Erhalten bestehender Datensätze.

GPL-3.0-or-later; siehe LICENSE und THIRD_PARTY.md. Öffentliche Binärreleases benötigen den passenden vollständigen Quellstand und Lizenzunterlagen.

## Oberfläche 0.3

Drei getrennte Schritte: Gerät, Mission, Übertragen. Gerätenamen sind lesbar; ADB-Pfad, zusätzliche Sicherung und Protokoll liegen ausschließlich in den Einstellungen. Die Ersetzungsliste mit Bild und Punktzahl erscheint nur bei Android. UUIDs stehen in den Tooltips. Die letzte Seite ist die konkrete Bestätigung vor einer Übertragung.
