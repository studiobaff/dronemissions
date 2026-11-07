# Import-Untersuchung – Arbeitsstand

Stand: 7. November 2026. Kein Abschlussbericht und keine bestätigte Erklärung für alle früheren Fehler.

## Ziel

KMZ und Vorschaubild vollständig übertragen, vorhandene Missionen sichern, Übertragung zurücklesen und DJI-Fly-Sichtbarkeit getrennt bestätigen. Plattformen getrennt behandeln: iOS und Android/DJI RC Pro 2.

## Bisher belegte Beobachtungen

- Bestehende Injector-Logs meldeten bei früheren Android-Versuchen `Mission replaced successfully`, obwohl unmittelbar zuvor `adb push` mit `remote fchown failed: Operation not permitted` fehlgeschlagen war. Vor dem fehlgeschlagenen Push wurde die alte KMZ gelöscht. Das ist ein belegter Fehler in Fehlerbehandlung/Erfolgsmeldung dieses Ablaufs; es beweist nicht automatisch die Ursache jedes fehlenden Eintrags.
- Fehlende lokale KMZ kann auch ein noch nicht heruntergeladener Cloud-Eintrag sein. Aus einem leeren UUID-Ordner allein darf kein Datenverlust abgeleitet werden.
- Beim iPad enthalten frühere importierte Datenbankeinträge relative `filePath`-Werte, native Einträge absolute Sandbox-Pfade. Importierte Anzeigenamen waren pauschal `Injected Mission`. Ob die relativen Pfade die fehlende Anzeige verursachen, ist noch nicht bestätigt.
- Auf dem aktuellen iPad konnte die reale DJI-Fly-Sandbox mit `InstallationProxyService.lookup` und `Container` ermittelt werden. Sie weicht von älteren gespeicherten Sandbox-Pfaden ab. Pfade nicht aus einer beliebigen alten Datenbankzeile ableiten.
- MTP-Zugriff am Mac war durch `ptpcamerad` belegt. Nach Freigabe öffnete die MTP-Sitzung, die Bestandsabfrage war aber nicht zeitnah erfolgreich. Der Versuch wurde beendet. MTP wird für den aktuellen Controller-Test nicht verwendet.
- ADB erkannte danach die RC Pro 2 als autorisiertes Gerät. DJI Fly auf dem Controller: 1.21.18.
- Der erreichbare Waypoint-Bestand des Controllers wurde lokal gesichert. Produktionsdaten und Seriennummern gehören nicht ins öffentliche Repository.

## Aktueller kontrollierter Test

- Genau eine neue Testmission mit neuer UUID statt Ersetzen vorhandener Missionen.
- Quelle: vom Nutzer bereitgestellte Map-Creator-Doppelhelix; Original unverändert. Kein Flug ausgeführt.
- Neue Dateien werden zuerst unter temporären Namen geschrieben und zurückgelesen. Erst danach werden sie an den endgültigen Ort umbenannt.
- ADB-Übertragung erfolgt mit binärem stdin über `adb shell -T 'cat > ...'`, damit kein fchown aus `adb push` erforderlich ist.
- Vollständige Sicherung vor Änderung, lokale Prüfsummen, Transaktionsprotokoll und Wiederherstellungsversuch bei Fehlern.
- KMZ und JPEG wurden nach finalem Umbenennen zurückgelesen und mit SHA-256 geprüft.
- Ergebnis bisher: `files-verified`; **DJI-Fly-Registrierung, Sichtbarkeit, Anzeigename und Öffnen noch nicht bestätigt**.
- Die Android-Missionsdatenbank ist mit normalem ADB nicht zugänglich. Es wurde kein Root-Zugriff eingerichtet und keine private Datenbank umgangen.
- Auf Android wurde kein eigener Anzeigename in die private DJI-Datenbank geschrieben. `name` im Transferplan bezeichnet bisher den Archivnamen.

## Tests der eigenen Übertragungslogik

Unit-Tests decken Parser/Koordinatenvalidierung, Ablehnung von XML-Entities, veränderte Quelldateien, gefälschte Zielpfade, Erhaltung vorhandener Dateien bei Staging-Fehlern sowie Rücklesefehler mit Wiederherstellung ab. Sie ersetzen keinen DJI-Fly-Gerätetest.

## Noch zu bestätigen

