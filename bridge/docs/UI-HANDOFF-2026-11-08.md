# Handover für Claude: Bridge-Oberfläche und Mehrfachübertragung

## Auftrag

Die Bridge übersichtlich gestalten. Der Nutzer übergibt Claude die UI-Arbeit; nach dem Push übernimmt ChatGPT wieder Mac-Build, Installation und Gerätetest. Bestehende Gerätefunktionen, Prüfungen und Sicherungen erhalten. Die Webarchiv-Arbeit separat behandeln.

## Verbindlicher Ausgangsstand

* Aktuell installierte Bridge: **0.4.4**, Code **da4e48d** auf `bridge/config-and-settings-fix`.
* **PR #6** zuerst einbeziehen: https://github.com/studiobaff/dronemissions/pull/6 (Ziel `claude/drone-missions-ui-handoff-4nsj6e`). Nicht nur den älteren Claude-Branch bearbeiten: Sonst gehen die funktionierenden Filter und Archivfunktionen verloren.
* 71 Bridge-Tests bestehen. Qt/PySide6 ist auf **6.10.3** festgelegt: frühere 6.8.3 verursachte native macOS-Accessibility-Abstürze. Nicht zurücksetzen, Accessibility nicht abschalten.
* Vorhanden und zu erhalten: lokale/Cloud-/nicht-im-Webarchiv-Filter, klare Hakerl inklusive Teilzustand, Sortierung, Archivstatus-Chips anhand Prüfsumme, und beim erneuten Sichern einen eindeutig identischen Archiveintrag in den gewählten Projektordner verschieben statt duplizieren. Unbekannt ist nicht gleich ungesichert.
* Konfigurationsimport und Test-Isolation sind behoben. Tests dürfen weder den echten Schlüsselbund noch echte Programmeinstellungen lesen oder verändern.

## 1. Echte Programmvoreinstellungen

**Adresse und Schlüssel gehören nicht in den Webarchiv-Tab und auch nicht dauerhaft in einen Einstellungen-Tab.**

Ein separates natives Fenster **„Einstellungen …“**, auf macOS über das Programmmenü und **⌘,**, auf Windows über das Menü. Dorthin gehören:

* Webarchiv-Adresse und Zugangsschlüssel;
* „Schlüssel merken“, Speicherort (macOS-Schlüsselbund / vorhandene 1Password-CLI-Integration / Windows DPAPI), „Schlüssel vergessen“;
* Bridge-Konfiguration laden;
* gebündeltes ADB, eigener ADB-Pfad und weitere technische Optionen.

Vorhandene Einstellungen migrieren/weiterverwenden. Schlüssel nur dem passenden Archiv-URL zuordnen, keine fremden Testadressen oder Zugangsdaten übernehmen. Keine Secrets in Git, Protokollen, Screenshot-Fixtures oder Handoffs.

Im Webarchiv-Tab nur kompakter Verbindungsstatus mit „Verbinden/Neu laden“ und Link „Einstellungen …“. Fehler führen verständlich zu den Einstellungen. Der frei gewordene Platz gehört den Missionen. Das Protokoll darf separat erreichbar bleiben, muss aber keine technischen Einstellungen im Hauptfenster zeigen.

## 2. Webarchiv: Ordner wie auf der Website

**Kein bloßes Projekt-Dropdown.** Links derselbe aufklappbare Projekt-/Ordnerbaum wie im Webarchiv, inklusive Unterordnern, „Alle Missionen“ und „Ohne Projekt“. Rechts eine große Missionsliste des gewählten Ordners.

* Optional „Unterordner einbeziehen“.
* Suche und Sortierung mit dem gewählten Ordner kombinieren.
* Große, lesbare Vorschaubilder und Missionsnamen. Ordnerpfad erkennbar.
* Mehrfachauswahl mit echten Hakerln; Auswahl über Filterwechsel nicht unbemerkt verlieren. Verborgene ausgewählte Einträge zählen/anzeigen.
* Nur tatsächlich übertragbare DJI-KMZs anbieten. Native MPROJ/LCHM/LCHZ sind Projektdateien; keine erfundene Konvertierung. Zugehörige ausführbare KMZ verwenden, sofern vorhanden.
* Kunden-/Projektberechtigungen des Servers respektieren.

## 3. Klarer Ablauf und Pfeile

Der Nutzer wünscht stilisierte Pfeile: **Gerät wählen → Missionen auswählen → Vorschauen prüfen → Übertragen**. Aktuellen Schritt hervorheben; Rücksprung muss möglich bleiben.

