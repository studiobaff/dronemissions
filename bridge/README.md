# Drone Missions Bridge 0.6

Lokale Mac-Oberfläche für DJI-KMZ-Dateien. Der Kern verwendet für Android separat installiertes ADB; der iPad/iPhone-Adapter verwendet pymobiledevice3 über USB. Keine Injector-Bibliotheken werden gebündelt.

## iPad / iPhone

1. Gerät per Kabel verbinden, entsperren und diesem Computer vertrauen.
2. DJI Fly vollständig schließen. Andere Übertragungsprogramme für den Vergleich schließen.
3. In der Bridge Geräte suchen und das iPad/iPhone auswählen. Missionen lesen zeigt die DJI-Fly-Namen.
4. In Schritt 2 Missionen aus dem Webarchiv anhaken oder „KMZ-Dateien vom Mac …“ wählen; in Schritt 3 je Mission Namen prüfen und das Titelbild wählen: „3D-Ansicht“ (offline, Route schräg mit echten Wegpunkthöhen, siehe „Automatische 3D-Titelvorschau“), „Luftbild“ (Route auf dem Orthofoto, braucht Internet, siehe „Kartenquellen“; ohne Kartenquelle 3D-Ansicht) oder „Eigenes Bild“. Die Wahl wird gemerkt. DJI Fly zeigt das Bild fest; drehen lässt es sich dort nicht.
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

Der Tab „Webarchiv“ meldet sich mit dem Zugangsschlüssel des Eigentümers an der Archiv-API an (`archive.py`, nur Standardbibliothek, HTTPS erforderlich außer auf localhost). Die Archiv-Adresse wird gemerkt. Der Schlüssel bleibt standardmäßig nur für die laufende Sitzung im Speicher; mit „Schlüssel merken“ landet er wahlweise im macOS-Schlüsselbund (`security`, Dienst `DroneMissionsBridge`), in 1Password (CLI `op`, Eintrag „Drone Missions Bridge · <Host>“, CLI-Integration in der 1Password-App aktivieren) oder unter Windows DPAPI-verschlüsselt für das angemeldete Konto (`credentials.py`), nie in einer Klartextdatei. Ein gemerkter Schlüssel meldet die Bridge beim Öffnen des Tabs automatisch an; „Schlüssel vergessen“ entfernt ihn. Die Tests nutzen isolierte Einstellungen und einen Platzhalter-Schlüsselspeicher, damit sie die echten Einstellungen nicht verändern. Die Liste zeigt Vorschaubild, Projektpfad, Format, Version, Wegpunkte und Strecke, mit Suche und den Filtern „Nur DJI-KMZ“ und „Archivierte zeigen“. „Für Übertragung verwenden“ lädt die Originaldatei, vergleicht die SHA-256-Prüfsumme mit dem Archiv, legt sie im Anwendungsdatenordner unter `archive/` ab und setzt sie als Quelle im Tab „Übertragen“ ein. LCHM/LCHZ und MPROJ sind bearbeitbare Quellprojekte; für DJI Fly wird ein gültiger DJI-KMZ-Export benötigt. Der Weg vom Archiv zur Drohne: Archiv → Bridge → DJI Fly auf iPad oder Fernsteuerung → Fluggerät beim Start der Mission.

## Entwickeln und bauen

Python 3.9+, Abhängigkeiten aus requirements-desktop.txt installieren, dann `python bridge/build_desktop.py`. Windows muss unter Windows gebaut und getestet werden; ein Windows-Paket wurde hier nicht gebaut. Der lokale Mac-Build ist ad-hoc signiert und nicht notarisiert.

Tests: `python3 -m unittest discover -s bridge/tests -v` (57 Tests, offscreen ohne Gerät; `test_archive.py` nutzt einen lokalen Nachbau der Archiv-API). Die automatisierten Testdaten sind synthetisch. Die iOS-Tests prüfen unter anderem die Wiederherstellung nach einer unklaren Datenbank-Umbenennung und das unveränderte Erhalten bestehender Datensätze.

