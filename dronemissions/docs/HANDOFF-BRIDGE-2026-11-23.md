# Bridge-Kompatibilitätsprüfung · Übergabe 23. November 2026

Cloud-Sitzung ohne angeschlossenen Mac und ohne USB-Gerät. Alle Aussagen unten sind entweder geprüft (mit Prüfweg) oder ausdrücklich als offen gekennzeichnet. Keine Serveränderung, kein Deployment, keine echten Schlüssel oder Missionsdaten verwendet.

## 1. Quellstand und installierte App

| Gegenstand | Befund | Nachweis |
| --- | --- | --- |
| Bridge-Quellcode | `618aa5a9b52ad7d10e3b6efee8d4be7ce0461336` („Render active POIs … Bridge 0.6.2“, 8.11.2026) | Über GitHub-API und `git fetch origin <volle SHA>` geholt; die Kurzform ist nicht auflösbar, der Commit liegt nicht in der `main`-Historie (9 Commits auf einem Zweig ab `2ef45d8`, PR #8). `bridge/` ist in `main` nicht mehr vorhanden. |
| Versionsangaben im Quellstand | `desktop.VERSION='0.6.2'`, `CFBundleShortVersionString 0.6.2`, `CFBundleVersion 20261108.8` | `bridge/desktop.py`, `bridge/build_desktop.py` |
| Lokale Änderungen auf dem Mac | **unbekannt** | Kein Mac angebunden (Remote Control nicht verfügbar). Ein lokal abweichender Stand (Codex' Auslagerung, Patch `ccd63b9`/`e4ed6a0`) konnte nicht gelesen werden. |
| Installierte App aus diesem Quellstand gebaut? | **nicht nachweisbar** | Auf dem Mac prüfen, siehe unten. |

Prüfweg auf dem Mac (liest nur, verändert nichts):

```bash
defaults read /Applications/dronemissions-bridge.app/Contents/Info.plist CFBundleShortVersionString
```

```bash
defaults read /Applications/dronemissions-bridge.app/Contents/Info.plist CFBundleVersion
```

```bash
stat -f '%Sm %N' /Applications/dronemissions-bridge.app
```

Erwartung für einen Build aus `618aa5a`: `0.6.2` und `20261108.8`. Weicht `CFBundleVersion` ab oder ist das Änderungsdatum nach dem 8.11.2026, stammt die App aus einem anderen (lokalen) Stand. Zusätzlich im lokalen Bridge-Projekt `git status --short` und `git log -1 --format=%H` mit `618aa5a…` vergleichen; die ZIP-Prüfsumme im Webarchiv-Dialog **Bridge** gegen das installierte Paket halten.

## 2. Geprüfter Webarchiv-Stand

| Gegenstand | Befund |
| --- | --- |
| Live-Server `service.studiobaff.com/dronemissions/` | Header `X-Drone-Release: 27b770c59c687a78197b44fb0ff2a2c378535ae5` = aktueller `main`-HEAD. Der Server ist **nicht** älter als `main`; der abgebrochene Deploy-Lauf 110 wurde durch spätere Läufe überholt. PHP 8.3.36, API `session` antwortet wie erwartet. |
| Patch `ccd63b9` / `e4ed6a0` (QR-/Kurzcode-Download) | **Weder auf GitHub noch auf dem Server vorhanden** (GitHub-API: „No commit found“). Live-Probe mit geratenen Aktionsnamen ohne Anmeldung zeigt nur das normale 401; ein Kurzcode-Endpunkt ist damit weder bestätigt noch ausgeschlossen. Nicht prüfbar; Schnittstellenvertrag dafür in `BRIDGE.md`. |
| Lokale Prüfinstanz | `main` `27b770c`, PHP 8.3.6 (Linux), SQLite, synthetische Admin-Identität mit lokalem STARTTLS-Postfach, Loopback. |

## 3. Bestandene Tests

**A. Unveränderter 0.6.2-Client (`tests/fixtures/bridge062`, identisch mit `bridge/archive.py` aus `618aa5a`) gegen die lokale Instanz** – `tests/device-access.py` (bestehend) und neu `tests/bridge-compat.py`, beide bestanden:

1. Geräteanmeldung: Browser-Login per E-Mail-Code erzeugt den Schlüssel; Bridge meldet sich mit `login`/`password` an, Antwort `role: device`; alter gemeinsamer Schlüssel wird mit Hinweis abgelehnt.
2. Mission **BRIDGE-KOMPATIBILITAETSTEST** (4 Wegpunkte, Fotoaktion je Punkt, synthetische Koordinaten) mit Titelbild in Projektordner gesichert → Version 1.
3. Wiederfinden: richtiger Projektordner, Name und Dateiname `BRIDGE-KOMPATIBILITAETSTEST.kmz` erhalten, Prüfsumme und Größe gleich, Wegpunktzahl 4 = 4, Strecke Server 129,6 m / Bridge 129,64 m, Format KMZ/übertragbar, Vorschau als JPEG.
4. Download: bytegleich zum Upload, ZIP-Test fehlerfrei, WPML lesbar, Bridge-Parser liefert identische Metadaten.
5. Erneutes Sichern derselben Datei in ein anderes Projekt: vorhandener Eintrag wird verschoben, kein Duplikat; Rückverschieben erhöht die Revision.
6. Fehlerbehandlung: unbekannter Ordner (404), Nicht-KMZ durch Gerät (403), veraltete Revision (409), Eigentümeraktionen `settings`/`shares`/`device-keys`/`bridge`/`bridge-config`/`versions` für Geräte gesperrt (403) – jeweils mit lesbarer Meldung.
7. Ablage: Server speichert nur SHA-256 des Schlüssels; Versionszeile und Blob (`blobs/<sha256>.kmz`) stimmen.
8. Widerruf beendet die laufende Bridge-Sitzung sofort.

**B. Bridge-Quellstand `618aa5a`, isolierte Tests offscreen (Linux, PySide6 6.10.3, pymobiledevice3 11.50.0):** 113 Tests bestanden, wie dokumentiert.

**C. Bridge 0.6.3 (Patch `bridge-patches/0001-…`):** 123 Tests bestanden (10 neue: Geräterolle, kein Schlüssel nach Fehlanmeldung, einmalige Erneuerung bei GET und Multipart-POST, Widerruf ohne Wiederholungsschleife, Anzeige „Gerätezugang“). Zusätzlich gegen die echte PHP-Instanz: serverseitig abgelaufene Sitzung → `library` und `upload` werden nach genau einer Neuanmeldung erfolgreich wiederholt, neue Sitzungs-ID; nach Widerruf Abbruch mit Servermeldung und ohne weitere Anmeldeversuche. Die 34 Prüfpunkte aus A bestehen auch mit dem 0.6.3-Client.

**D. Live-Server (nur unauthentifiziert, 4 Anmeldeversuche mit ungültigen Schlüsseln):** `session` liefert CSRF; `login` mit Schlüssel alter Form → 401 „Bitte einen neuen Geräteschlüssel … erstellen“; mit zufälligem `dmb_`-Schlüssel → 401 „ungültig, abgelaufen oder widerrufen“; `library` ohne Sitzung → 401. Das bestätigt Pfad, CSRF-Fluss und Fehlerformat am Live-Server, **nicht** eine erfolgreiche Anmeldung.

## 4. Offene oder nicht ausführbare Gerätetests

Nichts davon wurde ausgeführt; ein bestandener API-Test ersetzt keinen USB-/DJI-Fly-Test.

- Installierte App lesen und mit `618aa5a` vergleichen (Prüfweg oben).
- iPad per USB: Erkennung (pymobiledevice3/usbmux, Sandbox über `InstallationProxyService.lookup`), **Neu anlegen** der Testmission, Sichtbarkeit und erneutes Öffnen in DJI Fly, Rückimport ins Webarchiv.
- RC-Controller per USB (ADB, `/sdcard/Android/data/dji.go.v5/files/waypoint`): Erkennung getrennt prüfen. **Einschränkung laut Quellstand:** geprüft ist nur das **Ersetzen eines vorhandenen, in DJI Fly registrierten Missionsplatzes** nach vollständiger Sicherung; „Neu anlegen“ ist auf Android als experimentell gekennzeichnet, eine früher neu angelegte Kennung war nach Controller-Neustart in DJI Fly nicht sichtbar. Bestehende Missionen werden nie ungefragt ersetzt oder gelöscht (Ersetzen braucht ein ausdrücklich markiertes Ziel).
- Rückimport-Vergleich: DJI Fly kann beim Speichern Wegpunkt-Turn-Parameter, Vorschaubild und Metadaten verändern; die zurückgelesene KMZ ist dann **nicht** bytegleich. Vergleich erfolgt über `inspect_kmz` (Wegpunkte, Koordinaten, Höhen, Geschwindigkeiten, POIs, Aktionen) statt über identische Prüfsummen; Unterschiede sind zu erklären.
- Kein Flug.

Vorschlag für den koordinierten USB-Test (nur mit angeschlossenem Mac, Nutzer bestätigt jeden Schritt): 1) App-Stand lesen, bisherige App als Rückfallkopie sichern; 2) Testmission aus dem Webarchiv-Projekt in die Warteschlange, Modus **Neu anlegen** (iPad); 3) DJI Fly schließen, übertragen, Rücklese-Journal prüfen; 4) DJI Fly öffnen, Mission öffnen, schließen, erneut öffnen; 5) Mission anhaken und **Im Webarchiv sichern** in dasselbe Projekt; 6) Archiv-Chip/Prüfsumme vergleichen, bei Abweichung beide KMZ mit `inspect_kmz` gegenüberstellen.

