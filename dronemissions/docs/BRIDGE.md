# Bridge bedienen und aktualisieren

Stand: 8. November 2026.

## Aktueller Stand und offene Gerätetests

Der aktuelle Mac-Download und die installierte App sind **0.6.2**:
**`dronemissions-bridge.app`**, Quellstand
[`618aa5a`](https://github.com/studiobaff/dronemissions/tree/618aa5a/bridge).
Er enthält Claudes
[`21bd381`](https://github.com/studiobaff/dronemissions/commit/21bd381)
und zusätzlich den ADB-Verpackungsfix. Das vorherige Bundle
„Drone Missions Bridge.app“ wurde auf dem betreuten Mac aus Programme in eine
Rückfallkopie verschoben. Kennungen für Einstellungen und Schlüsselbund bleiben
unverändert; vorhandene Zugangsdaten gelten weiterhin.

**113 isolierte Tests** bestehen. Paket und ADB-Prüfsumme wurden geprüft, die App
wurde installiert und gestartet. Am verbundenen iPad wurden **44 Missionen samt
DJI-Fly-Titelbildern** erfolgreich gelesen (Bestand zum Testzeitpunkt). Bei diesem Bildlesetest
wurden keine Missionen geändert oder übertragen. Der Vorschau-Upload ins
Webarchiv und die unten genannten Übertragungsfälle bleiben offen.

## Neu in 0.6.2: POIs

3D und Luftbild zeichnen vorhandene aktive WPML-Blickziele als lila Rauten mit „POI N“. Wiederholte Verweise werden zusammengefasst und der Ausschnitt berücksichtigt die POIs. Es entstehen keine zusätzlichen Flugpunkte, und Original-KMZs bleiben unverändert. In 3D ist die horizontale Lage auf der unteren Routenebene gemeint; ein unbestätigter Höhenbezug wird nicht geraten. Vorhandene Fotos und Archivbilder bleiben unverändert. Für die neuen Marker eine 3D-/Luftbildvorschau erzeugen oder im Webarchiv ein neues Bild speichern.

Die installierte App 0.6.2 wurde mit einer synthetischen KMZ geöffnet und die POI-Zeichnung visuell geprüft. Es wurde dabei nichts aufs iPad übertragen. 113 isolierte Tests bestehen, einschließlich aktiv/inaktiv, Koordinatenreihenfolge, Zusammenfassung, ungültigen Werten und 3D-/Luftbildrendering mit Kachel-Fakes. App-Signatur, gebündelter ADB-Hash und vollständiger authentifizierter ZIP-Download sind geprüft. Der zuvor bestätigte Geräte-Rundlauf bezieht sich weiterhin auf 0.6.1; neue Geräteänderungen wurden für den Vorschauwechsel nicht vorgenommen.

## Download und Zugang

Im [Webarchiv](https://service.studiobaff.com/dronemissions/) anmelden und
**Bridge** öffnen. Mac-ZIP und bei Bedarf die Konfiguration herunterladen; die
Prüfsumme steht beim Download. Die Konfiguration enthält die Archiv-Adresse,
keinen Zugangsschlüssel. Die App ist lokal ad-hoc signiert, nicht von Apple
notarisiert. Windows braucht einen separaten Build auf Windows; ein getestetes
Windows-Paket ist nicht veröffentlicht.

Archiv-Adresse: `https://service.studiobaff.com/dronemissions/`.

In **0.4.4** stehen Adresse und Schlüssel im Webarchiv-Tab. In **0.5.0** wandern sie
in ein separates natives Fenster **Einstellungen …** mit **⌘,**. Dort liegen auch
Konfigurationsimport, ADB, Ablage und Schlüsselspeicher. Im Hauptfenster bleiben
nur Verbindungsstatus und die Missionen.

**Schlüssel merken** unterstützt den macOS-Schlüsselbund, bei installierter
1Password-CLI `op` die vorhandene 1Password-Integration und unter Windows DPAPI.
Die CLI-Integration muss in 1Password aktiviert sein. Das speichert den
Zugangsschlüssel, keine Missionsdaten oder Datenbanksicherung. Auf diesem Mac ist
die 1Password-Integration noch nicht geprüft. Tests dürfen den echten
Schlüsselbund und echte Programmeinstellungen nie berühren.

## Bestehende Funktionen aus 0.4.4

* **Gerät wählen → Missionen lesen** lädt die Missionsliste.
* Filter: **Nur lokal**, **Nur Cloud**, nach Archivanmeldung **Nicht im Webarchiv**.
* Suche und Sortierung nach Name, Datum, Strecke oder Punktzahl; nicht verfügbare
  Metadaten bleiben unbekannt. Hakerl zeigen Auswahl und Teilzustand deutlich.
* Chips zeigen lokalen/Cloud-Bestand sowie den Archivstatus. „Im Webarchiv“ setzt
  eine identische Prüfsumme im geladenen aktuellen Archivbestand voraus.
* **Im Webarchiv sichern** sichert lokale Dateien. Wird dieselbe Datei in einen
  anderen Projektordner gesichert, verschiebt die Bridge einen eindeutig passenden
  bestehenden Archiveintrag, statt ihn zu duplizieren. Mehrdeutige Treffer und
  veraltete Revisionen werden abgelehnt.
* Reine Cloud-Missionen müssen zunächst **in DJI Fly manuell heruntergeladen**
  werden. Der entsprechende Bridge-Knopf zeigt eine Anleitung und führt selbst
  keinen Cloud-Download aus. Danach die Geräteliste neu lesen.
* Ab 0.6.1 können angehakte Missionen auf iPad/iPhone lokal entfernt werden; siehe Aufräumen unten. Auf Android weiterhin DJI Fly verwenden.

## Ablauf ab 0.5.0

1. **Gerät wählen:** iPad/iPhone oder Fernsteuerung per USB verbinden, entsperren
   und auswählen.
2. **Missionen auswählen:** aufklappbarer Projektbaum wie im Webarchiv mit
   Unterordnern, „Alle Missionen“, „Ohne Projekt“ und „Unterordner einbeziehen“.
   Ordnerfilter, Suche und Sortierung sind kombinierbar. Mehrere ausführbare
   DJI-KMZs lassen sich auswählen; ausgeblendete ausgewählte Einträge werden
   gezählt. Lokale KMZs benötigen keine Archivanmeldung. Native Litchi-/Map-Creator-
   Projektdateien ersetzen keinen ausführbaren DJI-KMZ-Export.
3. **Vorschauen prüfen:** pro Auftrag Name, Quelle, Vorschau und Modus kontrollieren.
   **Neu anlegen** und **Ersetzen** bleiben getrennt. Jedes Ersetzen braucht ein
   eindeutiges lokales Ziel. 3D nutzt gespeicherte Wegpunkthöhen; erste und letzte
   Wegpunktnummer sind markiert. In Österreich nutzt das Luftbild basemap.at plus
   Beschriftung, außerhalb das weltweite Luftbild mit Quellenangabe und eine
   Karten-Rückfallebene. Ein eigenes Bild ist ebenfalls möglich. Es handelt sich
   um ein festes Titelbild, kein drehbares Modell in DJI Fly.
4. **Übertragen:** DJI Fly vollständig schließen, keinen Flug aktiv lassen und den
   Zustand bestätigen. Die Warteschlange schreibt seriell, sichert vorher und
   liest zurück. Einzelstatus und Fortschritt anzeigen; beim ersten Fehler stoppen.
   Erfolgreiche Aufträge werden beim Fortsetzen nicht erneut angelegt. Gerätewechsel
   verwirft zugehörige Pläne und Ziele.

Pfeilleiste und **⌘1–⌘4** wechseln zwischen den vier Schritten. Das Protokoll ist
separat erreichbar. Native Menüs rufen dieselben Prüfungen wie die Knöpfe auf;
Tastenkürzel umgehen keine Bestätigung.

## Neu in 0.6.0

* Systemabhängiges helles/dunkles Schema, kompakte Symbolleiste mit einfarbigen
  Icons, Kapsel-Knöpfe und gerahmter Infoblock auf der Prüfseite. Der Programmname
  lautet **dronemissions-bridge**.
* Die Warteschlange zeigt Bilder sofort. Für Archivmissionen ist das mitgeladene
  **Archivbild** die Standardvorschau, wählbar neben 3D, Luftbild und eigenem Bild.
* Das iPad liefert beim Lesen auch seine DJI-Fly-Titelbilder. Fehlt ein Gerätebild,
  kann die identische Archivmission als Bildquelle dienen.
* **Vorschauen ins Webarchiv** speichert Gerätebilder als zusätzliche aktive Bilder
  identischer Archivmissionen. Die angehakten Missionen sind maßgeblich; ohne
  Hakerl werden alle sichtbaren passenden Missionen berücksichtigt. Der Dialog
  fragt vor dem Speichern nach. Für den ersten Test **genau eine Mission anhaken**.
  Frühere Bilder und KMZ bleiben erhalten; eine neue Missionsversion entsteht
  nicht. Der echte Upload dieses Ablaufs ist noch nicht geprüft.
* Checkboxen in Schritt 3 und 4 erlauben **Markierte entfernen**, bevor die
  Übertragung beginnt. Die übrigen geprüften Aufträge bleiben gültig.
* **Umbenennen** ist auch bei genau einer angehakten Gerätemission verfügbar.
  Das ist eine Änderung am Gerät und kein Bestandteil des reinen Bildlesetests.

## Aufräumen und später neu übertragen (0.6.1)

1. Missionen anhaken und **Im Webarchiv sichern …**. Der Archiv-Chip bestätigt die identische KMZ anhand der Prüfsumme.
2. Die gewünschten Missionen anhaken und **Vom iPad entfernen …**. Eine nur markierte Zeile genügt nicht. Auch ausgeblendete angehakte Einträge werden im Bestätigungsdialog aufgeführt.
3. Archivstatus prüfen, DJI Fly vollständig schließen und im Dialog bestätigen. Erst **Sichern und vom iPad entfernen** startet den Vorgang; Abbrechen ist voreingestellt.
4. Später im Webarchiv-Projekt auswählen und über **Neu anlegen** wieder aufs Gerät übertragen. Webarchiv-Dateien, Bilder, Namen und Versionen werden durch das Entfernen nicht verändert.

Vor jeder Entfernung wird der vollständige lokale Gerätebestand gesichert und zurückgelesen. Es werden nur die ausgewählten Datenbankeinträge und ihre eindeutig zugehörigen Dateien entfernt. Alle anderen Zeilen/Tabellen und verbleibenden Dateien müssen unverändert bleiben. Zwischenzeitliche Änderungen und geteilte Dateiverweise brechen ab. Fehler nach Schreibbeginn lösen eine Rücklese-geprüfte Wiederherstellung aus; Sicherung und Journal bleiben im Anwendungsdatenordner erhalten. Gerät und Menüs sind während der Arbeit gesperrt.

Nicht archivierte oder defekte Einträge können nach ausdrücklicher Bestätigung ebenfalls lokal entfernt werden, haben dann aber nur die lokale Sicherung und keinen zugesicherten Webarchiv-Wiederimport. Die Funktion löscht **keine DJI-Cloud-Kopie**; eine solche kann bei Synchronisation erneut auftauchen. Android-Löschen ist nicht implementiert.

Prüfung: **109 isolierte Tests**, einschließlich Abbrechen, Checkbox-Auswahl trotz Filter, iPad-Beschränkung, exakter Datenbankauswahl, gemeinsam verwendeten Dateien, veränderten Quelldaten und Rollback nach teilweisem Löschen oder unklarer Datenbankumbenennung. Mit ausdrücklicher Nutzerfreigabe wurden am echten iPad fünf alte, nie synchronisierte „Injected Mission“-Einträge und zehn Dateien entfernt. 144 Dateien wurden vorher vollständig gesichert; sämtliche übrigen Dateien wurden unverändert bestätigt. Anschließend las die installierte App die verbleibenden **39 Missionen** erfolgreich. Der vollständige Rundlauf wurde anschließend am echten iPad über die installierte Bridge geprüft: eine Mission mit 12 Wegpunkten neu im Webarchiv gesichert, von dort mit identischer KMZ-Prüfsumme zurückgeladen, lokal vom iPad entfernt (39 → 38 Missionen) und aus dem Archiv als neuer Eintrag wieder übertragen (38 → 39). Name und 12 Wegpunkte stimmen; das Archivbild wurde für die Übertragung verwendet. Die Archivkopie bleibt byte-identisch in Version 1. Der Nutzer bestätigte das Ergebnis in DJI Fly. Der neue Geräteeintrag hat erwartungsgemäß eine neue Kennung; die alte lokale Kennung bleibt entfernt.

## Prüfung und Grenzen

Die frühere Helix wurde nach gezielter Bereinigung eines doppelten Schlusspunkts
als neue iPad-Mission mit 117 Punkten angezeigt, synchronisiert und erfolgreich
gespeichert/verlassen. Die Bereinigung arbeitet mit einer Kopie, das Original
bleibt unverändert. Dies bestätigt nicht automatisch die neue Warteschlange.
DJI Fly kann das eigene Vorschaubild nach dem Speichern durch eine Karte ersetzen;
Änderungen bestehender Bilder werden nicht zuverlässig über DJI Cloud verteilt.

Für diesen Stand bestanden **109 isolierte Tests**. Echte Kartenabrufe wurden auf
dem Mac für Österreich und das weltweite Luftbild erfolgreich ausgeführt. Ein
reales Mac-Paket zeigte zusätzlich einen ADB-Verpackungsfehler: PyInstaller
verändert das Mach-O-Binary durch Architekturverarbeitung und Signatur. Der
Korrekturbranch `codex/bridge-050-packaging` bewahrt den Upstream-Hash und prüft den
Hash des tatsächlich ausgelieferten ADB. Das korrigierte Paket wurde nach dem
Staging mit strikter Signaturprüfung und erfolgreicher ADB-Erkennung geprüft.
Diese Korrektur ist auch im ausgelieferten Stand `55bbdaa` enthalten.

Noch offen: ein Gerätebild über die neue Bridge-Funktion ins Webarchiv speichern, zwei neue iPad-Missionen seriell übertragen, Fehler/Stopp/Fortsetzen
am Gerät, iPad-Ersetzen, RC-Pro-2-Ersetzen, experimenteller Android-Neuimport und
Windows-Build. Keine Dateiprüfung oder Vorschau bestätigt die Flugsicherheit.

## GitHub und Veröffentlichung

`main` ist geschützt: Pull Request, erfolgreiche Checks, keine Force-Pushes oder
Branchlöschung. Claude kann auf seinem Arbeitsbranch weiterarbeiten. Beiträge
von außen erfolgen in einem Fork; nur der Eigentümer hat Schreibzugriff.

Die zentrale Anleitung liegt auf `main`; Bridge-Arbeit und der genaue Paketstand sind oben verlinkt. Für weitere Versionen nach Claudes finalem Commit: Stand holen, isolierte Tests,
Mac-Build, Paket-/Signaturprüfung, App installieren und Gerätetest mit dem Nutzer.
Das ZIP und die zugehörige Doku kommen anschließend in den privaten Serverordner
`bridge/`. Alte Download-Pakete bleiben separat archiviert. Web-Code wird über
geprüfte PRs und GitHub Actions veröffentlicht, nicht mit alten lokalen Dateien
überschrieben.

Die eigenständige Bildauswahl im Webarchiv ist unter
[PREVIEWS.md](PREVIEWS.md) dokumentiert: mehrere Bilder und gespeicherte
Einstellungen ohne neue Missionsversion; Archivordner sind aufklappbar.