GPL-3.0-or-later; siehe LICENSE und THIRD_PARTY.md. Öffentliche Binärreleases benötigen den passenden vollständigen Quellstand und Lizenzunterlagen.

## Oberfläche 0.4

Vier Tabs statt drei Schritte: **Gerät & Missionen** (Gerät oben wählen, „Missionen lesen“ zeigt eine große Liste mit Vorschaubild, Wegpunkten, Bestand und Kennung, mit Namenssuche und Checkboxen für Mehrfachauswahl; darunter „Umbenennen …“, „Neu anlegen“ und „Ausgewählte ersetzen“, letztere nur für lokal vorhandene Missionen; „Im Webarchiv sichern …“ lädt die angehakten, lokal vorhandenen Missionen samt Titelbild als neue Einträge in einen wählbaren Projektordner des Archivs, bereits vorhandene Prüfsummen werden übersprungen), **Webarchiv** (siehe oben), **Übertragen** (Modus Neu/Ersetzen, bei Ersetzen die Karte des Zieleintrags, KMZ, Name, großes Vorschaubild; „Vorschau prüfen“ führt zur Prüfseite mit großem Titelbild, Zusammenfassung und der ausdrücklichen Bestätigung „DJI Fly ist geschlossen“ vor „Jetzt übertragen“) und **Protokoll & Einstellungen** (Protokoll mit Zeitstempel, Sicherungen öffnen, ADB-Pfad).

Plattformregeln in der Oberfläche: Auf Android ist „Ersetzen“ der geprüfte Weg, „Neu anlegen“ ist als experimentell gekennzeichnet (Dateien geprüft, DJI-Fly-Sichtbarkeit nicht bestätigt). Auf iPad/iPhone ist „Neu anlegen“ geprüft, „Ersetzen“ nutzt `ios.apply_new(replace=…)` und ist als noch nicht am Gerät geprüft gekennzeichnet. Jede Änderung an Quelle, Name, Bild, Ziel oder Gerät verwirft den vorbereiteten Transfer; die Prüfseite muss erneut durchlaufen werden. Gerätefunktionen (`core.py`, `ios.py`, `preview.py`) sind gegenüber 0.3 unverändert.

## Umbenennen und Sichern ins Webarchiv

Auf iPad/iPhone ändert „Umbenennen …“ den Anzeigenamen in der DJI-Fly-Datenbank (`ios.rename_mission`): Sicherung, temporär schreiben, zurücklesen, umbenennen, bei Fehlern verifizierter Rollback; dieselbe Disziplin wie beim Anlegen. Auf Android ist die Datenbank nicht erreichbar, dort ändert der Knopf nur das Etikett in der Bridge. „Im Webarchiv sichern …“ liest die KMZ und das Titelbild nur vom Gerät (`ios.read_mission` beziehungsweise ADB) und lädt sie über `archive.upload` hoch; das Archiv prüft die Prüfsumme und legt das Original unverändert ab. Cloud-Missionen ohne lokale KMZ werden übersprungen.

## Übertragungskopie bei doppeltem Schlusspunkt

Map Creator schreibt bei manchen Exporten den letzten Wegpunkt zweimal mit derselben `wpml:index`-Nummer, gleichen Koordinaten und gleicher Höhe; der einzige Unterschied ist der Abbiegemodus (erst Durchfahren, dann Stopp). `inspect_kmz` lehnt doppelte Nummern weiterhin ab. `prepare_source` erkennt genau diesen Fall über `sanitize_kmz`, behält den Placemark mit dem Stopp, verwirft den Zwilling und schreibt eine Übertragungskopie `<Name> (bereinigt).kmz` plus Journal in den Anwendungsdatenordner unter `cleaned/`. Die Originaldatei bleibt unverändert, Wegpunkte werden nicht umnummeriert, Aktionsgruppen und ihre Indexverweise bleiben erhalten. Jedes andere Duplikat (abweichende Koordinaten, mehr als zwei Treffer, Duplikat nicht am Ende, keine Stopp-Variante) bleibt ein Fehler. Die Oberfläche zeigt die Bereinigung in der Dateizeile an; der Transferplan enthält `originalSource`. Dass das Webarchiv eine Datei liest, bestätigt keine DJI-Fly-Kompatibilität; die Übertragung muss am Gerät geprüft werden.