Die derzeitige Tab-Leiste nutzt nur die linke Hälfte und hat eine störende lange Restlinie. Navigation verständlich über die verfügbare Breite verteilen. Technische Einstellungen aus diesem Ablauf entfernen. Eine lokale KMZ muss weiterhin ohne Webarchiv-Anmeldung auswählbar sein.

## 4. Mehrere Missionen übertragen

Der Nutzer möchte mehr als eine Mission auswählen können. Aktuell verarbeitet die Bridge jeweils nur eine Übertragung.

Eine **Warteschlange** für mehrere ausgewählte Missionen implementieren:

* Aus dem gewählten Webarchiv-Ordner mehrere DJI-KMZs übernehmen; nach Möglichkeit auch mehrere lokale KMZs auswählen.
* Vor Übertragung pro Eintrag Name, Quelle, Vorschau und Modus klar zeigen. Namen vorbelegen und bearbeitbar halten.
* „Neu anlegen“ und „Ersetzen“ klar trennen. Beim Ersetzen braucht **jeder** Auftrag ein eindeutiges Ziel; keine automatische oder mehrfache Zielzuordnung.
* Gerätefähigkeiten beachten: neuer iPad/iPhone-Eintrag ist bestätigt; Android/RC Pro 2 kann nicht einfach denselben Ablauf übernehmen. Nicht unterstützte Modi sperren und begründen.
* Ein gemeinsamer Start, danach **seriell**, nicht parallel auf dasselbe Gerät schreiben.
* Bestehende vollständige Sicherung und Rücklesen/Prüfen nicht umgehen. „DJI Fly geschlossen, kein Flug aktiv“ bleibt Voraussetzung.
* Pro Mission Status: bereit, läuft, erfolgreich, fehlgeschlagen, nicht gestartet. Fortschritt etwa „2 von 5“.
* Bei Fehlern stoppen und den Zustand klar zeigen; keinen unklaren Auftrag blind erneut ausführen. Wiederaufnahme darf bereits erfolgreiche neue Missionen nicht duplizieren.
* Eine abgebrochene Warteschlange und ein Gerätewechsel dürfen keine versehentlichen Übertragungen auslösen.

Die Auswahl zum Sichern vorhandener Gerätemissionen nicht unbemerkt als Übertragungswarteschlange umdeuten.

## 5. Vorschaubilder und bestehende Grenzen

Große Vorschauen, Titelband unten, oben Platz für DJI-Fly-Symbole. Vorhandene Modi 3D/Luftbild/eigenes Bild erhalten. 3D nutzt Wegpunkthöhen; Helix muss als Halbkugel erkennbar sein. DJI Fly kann ein importiertes Bild später durch einen eigenen Kartenausschnitt ersetzen. Keine gegenteilige Zusicherung geben.

„Download in DJI Fly …“ lädt derzeit **nicht automatisch** herunter, sondern zeigt nur eine Anleitung zum manuellen Download. Ehrlich umbenennen, etwa „So lädst du Cloud-Missionen herunter …“. Keine direkte DJI-Cloud-Downloadfunktion behaupten.

Löschen auf dem Gerät ist **nicht** implementiert und gehört nicht zu diesem UI-Auftrag. Keine Missionen für Tests löschen oder überschreiben.

## 6. Abgrenzung zur Web-App

Die Web-App hat inzwischen **PR #8** auf `main`: https://github.com/studiobaff/dronemissions/pull/8. Dort sind einstellbare 3D-/Karten-/Fotovorschauen, mehrere Bilder ohne neue Missionsversion und Archiv-Ordner als Akkordeons umgesetzt. Doku: `dronemissions/docs/PREVIEWS.md`.

Diese Änderungen beim Zusammenführen erhalten; nicht durch den älteren Stand des Claude-Branches ersetzen. Web-Deployment läuft über GitHub/main. Die Bridge separat bauen. Keine lokalen Kundendaten, Originalmissionen oder Schlüssel ins öffentliche Repository aufnehmen.

## Rückgabe

Auf GitHub pushen, Branch und Commit nennen, geänderte Funktionen und echte Einschränkungen dokumentieren. Isolierte Unit-/UI-Tests mit synthetischen Daten ausführen, besonders Ordnerfilter/Mehrfachauswahl, Reihenfolge, Fehler/Stopp/Wiederaufnahme, Gerätewechsel, Import und Einstellungs-Migration. Screenshots der Oberfläche mit synthetischen Daten beilegen. Keine Erfolgsmeldung für einen nicht durchgeführten Gerätetest.

ChatGPT holt danach den Stand, prüft ihn, baut und installiert auf dem Mac. iPad-/RC-Pro-2-Tests folgen mit dem Nutzer.
