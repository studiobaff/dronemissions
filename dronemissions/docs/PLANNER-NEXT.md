# Nächste Ausbauschritte · 8. November 2026

Der Abschluss des Webplaners 0.5.0 ist in `PLANNER.md` und `UPDATE.md` dokumentiert. Berechnungs-, Export-, API- und Browserprüfungen erfolgen vor der Veröffentlichung; GitHub-Checks und Deployment bleiben der verbindliche Veröffentlichungsweg.

1. Neue Exporte auf iPad/DJI Fly und RC Pro 2 prüfen: Import, Vorschau, Speichern/Verlassen, Abschnittswechsel. Bisher kein Gerätetest dieser Planergeneration.
2. Beliebige DJI-KMZ als bearbeitbare Mission öffnen, Wegpunkte/Aktionen erhalten und Änderungen als neue Archivversion speichern. Gespeicherte eigene Planungen sind bereits bearbeitbar; allgemeiner KMZ-Editor fehlt noch.
3. Mehrere Map-Creator-KMZs mit gleicher Geometrie und jeweils einem veränderten Parameter vergleichen; keine pauschal optimale Geschwindigkeit behaupten.
4. Kreisraster/Circlegrammetry als eigene Flugart entwickeln; Randabdeckung, Kreismittelpunkte, verbindende Wege und Fotoaktionen gesondert validieren.
5. Publisher-Identität/Session/Rollen prüfen und gemeinsame Anmeldung integrieren. Administratoren verwalten; Kunden sehen freigegebene Orte und Navigation. Rechte serverseitig für Unterordner, Dateien und Export erzwingen. Keine zweite unabhängige Kontenverwaltung ohne diese Prüfung.
6. Höhenreferenzen zu einem expliziten Vermessungs-/Hindernismodell erweitern: Flugposition vs. Objektoberkante, Unsicherheit, unbekannte Bereiche. Der aktuelle globale Mindesthöhenansatz ersetzt diese Prüfung nicht.

Benutzerverwaltung ist auf Wunsch nach Abschluss des Planers eingeplant, nicht Teil des Planer-PR.