## Menüleiste

Die Hauptfunktionen liegen zusätzlich in einer nativen Menüleiste (macOS oben, Windows im Fenster): Datei (KMZ ⌘O, eigenes Vorschaubild, Bridge-Konfiguration, Sicherungen öffnen, Beenden ⌘Q), Gerät (Geräte neu suchen ⌘R, Missionen lesen ⌘L, Gerät sichern ⌘B, Umbenennen ⌘E, Neu anlegen ⌘N, Ausgewählte ersetzen ⇧⌘R, Im Webarchiv sichern ⌘S), Webarchiv (Anmelden ⇧⌘L, für Übertragung verwenden ⌘U, im Browser öffnen), Übertragen (Vorschau prüfen ⌘↩, Jetzt übertragen ⇧⌘↩, Modus), Ansicht (Tabs ⌘1 bis ⌘4) und Hilfe (README, Über).

## App-Icon

`assets/icon.png`, `icon.icns` (macOS) und `icon.ico` (Windows) zeigen das Routen-Zeichen der Web-App auf dunkelgrünem Grund. `build_desktop.py` übergibt das passende Icon an PyInstaller und liefert `assets/` mit; die Oberfläche setzt es zusätzlich als Fenstersymbol.

## Windows 11

Der Code ist plattformunabhängig (PySide6). Das Paket muss auf einem Windows-Rechner mit demselben `build_desktop.py` gebaut werden; PyInstaller baut nicht quer. Zusätzlich nötig: die Windows-Version der Android Platform-Tools (ADB) und für iPad/iPhone die Apple-USB-Treiber (iTunes oder die Apple-Devices-App), damit pymobiledevice3 das Gerät sieht. Ein Windows-Paket wurde noch nicht gebaut oder getestet.

## Automatische 3D-Titelvorschau

Die automatische Vorschau zeigt eine schräge Projektion aus lokalen Meterkoordinaten und gespeicherten Wegpunkthöhen. Horizontale Strecken und Höhen verwenden denselben Maßstab; die Höhen werden nicht übertrieben. Unterschiedliche oder unbekannte Höhenbezüge sowie fehlende Höhen führen zu einer ausdrücklich beschrifteten Draufsicht. Die Grafik zeigt die geplante Route, kein Geländemodell und keine Hindernisse. Bodenraster, Bodenabdruck und Fallinien geben dem Auge eine Bezugsebene; ferne Segmente werden zuerst gezeichnet, nahe bleiben an Kreuzungen sichtbar; Start (grün) und Ende (weiß) sind markiert. Der Missionsname bleibt im unteren Titelband, der Wolkenbereich oben links bleibt frei.

Ein eigenes Bild kann weiterhin ausdrücklich gewählt werden. Benachbarte JPEG-Dateien werden nicht mehr automatisch bevorzugt, damit alte 2D-Vorschaubilder die neue 3D-Ansicht nicht verdecken. Die Missions-KMZ wird durch die Darstellung nicht verändert.

## macOS 26 und Konfigurationsimport (0.4.1)

PySide6/Qt ist auf 6.10.3 aktualisiert. Qt 6.8.3 kann auf macOS beim Zurücksetzen von Listen nach Bedienungshilfe-Abfragen nativ in `QMacAccessibilityElement` abstürzen; upstream QTBUG-134784 ist seit 6.9.1 behoben. Quelle: https://qt-project.atlassian.net/browse/QTBUG-134784. Ein ähnlicher separater Fehler wird unter QTBUG-149612 verfolgt; die genaue Stabilität muss am Mac geprüft werden, ein grüner Offscreen-Test reicht dafür nicht. Bedienungshilfen werden nicht abgeschaltet.

