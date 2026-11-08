# Bridge bedienen und aktualisieren

Stand: 8. November 2026. Quellstand der Mac-App 0.4.1: `1679b96` auf
[Claudes Bridge-Branch](https://github.com/studiobaff/dronemissions/tree/1679b96/bridge).

## Download und Anmeldung

Im Webarchiv anmelden und **Bridge** öffnen. ZIP für macOS und bei Bedarf die
Archiv-Konfiguration herunterladen. Die SHA-256-Prüfsumme steht am Download.
ZIP entpacken und die App in Programme ablegen. Der Mac-Build ist ad-hoc signiert,
jedoch nicht von Apple notarisiert. Windows erfordert einen eigenen Build auf
Windows; ein getestetes Windows-Paket ist bislang nicht veröffentlicht.

Im App-Tab **Webarchiv** die Konfiguration laden oder die Archiv-Adresse eintragen:
`https://service.studiobaff.com/dronemissions/`. Der Zugangsschlüssel wird getrennt
angegeben und ist nicht Teil der herunterladbaren Konfiguration oder App.

**Schlüssel merken** bietet auf macOS den Schlüsselbund und bei installierter
1Password-CLI auch 1Password. Für 1Password muss `op` installiert und die
CLI-Integration in der 1Password-App aktiviert sein. Die App-Konfiguration allein
richtet diese Integration nicht ein. Das merkt den Archiv-Zugangsschlüssel;
Missionsdaten und Datenbank werden dadurch nicht in 1Password gesichert.

## Ablauf

1. iPad/iPhone oder Fernsteuerung per USB anschließen, entsperren und auswählen.
2. **Missionen lesen** lädt den Bestand; Namenssuche und Mehrfachauswahl helfen bei
   der Auswahl. iPad-Missionsnamen lassen sich bearbeiten, Fernsteuerungen können
   davon abweichen. **Im Webarchiv sichern** legt ausgewählte Gerätemissionen im
   Archiv ab; eine erfolgreiche Dateisicherung ersetzt keine Prüfung in DJI Fly.
3. Im Webarchiv eine DJI-KMZ wählen oder über **Datei → KMZ auswählen** öffnen.
4. **Neu anlegen** oder **Ersetzen** und das gewünschte Ziel wählen. Titel und
   Vorschaumodus festlegen: 3D offline, Luftbild über basemap.at innerhalb Österreichs
   mit Internet, oder ein eigenes Bild. Luftbildfehler werden mit Rückfall auf 3D
   angezeigt. Die Vorschau zeigt geplante Wegpunkthöhen, kein Hindernismodell.
5. **Vorschau prüfen**, DJI Fly vollständig schließen und den geschlossenen Zustand
   bestätigen. Erst **Jetzt übertragen** schreibt aufs Gerät. Der Bestand wird
   vorher gesichert und die übertragenen Daten werden zurückgelesen.
6. In DJI Fly Mission, Punktzahl, Darstellung, Speichern und Cloud-Synchronisation
   prüfen. Dateiprüfsummen bestätigen nicht die Flugsicherheit.

Bekannter Helix-Fall: Der doppelte abschließende Map-Creator-Punkt wird nur im
eng geprüften Sonderfall in einer Übertragungskopie zusammengeführt. Der Stopp
bleibt erhalten, das Original unverändert. Die Original-Helix wurde auf dem iPad
mit 117 Punkten angezeigt, synchronisiert und erfolgreich gespeichert/verlassen.
DJI Fly ersetzt die eigene Titelvorschau beim Speichern gegebenenfalls durch eine
Kartenansicht. Änderungen vorhandener Vorschaubilder werden nicht zuverlässig
über DJI Cloud auf andere Geräte verteilt.

## Menüleiste und Tastatur

Auf macOS erscheinen die Menüs in der Systemleiste, auf Windows im Fenster.
Windows verwendet Strg statt ⌘. Die Menüaktionen verwenden dieselben Prüfungen
wie die Knöpfe; Tastenkürzel umgehen keine Übertragungsbestätigung.

| Menü | Wichtige Aktionen / macOS-Kürzel |
| --- | --- |
| Datei | KMZ ⌘O, eigenes Bild ⇧⌘O, Konfiguration, Sicherungen, Beenden ⌘Q |
| Gerät | Suchen ⌘R, Lesen ⌘L, Sichern ⌘B, Umbenennen ⌘E, Neu ⌘N, Ersetzen ⇧⌘R, Webarchiv sichern ⌘S |
| Webarchiv | Anmelden ⇧⌘L, für Übertragung verwenden ⌘U, Browser öffnen |
| Übertragen | Vorschau ⌘↩, Übertragen ⇧⌘↩, Modus Neu/Ersetzen |
| Ansicht | Tabs ⌘1 bis ⌘4 |
| Hilfe | README und Versionsinformation |

## Betrieb und offene Prüfungen

Web-Änderungen laufen nach geprüftem PR/Merge in main automatisch über GitHub
Actions. Die Mac-App wird separat aus dem genannten Quellstand gebaut und als ZIP
in den privaten Serverordner `bridge/` gestellt; Zugang für Eigentümer/Bearbeiter.
Alte Pakete bleiben außerhalb der aktuellen Download-Liste archiviert.

Gerätetest **Ersetzen auf RC Pro 2**, Windows-Paket und 1Password-Integration auf
diesem Mac sind noch offen. Änderungen am Schlüsselbund dürfen niemals aus Tests
heraus erfolgen; die Desktop-Tests injizieren ihren Test-Schlüsselspeicher bereits
vor dem Fensteraufbau.

## Korrekturen in 0.4.1

Der Konfigurationsknopf und die native Menüaktion können die heruntergeladene JSON
öffnen. Nach dem Import wird der gespeicherte Zugangsschlüssel nur für die
importierte Archiv-Adresse geladen; anschließend „Anmelden und Bibliothek laden“
wählen. Test-Adressen wie `example.com` oder Loopback werden außerhalb des
Entwicklermodus auf die produktive Vorgabe zurückgesetzt.

Die Desktop-Tests verwenden explizite temporäre INI-Einstellungen und einen
vor dem Fensteraufbau injizierten Schlüsselspeicher. Sie lesen und ändern weder
die echten macOS-Präferenzen noch den Schlüsselbund. 60 Tests bestanden.

Qt wurde von 6.8.3 auf 6.10.3 aktualisiert. Der gemeldete native macOS-Absturz
in `QMacAccessibilityElement` passt zu QTBUG-134784 (Listen-/Tabellenmodell wird
nach einer Bedienungshilfe-Abfrage zurückgesetzt):
https://qt-project.atlassian.net/browse/QTBUG-134784.
Die Konfiguration aus Downloads, das Wiederherstellen des gespeicherten Schlüssels
und die erneute Anmeldung mit geladener Bibliothek wurden mit der gebauten App
auf dem Mac erfolgreich geprüft. Das ist keine Garantie gegen jeden weiteren
nativen Qt-Absturz; Bedienungshilfen bleiben aktiviert.