1. Wird die neu kopierte UUID überhaupt als Mission in DJI Fly angezeigt?
2. Ist sie zu öffnen, und stimmen Route, Wegpunktzahl, Höhe und Vorschau?
3. Woher kommen Anzeigename und Metadaten auf Android, und welche davon sind ohne geschützte Datenbankzugriffe aktualisierbar?
4. Wenn eine neue UUID nicht registriert wird: zuverlässiger, expliziter Ersatz einer lokal vorhandenen Mission und Verhalten bei erneutem Start/Cloud-Sync.
5. Vergleichstest iOS mit aktueller Sandbox und konsistenten Datenbankmetadaten.

## Späterer Bericht an Kilian

Erst nach bestätigtem Ergebnis: reproduzierbare Schritte, genaue Software-/Geräteversionen, bestätigte Ursache, kleinste wirksame Änderung, Rücklese-/UI-Ergebnis und Grenzen. Keine Schlüssel, Seriennummern, Benutzerdaten, echten Missionsdateien oder privaten Koordinaten veröffentlichen. Noch kein Issue oder Nachricht versendet.

## Bestätigtes Gerätetestergebnis

Der Nutzer hat am 7. November 2026 bestätigt: Der zuvor neu angelegte native DJI-Fly-Eintrag „Neusiedlersee“ (3 Punkte) wurde nach dem gesicherten Ersatz in DJI Fly sichtbar durch die Doppelhelix ersetzt. Es wurde kein Flug getestet oder freigegeben.

Der Test mit einer frei neu angelegten UUID war zuvor trotz zurückgelesener Dateien nach Controller-Neustart nicht in DJI Fly sichtbar. Dieser Versuch verwendete eine großgeschriebene `.KMZ`-Endung und shell-eigene Dateisystemobjekte. Dateiendung, Verzeichnisrechte und fehlende Datenbankregistrierung wurden dabei nicht getrennt isoliert. Deshalb ist nicht bewiesen, dass neue Missionen auf Android grundsätzlich unmöglich sind oder dass allein die Datenbankregistrierung die Ursache war.

Der erfolgreiche Ersatz verwendete den von DJI Fly registrierten nativen UUID-Ordner, dessen bestehende kleingeschriebene `.kmz`-Datei, eine temporär geschriebene und verifizierte Quelldatei sowie explizite Leserechte für die neue Datei. DJI Fly wurde vor Sicherung und Schreiben per `am force-stop` beendet. Das zugehörige JPEG aus dem Map-Creator-Ordner wurde separat an den bestehenden UUID-Vorschaubildpfad übertragen und zurückgelesen. Der Nutzer erwähnte Kilians eigenes Vorschaubild; eine unabhängige Bestätigung der konkreten Bilddarstellung, aller Wegpunkte/Höhen und des Android-Anzeigenamens steht noch aus.

Als vorläufig zuverlässiger Android-Ablauf gilt daher: einen ausdrücklich ausgewählten, bereits in DJI Fly registrierten lokalen Missionseintrag sichern und ersetzen. Reine Dateiintegrität und tatsächliche DJI-Fly-Sichtbarkeit bleiben getrennte Statuswerte. Der freie Neuimport bleibt experimentell. Die frühere falsche Erfolgsmeldung trotz `adb push`-Fehler ist weiterhin ein gesondert belegtes Problem.

## Speicherfehler nach dem ersten Ersatz

Der Nutzer konnte die Helix öffnen, aber nicht „Speichern und Verlassen“ verwenden. Damit ist der frühere sichtbare Ersatz KEIN vollständig erfolgreicher, nutzbarer Import. Nach ausdrücklicher Bestätigung des Nutzers, die Bearbeitung verlassen zu haben, wurde eine bereinigte Kopie vorbereitet und in denselben Testeintrag übertragen.

Strukturprüfung der Original-Helix: 118 Placemark-Wegpunkte, Indizes 0 bis 116 mit doppeltem Index 116. Die beiden letzten Wegpunkte enthalten dieselben Koordinaten, Höhen- und Aufnahmeparameter; lediglich waypointTurnMode unterscheidet sich. Die Kopie entfernt den vorletzten Duplikateintrag und erhält die letzte Turn-Einstellung, alle übrigen Wegpunkte und alle anderen ZIP-Einträge. Ergebnis: 117 Punkte mit lückenlosen eindeutigen Indizes. Das Original bleibt unangetastet. Der eigene Parser lehnt doppelte oder lückenhafte Wegpunktindizes jetzt vor Übertragung ab; entsprechender Regressionstest ergänzt.