Der Knopf „Konfiguration laden“ öffnet jetzt denselben Dateidialog wie das Menü. Alte Test-Adressen (`example.com`/Loopback) werden außerhalb des Entwicklermodus korrigiert; Tests verwenden explizite temporäre INI-Dateien statt echter macOS-Präferenzen. Nach Import wird nur der zur Archiv-Adresse gespeicherte Schlüssel geladen, kein Schlüssel aus einem anderen Archiv übernommen. Die Konfigurationsdatei selbst enthält keinen Zugangsschlüssel.

## Lokalfilter und Auswahl (0.4.2)

Im Tab **Gerät & Missionen** blendet **Nur lokal vorhanden** reine Cloud-Einträge und mehrdeutige Dateien aus. Der Filter wird auf diesem Mac gespeichert und lässt sich mit der Namens-/Kennungssuche kombinieren. **Alle sichtbaren** markiert nur die aktuell gefilterten Zeilen. Bereits ausgewählte, später ausgeblendete Zeilen bleiben ausgewählt; die Anzahl steht ausdrücklich bei **ausgeblendet**.

Checkboxen zeigen ein weißes Häkchen für **ausgewählt**, ein leeres Kästchen für **nicht ausgewählt** und bei **Alle sichtbaren** einen Strich für eine gemischte Auswahl. Es werden dafür echte QCheckBox-Steuerelemente mit weiterhin verfügbarer Tastatur-/Bedienungshilfe-Unterstützung verwendet. Filter und Auswahl ändern keine Missionsdateien.

## Sortierung, Cloud und Archivstatus (0.4.3)

Die Geräteliste lässt sich nach Name, Änderungsdatum, Streckenlänge und Wegpunktzahl in beide Richtungen sortieren. Fehlende Werte stehen immer zuletzt. Auf dem iPad stammen Datum und Strecke aus der Missionsdatenbank, auf Android aus der lokalen KMZ und dem Dateidatum, soweit zugänglich. Die ursprüngliche Geräte-Reihenfolge bleibt wählbar.

**Nur Cloud** zeigt Missions-Einträge ohne lokale KMZ. Nach Auswahl erklärt **Download in DJI Fly**, wie die Datei auf dem Gerät heruntergeladen wird. Ein eigener DJI-Cloud-Download ist nicht implementiert. Nach Download erneut **Missionen lesen**. Cloud-Missionen werden ohne Datei nicht als „ungesichert“ oder „gesichert“ eingestuft.

Für **Nicht im Webarchiv** zuerst im Webarchiv anmelden und die Geräteliste lesen. Ein identischer SHA-256 der aktuellen lokalen KMZ im geladenen Archivbestand ergibt **Im Webarchiv: identische KMZ**. Namen sind kein Sicherungsnachweis. Der Vergleich berücksichtigt den geladenen Versionsstand, nicht alle historischen Archivversionen, und ersetzt keine vollständige Geräte-Sicherung. Der Prüfstand gilt zum Zeitpunkt des Lesens; nach Änderungen erneut lesen/anmelden. Für die iPad-Liste werden höchstens 64 MiB lokale KMZ (je höchstens 16 MiB) eingelesen; nicht lesbare oder außerhalb des Budgets liegende Dateien bleiben **nicht geprüft**.

## Status-Chips und erneutes Sichern (0.4.4)

Die Geräteliste kennzeichnet **Lokal**, **Nur Cloud**, **Im Webarchiv**, **Nicht im Webarchiv** und **Archiv: nicht geprüft** als Chips. Beim Archiv-Chip nennt der Hinweis die passenden Namen und Projektordner. Das bleibt ein Vergleich der identischen aktuellen KMZ-Prüfsumme mit dem geladenen Archivbestand.

Beim erneuten Sichern wird nach der Zielordner-Auswahl eine identische, bereits vorhandene Archiv-Mission in diesen Ordner verschoben. Es entsteht keine doppelte Mission; Name, Missions-ID, Versionen und Originaldatei bleiben erhalten. Liegt ein identischer Eintrag schon im Zielordner, wird nichts geändert. Bei mehreren Treffern außerhalb des Zielordners wird keine automatische Auswahl getroffen. Die Verschiebung verwendet die geladene Revision; zwischenzeitliche Änderungen werden vom Server mit Konflikt abgelehnt. Das Ergebnis unterscheidet neu gesichert, verschoben, bereits im Zielordner und fehlgeschlagen.

