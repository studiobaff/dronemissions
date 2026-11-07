# Drone Missions Bridge 0.4

Lokale Mac-Oberfläche für DJI-KMZ-Dateien. Der Kern verwendet für Android separat installiertes ADB; der iPad/iPhone-Adapter verwendet pymobiledevice3 über USB. Keine Injector-Bibliotheken werden gebündelt.

## iPad / iPhone

1. Gerät per Kabel verbinden, entsperren und diesem Computer vertrauen.
2. DJI Fly vollständig schließen. Andere Übertragungsprogramme für den Vergleich schließen.
3. In der Bridge Geräte suchen und das iPad/iPhone auswählen. Missionen lesen zeigt die DJI-Fly-Namen.
4. Eine gültige DJI-KMZ auswählen, Namen eingeben und optional ein Hintergrundbild wählen. Ohne Bild wird die Route schräg von der Seite mit den echten Wegpunkthöhen gezeichnet (Bodenabdruck, Fallinien, Höhenverlauf in der Linienfarbe), damit Helix oder Halbkugel erkennbar bleiben. Flache Routen werden bis dreifach überhöht, das steht dann im Bild. DJI Fly zeigt das Bild fest; drehen lässt es sich dort nicht.
5. „Vorschau prüfen“ zeigt den dritten Schritt mit großer Titelvorschau und Zielgerät.
6. DJI Fly vollständig schließen, das im dritten Schritt bestätigen und „Jetzt übertragen“ wählen. Nach vollständiger Sicherung wird ein neuer Eintrag angelegt. Bestehende Missionen werden nicht ersetzt oder gelöscht.
7. DJI Fly öffnen; Mission, Speichern und Cloud-Synchronisation prüfen.

Die automatische Sicherung liegt im Benutzer-Anwendungsdatenordner; der Button in der App öffnet ihn. Datenbank und Missionsdateien werden zurückgelesen. Die Dateiprüfung ist ausdrücklich keine Bestätigung eines nutzbaren Flugplans oder einer erfolgreichen DJI-Cloud-Synchronisation.

Bestätigter Gerätetest vor Einbau der Oberfläche: neue Helix mit 117 Punkten, Name, eigener Titelvorschau, Speichern und Cloud-Synchronisation. Das gebaute App-Paket wurde am angeschlossenen iPad auf Geräteerkennung und lesenden Datenbankzugriff geprüft. Eine erneute vollständige Übertragung aus der Oberfläche muss mit DJI Fly geprüft werden.

Die Vorschau wird vor dem ersten Import erzeugt. DJI Fly kann sie beim Speichern ersetzen; eine nachträglich ausgetauschte Vorschau einer bestehenden Mission wurde im Nutzertest nicht zuverlässig erneut über die Cloud verteilt. WLAN ist noch nicht implementiert.

## Android / RC Pro 2

Die Bridge bringt ein eigenes ADB mit (`vendor/platform-tools`, Android Platform-Tools 37.0.1 für macOS, Prüfsumme in `provenance.json`, Lizenz in `NOTICE.txt`) und nutzt es nur, wenn die Prüfsumme stimmt. Ein eigener Pfad lässt sich unter „Protokoll & Einstellungen“ wählen; „Eingebautes ADB“ setzt zurück. Für einen Windows-Build muss der Ordner vorher durch die Windows-Platform-Tools mit passender `provenance.json` ersetzt werden.

Zielgerät ausdrücklich auswählen, Missionen lesen und einen entbehrlichen lokalen Testeintrag wählen. Der bestehende Missionsbestand wird vollständig gesichert. Übertragen wird eine geprüfte KMZ plus Titelvorschau; der DJI-Fly-Listenname kann derzeit nicht direkt gesetzt werden. Bei den Gerätetests war nach dem Austausch ein RC-Neustart erforderlich, bevor Speichern und das Erzeugen einer neuen Vorschau funktionierten. Es gibt deshalb keine Erfolgsmeldung allein aufgrund des Dateikopiervorgangs.

Das experimentelle Anlegen einer unregistrierten Android-UUID wird in der Oberfläche nicht mehr angeboten. Keine automatische Cloud-Synchronisation oder Löschung.

## Webarchiv

Der Tab „Webarchiv“ meldet sich mit dem Zugangsschlüssel des Eigentümers an der Archiv-API an (`archive.py`, nur Standardbibliothek, HTTPS erforderlich außer auf localhost). Der Schlüssel bleibt nur für die laufende Sitzung im Speicher und wird nie gespeichert; die Archiv-Adresse wird gemerkt. Die Liste zeigt Vorschaubild, Projektpfad, Format, Version, Wegpunkte und Strecke, mit Suche und den Filtern „Nur DJI-KMZ“ und „Archivierte zeigen“. „Für Übertragung verwenden“ lädt die Originaldatei, vergleicht die SHA-256-Prüfsumme mit dem Archiv, legt sie im Anwendungsdatenordner unter `archive/` ab und setzt sie als Quelle im Tab „Übertragen“ ein. LCHM/LCHZ und MPROJ sind bearbeitbare Quellprojekte; für DJI Fly wird ein gültiger DJI-KMZ-Export benötigt. Der Weg vom Archiv zur Drohne: Archiv → Bridge → DJI Fly auf iPad oder Fernsteuerung → Fluggerät beim Start der Mission.

