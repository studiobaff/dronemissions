# Bridge bedienen und aktualisieren

Stand: 8. November 2026.

## Aktueller Stand und offene Gerätetests

Der aktuelle Mac-Download und die installierte App sind **0.5.0**, Quellstand
[`3bd45da`](https://github.com/studiobaff/dronemissions/tree/3bd45da/bridge).
Er kombiniert Claudes Layoutkorrektur
[`7bf012c`](https://github.com/studiobaff/dronemissions/commit/7bf012c)
mit dem ADB-Verpackungsfix aus
[PR #10](https://github.com/studiobaff/dronemissions/pull/10).

**83 isolierte Tests** bestehen. Das Paket wurde gebaut, signiert, installiert
und gestartet. Das korrigierte Einstellungsfenster, die Erkennung des eingebauten
ADB und die Verbindung zum echten Webarchiv mit Ordnerbaum wurden auf dem Mac
geprüft. Die folgenden Gerätetests sind weiterhin offen; durch diese Prüfung
wurde keine Mission übertragen. Der spätere Apple-Design-Durchgang **0.6** ist
eine getrennte Überarbeitung und nicht Voraussetzung für diesen Build.

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
* Löschen auf dem Gerät ist nicht implementiert; es erfolgt in DJI Fly.

## Ablauf in 0.5.0

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

## Prüfung und Grenzen

Die frühere Helix wurde nach gezielter Bereinigung eines doppelten Schlusspunkts
als neue iPad-Mission mit 117 Punkten angezeigt, synchronisiert und erfolgreich
gespeichert/verlassen. Die Bereinigung arbeitet mit einer Kopie, das Original
bleibt unverändert. Dies bestätigt nicht automatisch die neue Warteschlange.
DJI Fly kann das eigene Vorschaubild nach dem Speichern durch eine Karte ersetzen;
Änderungen bestehender Bilder werden nicht zuverlässig über DJI Cloud verteilt.

Für diesen Stand bestanden **83 isolierte Tests**. Echte Kartenabrufe wurden auf
dem Mac für Österreich und das weltweite Luftbild erfolgreich ausgeführt. Ein
reales Mac-Paket zeigte zusätzlich einen ADB-Verpackungsfehler: PyInstaller
verändert das Mach-O-Binary durch Architekturverarbeitung und Signatur. Der
Korrekturbranch `codex/bridge-050-packaging` bewahrt den Upstream-Hash und prüft den
Hash des tatsächlich ausgelieferten ADB. Das korrigierte Paket wurde nach dem
Staging mit strikter Signaturprüfung und erfolgreicher ADB-Erkennung geprüft.
Diese Korrektur ist im ausgelieferten Stand `3bd45da` enthalten und bleibt über PR #10 für Claudes weitere Arbeit verfügbar.

Noch offen: zwei neue iPad-Missionen seriell übertragen, Fehler/Stopp/Fortsetzen
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