## 5. Notwendige Änderungen

**Bridge (Patch, nicht installiert):** `bridge-patches/0001-bridge-0.6.3-geraeteschluessel-sitzung.patch` gegen `618aa5a`.
- Abgelaufene 12-Stunden-Gerätesitzung wird einmal erneuert statt mit „Gerätezugang abgelaufen“ abzubrechen; ein widerrufener Schlüssel löst keine weiteren Anmeldungen aus (Serverlimit 10 je IP in 15 Minuten).
- Anzeige „Verbunden als Gerätezugang“ statt „Freigabe“.
- Version 0.6.3, `CFBundleVersion 20261123.1`, User-Agent mit Version, README-Abschnitt.
- Vor dem Austausch der installierten App: bisherige `dronemissions-bridge.app` als Rückfallkopie sichern, Build, Signatur-/ADB-Prüfung, Installation, Gerätetest – alles nur auf dem Mac.

**Webarchiv (in diesem Branch, kein Deployment):** `tests/bridge-compat.py` plus Aufruf in `run-email-suite.py`; `docs/BRIDGE.md` (Befund, Schnittstellenvertrag), `docs/UPDATE.md`, dieser Bericht. Kein Codefehler im Webarchiv gefunden, der die Bridge betrifft.

**Für den QR-/Kurzcode-Patch:** vor Veröffentlichung `python3 dronemissions/tests/run-email-suite.py` ausführen; `device-access.py` und `bridge-compat.py` müssen unverändert bestehen. Die Tabelle in `BRIDGE.md` nennt die Aktionen und Felder, die unverändert bleiben müssen.

## Reproduktion

```bash
python3 dronemissions/tests/run-email-suite.py
```

Bridge-Tests nach Anwenden des Patches:

```bash
cd bridge/tests && QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s . -v
```
