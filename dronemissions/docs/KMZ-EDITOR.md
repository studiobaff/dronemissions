# DJI-KMZ im Archiv bearbeiten

Stand: 8. November 2026. Einstieg: Mission öffnen → **Wegpunkte bearbeiten**.

## Bedienung

Die große Karte zeigt die gespeicherte Route mit nummerierten Wegpunkten. Marker anklicken oder den Punkt in der Seitenleiste wählen. Marker ziehen, Breiten-/Längengrad eingeben oder mit den Richtungspfeilen ungefähr einen Meter verschieben. Höhe im Zahlenfeld ändern; der originale Höhenbezug steht unmittelbar darunter. Vor/Zurück wechselt den ausgewählten Wegpunkt.

**Wegpunkt löschen** entfernt den Punkt und seine punktgebundenen Aktionen aus dem Entwurf. **Zwischenpunkt danach einfügen** setzt einen Punkt zwischen dem ausgewählten und dem folgenden Punkt. Er übernimmt die sonstigen Punktparameter des vorherigen Punktes, aber keine Kameraaktionen. Pro ursprünglichem Zwischenraum kann vor dem nächsten Speichern ein neuer Punkt eingefügt werden. Mindestens zwei Punkte müssen verbleiben. Ein Anker eines gerade eingefügten Zwischenpunktes kann erst entfernt werden, wenn der Zwischenpunkt entfernt wurde.

Rückgängig und Wiederholen halten bis zu 50 Bearbeitungsstände. **Als neue Version speichern** legt eine neue KMZ-Version derselben Archivmission an. Original, ältere Versionen und zugehörige Projektdateien bleiben erhalten. Schließen fragt bei ungespeicherten Änderungen nach; Neuladen/Verlassen warnt ebenfalls. Gleichzeitige Archivänderungen werden als Versionskonflikt abgewiesen, statt sie zu überschreiben.

Nach Strukturänderungen (Einfügen/Löschen) den Punkt für die Projektkarte neu auswählen. Bei einer reinen Positions-/Höhenänderung folgt der bereits ausgewählte Projektkartenpunkt derselben Wegpunktnummer in der neuen Version. Ein aktives benutzerdefiniertes Vorschaubild wird bei jeder Wegpunktbearbeitung abgewählt, damit es keine veraltete Route zeigt; seine Bildhistorie bleibt erhalten. Bei Bedarf danach **Vorschau einstellen** verwenden.

## Unterstützter Umfang

- Genau eine ausführbare Flugroute mit 2–2000 fortlaufend nummerierten Wegpunkten.
- Höhen relativ zum Startpunkt oder über WGS84-Ellipsoid. Diese Werte sind **kein AGL**. Keine neue Gelände- oder Hindernisberechnung.
- Metadatenvorlagen ohne Wegpunkte (z. B. Map Creator) oder eindeutige `waypoint`-Vorlagen, deren Punkte, Höhe und Referenz mit der ausführbaren Route übereinstimmen.
- Positions-/Höhenänderungen aktualisieren Route und vorhandene Wegpunktvorlage zusammen. Geerbte globale Höhen werden für geänderte Punkte lokal gesetzt, vorhandene Ellipsoidhöhen um denselben Höhenunterschied korrigiert.
- Löschen/Einfügen nur bei eindeutig punktgebundenen `reachPoint`-Aktionsgruppen mit unterstützten Aktionen: takePhoto, gimbalRotate, rotateYaw, hover, zoom, focus. Mehrpunkt-Aktionsgruppen, Videoaktionen und unbekannte Aktionen sperren Strukturänderungen; Position/Höhe bleiben bearbeitbar, sofern die übrige KMZ-Struktur unterstützt wird.
- Aktionen, POIs, Geräteprofil, Richtungs-/Gimbalparameter und zusätzliche ZIP-Dateien werden erhalten. Der Editor zeigt vorhandene Aktionsnamen/Ausrichtungswerte zur Kontrolle, bearbeitet sie aber noch nicht. Die Kameraausrichtung wird beim Verschieben **nicht neu berechnet**.
- Die Kartenlinie verbindet die Wegpunkte; sie simuliert keine geflogenen Kurven. Distanz wird neu berechnet; eine vorhandene Dauer wird nur als Schätzung um die geänderte Reisezeit korrigiert. Bisherige Nicht-Reisezeit bleibt dabei erhalten, auch bei gelöschten Aktionen.

Nicht eindeutig passende Vorlagen, mehrere Flugrouten, nicht fortlaufende Indizes, zusätzliche nicht-null KML-Koordinatenhöhen und andere Höhenmodi werden mit einer verständlichen Fehlermeldung abgewiesen. Keine automatische Reparatur oder Konvertierung solcher Originale.

Bearbeitung ist nur für Eigentümer und projektberechtigte Bearbeitungsfreigaben verfügbar. Kunden mit Standortansicht erhalten auch serverseitig keinen Editorzugriff.

## Implementierung und Nachweise

`kmz-editor-core.php` bearbeitet XML gezielt in einer Kopie; `kmz-editor.php` prüft Rechte, Quellversion und Prüfsumme und legt die neue Version mit Änderungsjournal transaktional an. `kmz-editor.js` und `kmz-editor.css` sind vom Planer getrennt. Kleine Anschlüsse in app.js, api.php und view.html; kein Umbau an planner.js.

```sh
php dronemissions/tests/kmz-editor.php
python3 dronemissions/tests/kmz-editor-api.py --base http://127.0.0.1:18764/dronemissions/ --access /pfad/zur/isolierten/test-access.json
```

Die Tests prüfen Original-/Asset-Erhalt, Aktionen und POIs, Vorlagen-/Höhenkonsistenz, Strukturverweise, ungültige Änderungen, neue Versionen, alte Downloads, konkurrierende Änderungen, Vorschauhistorie, Projektkartenpunkt und Rechte/CSRF. API-Tests erlauben ausschließlich eine isolierte Loopback-Testinstallation mit synthetischen Missionen.

Browserprüfung am 8.11.2026: Ziehen, Dezimalhöhe, Löschen, Einfügen, Undo/Redo, Speichern und erneutes Öffnen (84,5 m bestätigt), Desktop 1280×720 und iPad-Größe 1024×768. Keine JavaScript-Fehler in diesem Durchlauf. Keine Geräte- oder Flugprüfung; bearbeitete Missionen vor Ausführung in DJI Fly kontrollieren.
