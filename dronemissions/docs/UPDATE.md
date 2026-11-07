# Update vom GitHub-Branch auf den Server

Übergabe für die Person oder den Assistenten, der den Webserver betreut. Stand: 7. November 2026.

## Was wo liegt

- Quelle: `https://github.com/studiobaff/dronemissions`, Branch `claude/drone-missions-ui-handoff-4nsj6e` (nach dem Merge in `main`: Branch `main`).
- Das Repository ist öffentlich. Das ist in Ordnung, weil es nur Code, Doku und synthetische Beispiele enthält. Zugangsschlüssel, `config.json`, `missions.sqlite`, `blobs/`, `sessions/` und `tmp/` liegen im privaten Verzeichnis außerhalb des Webroots und sind per `.gitignore` ausgeschlossen. Niemals private Daten ins Repository legen.
- Auf dem Server wird nur der Inhalt von `dronemissions/public/` ausgeliefert. Alles andere (Tests, `tools/`, `bridge/`, Doku) bleibt außerhalb des Webroots.

## Schritte

1. Datenbank und `blobs/` sichern (siehe `DEPLOYMENT.md`, Abschnitt Updates und Backups).
2. Aktuellen Stand holen, zum Beispiel in ein Arbeitsverzeichnis auf dem Server oder auf dem Mac:

```sh
git clone --branch claude/drone-missions-ui-handoff-4nsj6e --depth 1 https://github.com/studiobaff/dronemissions.git dronemissions-src
```

Bei vorhandenem Arbeitsverzeichnis stattdessen `git fetch origin && git checkout claude/drone-missions-ui-handoff-4nsj6e && git pull`.

3. Nur `public/` in den Webroot kopieren, ohne private Dateien zu überschreiben:

```sh
rsync -av --delete --exclude 'config.json' dronemissions-src/dronemissions/public/ /usr/local/www/vhosts/studiobaff/dronemissions/
```

Zielpfad an die Installation anpassen. `--delete` entfernt veraltete Dateien aus dem Webroot; der private Ordner liegt nicht darunter und ist nicht betroffen.

4. Schema-Ergänzung: Diese Version legt beim ersten Aufruf automatisch die Spalten `overview_waypoint`, `overview_version`, `litchi_url` und die Tabelle `mission_attachments` an, falls sie fehlen (`dm_migrate()` in `lib.php`). Bestehende Daten werden nicht verändert.

5. Prüfen: HTTPS-Aufruf, Login, Bibliothek, eine Mission öffnen, Download einer Originaldatei, Karte mit Panel „Karte & Zonen“. PHP-Syntax bei Bedarf mit `php -l` auf `api.php`, `lib.php`, `zones.php`, `address.php`, `location.php`.

## Bridge

Die Bridge-App wird nicht auf den Server kopiert. Sie wird auf dem Mac aus `bridge/` gebaut und ersetzt `/Applications/Drone Missions Bridge.app`:

```sh
cd /Users/florianfrey/Documents/missionplaner && git pull origin claude/drone-missions-ui-handoff-4nsj6e
python3 -m unittest discover -s bridge/tests
rm -rf work/bridge-build && python3 bridge/build_desktop.py
rm -rf "/Applications/Drone Missions Bridge.app" && cp -R "outputs/Drone Missions Bridge.app" /Applications/
```

Damit die Web-App die Bridge zum Download anbietet (Dialog „Bridge“), das gebaute Paket als ZIP in den privaten Serverordner legen, außerhalb des Webroots:

```sh
cd outputs && ditto -c -k --keepParent "Drone Missions Bridge.app" "Drone-Missions-Bridge-macOS.zip"
# dann z. B. per scp nach privat/dronemissions/bridge/Drone-Missions-Bridge-macOS.zip
```

Erlaubte Endungen: zip, dmg, pkg, exe, msi, txt, md. Dateinamen mit „mac“ oder „win“ werden der Plattform zugeordnet. Die Web-App berechnet die SHA-256-Prüfsumme beim ersten Aufruf und zeigt sie im Dialog. Ein Windows-Paket entsteht nur auf einem Windows-Rechner (`bridge/README.md`, Abschnitt Windows 11).