**Löschen auf dem Gerät ist nicht eingebaut.** Dafür DJI Fly verwenden. Ein Download aus der DJI-Cloud bleibt ebenfalls eine Aktion in DJI Fly; die Bridge erklärt dafür den Weg und liest danach den lokalen Bestand neu.

## Einstellungsfenster, Ordnerbaum und Warteschlange (0.5.0)

Die Oberfläche folgt jetzt vier Schritten, die als Pfeilleiste über die ganze Breite laufen: **1 Gerät wählen → 2 Missionen auswählen → 3 Vorschauen prüfen → 4 Übertragen**. Jeder Schritt ist jederzeit anklickbar (auch über `⌘1`–`⌘4`), Schritt 4 wird erst mit gefüllter Warteschlange aktiv. Bildschirmfotos mit synthetischen Daten liegen unter `docs/screenshots-0.5/light/` und `docs/screenshots-0.5/dark/`.

**Einstellungen (`⌘,` oder „Einstellungen …“)**: Archiv-Adresse, Zugangsschlüssel, „Schlüssel merken in“ (macOS-Schlüsselbund, 1Password, Windows DPAPI), „Schlüssel vergessen“, „Konfiguration laden …“, ADB-Pfad und Ablageordner liegen in einem eigenen, nicht blockierenden Fenster. Die Archiv-Adresse wird beim Verlassen des Felds normalisiert und gemerkt; Schlüssel landen nie in den Einstellungen. Schritt 2 zeigt nur noch den Verbindungsstatus („verbunden als Eigentümer · 6 Missionen · Adresse“), „Verbinden“/„Neu laden“ und einen Link ins Einstellungsfenster. Ohne hinterlegten Schlüssel öffnet „Verbinden“ die Einstellungen.

**Schritt 2 wie die Website**: links der Projektbaum („Alle Missionen“, „Ohne Projekt“, Ordner mit Unterordnern und Anzahl, archivierte Ordner markiert), darunter „Unterordner einbeziehen“. Rechts Suche (Name, Projekt, Dateiname), Sortierung (zuletzt geändert, Name, Strecke, Wegpunkte), „Nur DJI-KMZ“ und „Archivierte zeigen“; die Filter wirken zusammen. Jede Zeile hat eine große Vorschau, Projektpfad, Format, Version, Wegpunkte und Strecke sowie eine echte Checkbox; LCHZ/MPROJ und andere Nicht-KMZ bleiben ohne Checkbox und lassen sich nicht übernehmen. „Alle sichtbaren“ hakt nur die sichtbaren KMZ an; die Zahl unten nennt Angehakte außerhalb von Ordner oder Filter („3 ausgewählt · 1 außerhalb von Ordner oder Filter“). „Zur Übertragung übernehmen“ lädt jede angehakte KMZ mit Prüfsummenabgleich und stellt sie in die Warteschlange. Lokale KMZ-Dateien lassen sich ohne Archivanmeldung wählen (`⌘O`, mehrere auf einmal).

**Schritt 3, Warteschlange**: Links die Aufträge in Reihenfolge mit Vorschau, Quelle (Webarchiv-Ordner oder lokale Datei), Wegpunkten, Strecke, Modus und Status; rechts der Editor des markierten Auftrags: „Neu anlegen“ oder „Ersetzen“ als getrennte Segmente, bei Ersetzen die Zielkarte („Zu ersetzender Eintrag auf dem Gerät“, Bild, Wegpunkte, lokal vorhanden, Kennung). Ein Ziel wird in Schritt 1 markiert und mit „Ausgewählte ersetzen“ dem Auftrag zugeordnet; jedes Ziel darf nur einem Auftrag gehören, nur lokal vorhandene Einträge sind zulässig. „Vorschauen erzeugen und prüfen“ rendert alle Titelbilder und prüft alle Aufträge, dann folgt die Prüfseite mit Liste, großer Vorschau, Zusammenfassung („1 von 4“, Zielgerät, Ziel) und der Bestätigung „DJI Fly ist vollständig geschlossen“. Jede Änderung an Name, Quelle, Bild, Modus, Ziel oder Gerät verwirft die Prüfung aller noch nicht übertragenen Aufträge.