Dies ist eine bestätigte Strukturabweichung, ihre Kausalität für den Speicherfehler ist erst nach dem nächsten DJI-Fly-Speichertest bestätigt. Die 118 Punkte allein überschreiten die von DJI aktuell dokumentierte Grenze von 200 Wegpunkten nicht. Referenz: https://support.dji.com/help/content?customId=en-us03400007343&documentType=artical&lang=en&paperDocType=paper&re=ID&spaceId=34

Das vom Nutzer bereitgestellte Foto zeigt weiterhin alte Drei-Punkt-Metadaten und See-Vorschaubild im nativen Testeintrag sowie eine ältere Helix mit 118 Punkten als separaten Eintrag. Die auf dem Gerät zurückgelesene KMZ des Testeintrags entsprach trotzdem weiterhin der übertragenen Helix. Diese Beobachtung belegt zusätzlich, dass Dateiinhalte und die Metadaten der Missionsliste auseinanderfallen können. Foto enthält private Missionsstandorte und darf nicht ungefragt veröffentlicht werden. „Donau“ mit vier Punkten blieb unverändert und ist separat gesichert.

## Rückschlag und Wiederherstellung

Der Nutzer meldete beim bereinigten Testeintrag „0 Punkte / leer“. Deshalb keine erfolgreiche Import- oder Speicherreparatur behaupten. Die originale native Drei-Punkte-KMZ, ShotSnap und JPEG-Vorschau wurden aus der Sicherung vor dem ersten Ersatz zurückgeschrieben und per SHA-256-Rücklesen bestätigt. DJI-Fly-Anzeige nach Wiederherstellung muss der Nutzer noch prüfen. „Donau“ wurde nicht verändert.

Die erste lokale Bereinigung verwendete ElementTree-Neuserialisierung. Dadurch können Namespace-Präfixe und XML-Darstellung gegenüber dem Herstellerformat verändert worden sein. Dieses Formatdelta muss vor weiteren Gerätetests separat untersucht werden; ein Strukturfehler der Quelle und ein Fehler des eigenen Reparaturwegs dürfen nicht vermischt werden. Weitere Schreibtests auf der Steuerung sind vorerst ausgesetzt.


## Spätere bestätigte Gerätetests vom 7. November 2026

- Direkter Austausch einer 12-Punkte-KMZ auf RC Pro 2: Punkte sichtbar, weder Speichern und verlassen noch Speichern als zunächst möglich. Nach Controller-Neustart konnte dieselbe Mission gespeichert werden; neue Vorschau entstand danach. Kein Nachweis, dass die Ursache ausschließlich eine Datenbankabweichung ist.
- Bereinigte Helix mit 117 eindeutigen Wegpunktnummern auf RC Pro 2: Punkte sichtbar, zunächst ebenfalls nicht speicherbar. Umbenennen aktualisierte die Kartenposition, aber erzeugte kein neues Bild. Der erfolgreiche Neustart-Ausweg wurde ausdrücklich für den 12-Punkte-Test bestätigt; kein unbestätigter Helix-Erfolg wird daraus abgeleitet.
- iPad: Neue Helix-Mission einschließlich neuem Datensatz, absolutem aktuellem Sandboxpfad, Name, 117 Punkten, vollständigen Punktpositionen, Strecke/Dauer und JPEG mit Titel angelegt. Nutzer bestätigte Sichtbarkeit, Cloud-Synchronisation, Herunterladen und Speichern auf dem anderen Gerät.
- Umbenennen ließ die eigene Vorschau erhalten. Speichern in DJI Fly kann das Bild verändern oder entfernen. Nach Austausch nur der vorhandenen JPEG wurde im Nutzertest das neue Bild nicht erneut zuverlässig über die Cloud auf bereits synchronisierte Einträge verteilt.
- Neue Titelgestaltung: unteres Drittel, große Schrift, seitlicher Sicherheitsabstand; Wolkensymbol oben links bleibt frei. Direkter Controller-Screenshot bestätigte das Overlay und den seitlichen Beschnitt.
- Bridge 0.2 implementiert diesen iOS-Weg für neue Missionen. Es werden keine bestehenden Gerätemissionen automatisch gelöscht. Netzwerkzugriff ist noch nicht umgesetzt.

Die genauen Unterschiede zwischen Litchis Controller-Übertragungsablauf und unserem Austausch sind weiterhin offen. Keine alleinige Ursache für alle beobachteten Symptome wird behauptet.