## Entwickeln und bauen

Python 3.9+, Abhängigkeiten aus requirements-desktop.txt installieren, dann `python bridge/build_desktop.py`. Windows muss unter Windows gebaut und getestet werden; ein Windows-Paket wurde hier nicht gebaut. Der lokale Mac-Build ist ad-hoc signiert und nicht notarisiert.

Tests: `python3 -m unittest discover -s bridge/tests -v` (34 Tests, offscreen ohne Gerät; `test_archive.py` nutzt einen lokalen Nachbau der Archiv-API). Die automatisierten Testdaten sind synthetisch. Die iOS-Tests prüfen unter anderem die Wiederherstellung nach einer unklaren Datenbank-Umbenennung und das unveränderte Erhalten bestehender Datensätze.

GPL-3.0-or-later; siehe LICENSE und THIRD_PARTY.md. Öffentliche Binärreleases benötigen den passenden vollständigen Quellstand und Lizenzunterlagen.

## Oberfläche 0.4

Vier Tabs statt drei Schritte: **Gerät & Missionen** (Gerät oben wählen, „Missionen lesen“ zeigt eine große Liste mit Vorschaubild, Wegpunkten, Bestand und Kennung; darunter die Aktionen „Neu anlegen“ und „Ausgewählte ersetzen“, letztere nur für lokal vorhandene Missionen), **Webarchiv** (siehe oben), **Übertragen** (Modus Neu/Ersetzen, bei Ersetzen die Karte des Zieleintrags, KMZ, Name, großes Vorschaubild; „Vorschau prüfen“ führt zur Prüfseite mit großem Titelbild, Zusammenfassung und der ausdrücklichen Bestätigung „DJI Fly ist geschlossen“ vor „Jetzt übertragen“) und **Protokoll & Einstellungen** (Protokoll mit Zeitstempel, Sicherungen öffnen, ADB-Pfad).

Plattformregeln in der Oberfläche: Auf Android ist „Ersetzen“ der geprüfte Weg, „Neu anlegen“ ist als experimentell gekennzeichnet (Dateien geprüft, DJI-Fly-Sichtbarkeit nicht bestätigt). Auf iPad/iPhone ist „Neu anlegen“ geprüft, „Ersetzen“ nutzt `ios.apply_new(replace=…)` und ist als noch nicht am Gerät geprüft gekennzeichnet. Jede Änderung an Quelle, Name, Bild, Ziel oder Gerät verwirft den vorbereiteten Transfer; die Prüfseite muss erneut durchlaufen werden. Gerätefunktionen (`core.py`, `ios.py`, `preview.py`) sind gegenüber 0.3 unverändert.

## Übertragungskopie bei doppeltem Schlusspunkt

Map Creator schreibt bei manchen Exporten den letzten Wegpunkt zweimal mit derselben `wpml:index`-Nummer, gleichen Koordinaten und gleicher Höhe; der einzige Unterschied ist der Abbiegemodus (erst Durchfahren, dann Stopp). `inspect_kmz` lehnt doppelte Nummern weiterhin ab. `prepare_source` erkennt genau diesen Fall über `sanitize_kmz`, behält den Placemark mit dem Stopp, verwirft den Zwilling und schreibt eine Übertragungskopie `<Name> (bereinigt).kmz` plus Journal in den Anwendungsdatenordner unter `cleaned/`. Die Originaldatei bleibt unverändert, Wegpunkte werden nicht umnummeriert, Aktionsgruppen und ihre Indexverweise bleiben erhalten. Jedes andere Duplikat (abweichende Koordinaten, mehr als zwei Treffer, Duplikat nicht am Ende, keine Stopp-Variante) bleibt ein Fehler. Die Oberfläche zeigt die Bereinigung in der Dateizeile an; der Transferplan enthält `originalSource`. Dass das Webarchiv eine Datei liest, bestätigt keine DJI-Fly-Kompatibilität; die Übertragung muss am Gerät geprüft werden.

## Windows 11

Der Code ist plattformunabhängig (PySide6). Das Paket muss auf einem Windows-Rechner mit demselben `build_desktop.py` gebaut werden; PyInstaller baut nicht quer. Zusätzlich nötig: die Windows-Version der Android Platform-Tools (ADB) und für iPad/iPhone die Apple-USB-Treiber (iTunes oder die Apple-Devices-App), damit pymobiledevice3 das Gerät sieht. Ein Windows-Paket wurde noch nicht gebaut oder getestet.