**Schritt 4, Übertragung**: Ein Start, dann seriell: sichern, schreiben, zurücklesen, nächste Mission. Je Auftrag Status *bereit*, *geprüft*, *läuft*, *erfolgreich*, *fehlgeschlagen* oder *nicht gestartet*; oben „2 von 4 übertragen“. Beim ersten Fehler stoppt die Übertragung, der Rest bleibt „nicht gestartet“, Sicherung und Journal liegen im Ablageordner. „Nach dem aktuellen Auftrag anhalten“ stoppt nach dem laufenden Auftrag, „Fortsetzen“ überträgt nur nicht gestartete Aufträge; erfolgreiche Missionen werden nie erneut angelegt (Namensregister `names.json`). „Fehlgeschlagene erneut prüfen …“ setzt sie auf *bereit* zurück, sie müssen in Schritt 3 neu geprüft werden. Ein Gerätewechsel oder eine geleerte Warteschlange überträgt nichts; auch Ersetzen-Ziele werden beim Gerätewechsel gelöst. Ein Android-Neuimport bleibt experimentell, das Ersetzen am iPad ist weiter nicht am Gerät geprüft.

**Ehrliche Beschriftungen**: „So lädst du Cloud-Missionen herunter …“ erklärt den Weg in DJI Fly; die Bridge lädt nichts aus der DJI-Cloud. Löschen auf dem Gerät gibt es nicht. Das Fenster bleibt mindestens 1020 × 720 Punkte groß; der Menüpunkt „Übertragen“ führt zu Schritt 4, „Vorschauen prüfen“ zu Schritt 3.

**Tests**: `python3 -m unittest discover -s bridge/tests` (89 Tests) läuft mit `QT_QPA_PLATFORM=offscreen`, temporären INI-Einstellungen, einem Fake-Schlüsselbund und einem temporären Ablageordner; echter Schlüsselbund, echte Einstellungen und `names.json` des Nutzers werden nie gelesen oder beschrieben. `tests/test_queue.py` deckt Ordnerfilter mit und ohne Unterordner, Mehrfachauswahl mit verdeckten Treffern, Reihenfolge der Übernahme, lokale KMZ ohne Anmeldung, Zielprüfung beim Ersetzen, Gerätewechsel, seriellen Ablauf mit Fehlerstopp, Anhalten, Fortsetzen ohne Doppelanlage, Dateiänderung vor dem Start sowie die Lage der Verbindungsfelder im Einstellungsfenster ab. Gerätetests wurden in dieser Version nicht ausgeführt.

## Wegpunktmarker und Kartenquellen (0.5.0)

Beide Titelvorschauen (3D und Luftbild) zeichnen die Wegpunkte wie das Webarchiv: Start als nummerierter heller Kreis „1“, Ende als dunkler Kreis mit der letzten Nummer, alle übrigen Wegpunkte als kleine Punkte (bei sehr vielen Wegpunkten ausgedünnt, Start und Ende bleiben immer lesbar). Mehrere Flugrouten in einer Datei bekommen je einen eigenen nummerierten Startpunkt.

Kartenquellen für „Luftbild“ (`map_preview.py`, nur der Ausschnitt von wenigen Kacheln, kein Offline-Download, Kacheln werden je Quelle zwischengespeichert):

