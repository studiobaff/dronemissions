# UI-Handover für Claude · 10. November 2026

**Hier anfangen:** [Startprompt](STARTPROMPT.txt), anschließend das vollständige
[Briefing mit Abnahmekriterien](BRIEFING.txt).

Dieser Branch enthält den aktuellen stabilen Anwendungscode und den vollständigen,
geordneten Gestaltungsauftrag. Das lokale ZIP und Remote Control sind nicht nötig.

## Auftrag

- Kompakte Liste: Griff links, Positionsnummer ohne Klammern, Titel und Chips,
  Öffnen-Button und **Checkbox rechts**.
- Klarere Akzentfarben und abgestimmte Kacheln, Kartenlinien und Marker.
- Deutsch, Englisch und Ukrainisch in Oberfläche und PDF, mit geeigneter Schrift.
- Antrag-/Informations-PDF: ausgewogene Abstände, Logos, **Legende und Quellen**,
  Missionen/Punkte als kompakte Tabelle. Keine internen Status- oder Bedienabsätze.

## Beispiele des bisherigen Teststands

Diese Beispiele sind **keine Designvorlage**. Sie dokumentieren den funktionalen
Zwischenstand und die zu korrigierenden Layoutprobleme mit synthetischen Daten.

- [Liste](beispiele/mission-list-demo.png): Checkbox noch links, muss nach rechts.
- [Einzelkarte](beispiele/mission-map-round.png): Marker/Linien gestalterisch überarbeiten.
- [Panorama-Planer](beispiele/planner-kugelpanorama.png).
- [PDF](beispiele/Einzelmission-Demo-rund.pdf) und [gerenderte Kartenseite](beispiele/round.png):
  insbesondere Leerflächen, Absatzlisten und Typografie verbessern.

Private Projektscreenshots, echte Missionen, Zugangsschlüssel und Mailkonfigurationen
sind nicht veröffentlicht. Die unfertige Benutzerverwaltung gehört nicht in diesen PR.

## Getrennte Arbeitsstände

- Basis: `main` bei `a327f1f3a7e7a45fbcb0a32f320aec6d56922e22`.
- Claudes `claude/nature-overlay-opt-in` (`57d7f15`) ist ein separater, nicht
  gemergter Verhaltensänderungs-Branch. Nicht stillschweigend mit dem Layout vermischen.
- Benutzerverwaltung: separater, noch ungeprüfter lokaler Codex-Arbeitsstrang.
- RC-Tests: noch offen, nach der Gestaltung und technischen Prüfung.

Bitte einen eigenen Arbeitsbranch erstellen und PR/Commit, Screenshots und zwei
repräsentative PDF-Exporte zurückgeben. **Nicht main mergen oder deployen:** Codex
übernimmt Review, Regressionen und Veröffentlichung. Main deployt automatisch.
