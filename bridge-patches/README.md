# Bridge-Patches

Der Bridge-Quellcode liegt nicht mehr in `main`. Die hier abgelegten Patches gelten gegen den letzten
Repository-Stand mit `bridge/`, Commit `618aa5a` (Bridge 0.6.2, nur über die vollständige SHA
`618aa5a9b52ad7d10e3b6efee8d4be7ce0461336` erreichbar; nicht in der `main`-Historie).

Anwenden im Bridge-Projekt (Arbeitskopie auf Stand 618aa5a oder dem daraus gebauten lokalen Stand):

```bash
git am --3way bridge-patches/0001-bridge-0.6.3-geraeteschluessel-sitzung.patch
```

Ohne Git-Historie: `patch -p1 < bridge-patches/0001-bridge-0.6.3-geraeteschluessel-sitzung.patch` im
Repository-Wurzelverzeichnis (die Pfade beginnen mit `bridge/`).

| Patch | Inhalt | Prüfung |
| --- | --- | --- |
| `0001-bridge-0.6.3-geraeteschluessel-sitzung.patch` | Geräteschlüssel-Sitzung (12 h) nach Ablauf einmal erneuern, keine Wiederholungsschleife bei Widerruf; Verbindung als „Gerätezugang“ anzeigen; Platzhalter nennt den Geräteschlüssel; Version 0.6.3 (`CFBundleVersion` 20261123.1); README-Abschnitt | 123 isolierte Tests offscreen (Baseline 618aa5a: 113), synthetische Rundläufe gegen eine lokale Installation des Webstands `27b770c`, siehe `dronemissions/docs/HANDOFF-BRIDGE-2026-11-23.md` |

Nach dem Anwenden: `cd bridge/tests && QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s . -v`, dann auf dem Mac
`python bridge/build_desktop.py`, Signatur-/ADB-Prüfung, vorherige App sichern, installieren, Gerätetest mit dem Nutzer.