- **Österreich**: basemap.at Orthofoto (`bmaporthofoto30cm`) mit dem Beschriftungs-Overlay `bmapoverlay` (Straßennamen, Orte) darüber, CC BY 4.0. Quellenangabe im Bild.
- **Außerhalb Österreichs** (Italien, Frankreich usw.): Esri World Imagery als weltweites Luftbild, Quellenangabe „Esri, Maxar, Earthstar Geographics, GIS User Community“ im Bild; die Nutzung richtet sich nach den Esri-Bedingungen für Basiskarten mit Quellenangabe.
- **Rückfall**: ist auch das nicht erreichbar, die OpenStreetMap-Standardkarte (ODbL, © OpenStreetMap-Mitwirkende). Fällt alles aus, erscheint die 3D-Ansicht mit Hinweis im Protokoll.

Eine weitere WMTS-Quelle lässt sich in `PROVIDERS` als Liste von Kachel-URLs (`{z}/{x}/{y}`) mit Quellenangabe und maximaler Zoomstufe ergänzen, etwa die französische Geoplateforme (ORTHOIMAGERY.ORTHOPHOTOS) oder regionale italienische Orthofotos; `provider_for()` wählt die Reihenfolge nach der Lage der Route.

## Erscheinungsbild nach Apple-Grundsätzen (0.6.0)

Die Oberfläche folgt den Gestaltungsgrundsätzen aus Apples WWDC-Vorträgen (Vertrautheit, Klarheit, Handwerk, sofortige Rückmeldung), übersetzt auf Qt. Die Vier-Schritte-Logik bleibt unverändert.

- **Systemschrift**: San Francisco auf dem Mac, Segoe UI auf Windows; keine fest verdrahtete Schriftart mehr. Große Titel laufen enger (negatives Tracking), kleine Beschriftungen bleiben offen.
- **Hell und dunkel folgen dem System** (`theme.py`): ein Stylesheet-Template mit Farbtokens wird je Schema gerendert; wechselt macOS oder Windows das Erscheinungsbild, zieht die Bridge sofort nach. `DRONEMISSIONS_THEME=light|dark` erzwingt ein Schema (auch für Bildschirmfotos). Vorschaubilder und Platzhalter bleiben in beiden Schemata dunkelgrün, Status-Chips behalten ihre Pastellfarben wie macOS-Tags.
- **Symbolleiste** statt Kopfzeile: Gerätewahl links, rechts „Neu suchen“, „Missionen lesen“, „Gerät sichern“, „Protokoll“ und „Einstellungen“ als Icon mit Beschriftung. Die Icons sind einfache Linienzeichnungen, in der Textfarbe des Schemas gerendert (Retina-tauglich). Knöpfe quittieren den Druck sofort (`:pressed`).
- **Infoblock** auf der Prüfseite wie im Festplattendienstprogramm: Wegpunkte, Ziel, Quelle und Titelbild als Schlüssel-Wert-Zeilen mit feinen Trennlinien statt Fließtext.
- **Projektbaum**: Pfeile als eigene Grafik, Verzweigungsspalte ohne Fokusrahmen; markierte Ordner mit und ohne Unterordner sehen gleich aus.
- **Vorschaubilder passen sich dem Platz an** (`PreviewLabel`): das Quellbild wird bei jeder Größenänderung neu skaliert, Infoblock und Knöpfe werden nie überdeckt.
- **Warteschlange zeigt sofort Bilder**: Beim Hinzufügen entsteht eine schnelle Offline-Vorschau (3D oder Archivbild), beim Umbenennen wird sie entprellt erneuert. Das endgültige Titelbild entsteht weiterhin bei „Vorschauen erzeugen“.
- **Archivbild als Titelbild**: Missionen aus dem Webarchiv bringen ihre Vorschau mit (Routenzeichnung als SVG oder Bild aus dem Vorschau-Editor). Sie wird als JPEG abgelegt, ist Standard-Titelbild für Archivmissionen und steht als vierte Option „Archivbild“ neben 3D-Ansicht, Luftbild und eigenem Bild; für lokale Dateien ist die Option ausgeblendet.

Tests dazu: `tests/test_theme.py` (beide Schemata ohne offene Platzhalter, Icons, Symbolleiste, Infoblock) und `tests/test_queue.py` (Archivbild als Listenbild und Titelbild). Gesamt 89 Tests, ohne Gerät.
