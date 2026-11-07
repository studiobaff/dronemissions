# Bedien-, Kompatibilitäts- und Abnahmetests

Alle Tests sind geplant, nicht durchgeführt. Kein Geräteschreibzugriff oder Flug wurde in diesem Arbeitsauftrag ausgeführt. Gerätebedienung und Tests folgen nach dem priorisierten USB-Import. Vorhandene Missionen nicht überschreiben; isolierte Kopien und Test-IDs verwenden.

## Profile getrennt führen

- Mavic 3 Cine + tatsächlich verwendeter Controller (noch offen).
- Mavic 4 Pro + DJI RC Pro 2.

Je Profil: Seriennummer intern, Drohnen-/Controller-Firmware, DJI-Fly-Version, Planer-Version, Transferweg, Datum, Region und Quelldatei-Prüfsumme erfassen. Kein Ergebnis zwischen Profilen oder nach Versionswechsel ungeprüft übernehmen.

## Testfolge

| ID | Durchführung | Beleg / bestanden wenn |
| --- | --- | --- |
| T01 – Planer/Transfer | Synthetische Testkopie mit klarer Punkt-ID über den vorhandenen Workflow bereitstellen; anschließend in DJI Fly öffnen und alle Einstellungen lesen | Position, Höhenbezug, Heading-Modus, Gimbalwerte, Aktionen und Reihenfolge stimmen überein; Laden allein genügt nicht |
| T02 – Bedienbarkeit Panorama | Am Gerät prüfen, welche Kameraaktionen Waypoint-Modus anbietet und ob Panorama darin ausführbar ist; sonst den sicheren Übergang zu manueller Panorama-Aufnahme bestimmen | Bildschirmbeleg und konkrete Bedienfolge pro Profil; Moduswechsel verändert Position/Heading nicht unbemerkt |
| T03 – Heading vs Kamera | Auf freiem Testplatz Nord-Landmarke nutzen. Heading 0°, POI aus, Gimbalzustand dokumentieren. Dieselbe Anfahrt aus unterschiedlichen Richtungen wiederholen | Flugzeugnase und optische Blickrichtung vor Auslösung getrennt messbar; Herkunft/Basis jedes Werts dokumentiert |
| T04 – Erstes Bild | Panorama nach Nordausrichtung auslösen; Bildschirmaufzeichnung und Rohbildfolge/Metadaten sichern | Richtung des tatsächlich ersten Bilds gegen Landmarke bestimmt; interne Vorrotation erkannt. Nordstart nur bei Einhaltung der vereinbarten Toleranz bestätigt |
| T05 – Wiederholung | Mindestens drei Besuche desselben Punkts, einschließlich neuem Start und erneut geladener Mission; später zweiter Termin | Horizontale/vertikale und Winkelabweichungen protokolliert. Messverfahren und Unsicherheit angegeben; GNSS-Sollwerte allein sind kein unabhängiger Genauigkeitsnachweis |
| T06 – anderer Start | Nach erfolgreicher Basisprüfung anderen sicheren Start mit bekannter Höhendifferenz verwenden; relative Zielhöhe fachlich neu berechnen und vor Flug prüfen | Zielkamerahöhe innerhalb vereinbarter Toleranz. Separat testen, ob App alte Höhen unverändert übernimmt; keine Annahme automatischer Korrektur |
| T07 – Home Point | Wirkung einer zulässigen Home-Point-Aktualisierung auf Anzeige/Referenzen anhand Bedienung und Logs prüfen | RTH-Ziel und Höhenreferenz nachvollziehbar getrennt; bei Unsicherheit Startwechsel nicht freigeben |
| T08 – Stitch/Viewer | Beide Gerätepanoramen identisch verarbeiten; Bildmitte, Nordoffset und Standardblick dokumentieren; bekannte Landmarken prüfen | Norden stimmt im Viewer, Kartenradar und Zeitvergleich. Geänderte Stitch-Einstellungen erzeugen keine unbemerkte Rotation |
| T09 – 3D/3DGS | Kleines nicht vertrauliches Modell in installierter Pano2VR-Version laden; Maßstab und Achsen prüfen, zwei Knoten zuordnen | Position und Blick stimmen mit Landmarken überein; Übergang, Mobilbrowser und gewählte Dateiformate praktisch bestätigt |
| T10 – Kundenausgabe | Testprojekt mit Punktinformation und zwei synthetischen Terminen prüfen | Nur freigegebene Felder sichtbar; keine internen Pfade/Rohmetadaten; Änderungen hängen an konkreter Revision |

Bei Flugtests aktuelle Hindernisse, Kurven zwischen Waypoints und sicheren Abbruch berücksichtigen. Das Mavic-4-Pro-Handbuch weist darauf hin, dass die Route zwischen Punkten gekrümmt sein und dort tiefer verlaufen kann. [DJI Mavic 4 Pro Handbuch, Abschnitt 4.5](https://dl.djicdn.com/downloads/mavic-4-pro/20250513/DJI_Mavic_4_Pro_User_Manual_v1.0_en.pdf)

### T11 – Automatische Panorama-/Splat-Ausrichtung

Nach Abstimmung des Austauschformats mit Thomas Rauscher von Panotoury: ein nicht vertrauliches Testmodell einmal registrieren und mindestens drei Panoramen mit verschiedenen Positionen und bekannten Blickrichtungen gesammelt übernehmen. Ohne manuelle Einzelrotation müssen Position, Höhe und Landmarkenrichtung innerhalb vereinbarter Toleranzen stimmen. Danach mit einem weiteren Termin wiederholen. Fehlenden Nordbezug, abweichendes Höhendatum und eine neue Modellrevision gezielt prüfen: als unvollständig erkennen beziehungsweise neu berechnen. Eine reine GPS-Platzierung zählt nicht als bestandener Orientierungstest.

## Minimales Protokoll je Testlauf

`test_id`, Profil/Versionen, Missionskopie-Hash, Punktrevision, Start-ID, Zeitpunkt, Wetter/Wind, Bedienfolge, Sollwerte, beobachtete Werte, Messmethode/Unsicherheit, Bildschirm-/Bildbelege intern, Ergebnis, Abweichung und nächster Schritt. Nicht messbare Werte bleiben unbekannt. Gerätekompass bzw. EXIF-Yaw kann als Hinweis dienen, ersetzt aber nicht die optische Landmarkenprüfung.

## Noch konkret zu entscheiden

1. Welcher Controller und welche DJI-Fly-Version werden für die Mavic 3 Cine tatsächlich eingesetzt?
2. Bedeutet „Panorama beginnt nach Norden“ zwingend das erste Rohbild oder zunächst die optische Kameraausrichtung vor dem automatischen Ablauf? Das Modell hält beide getrennt; bis zur Klärung gilt keine Erstbildgarantie.
3. Kugelpanorama oder anderes Panoramaformat? Nur Hauptkamera? JPEG, DNG und welche Rohbildaufbewahrung?
4. Welche räumlichen und Winkelabweichungen sind für den Baustellenvergleich akzeptabel, und wie werden sie unabhängig gemessen?
5. Gibt es dauerhaft wiederbenutzbare Startmarken und belastbare Höhenpunkte? Bei Startwechsel: gleiche absolute Kamera-Höhe oder gleiche aktuelle AGL-Höhe?
6. Welche Pano2VR-Version/Lizenz ist vorhanden und welches 3D-/3DGS-Format liefert der bestehende Prozess?
7. Welche Informationen und welche Standortgenauigkeit dürfen Kunden sehen; wer gibt Punktrevisionen und Ergebnisse frei?

Diese Fragen blockieren weder den read-only-USB-Import noch die Archivierung. Sie blockieren nur die jeweils betroffene Aussage über automatische Ausführung, Wiederholgenauigkeit oder Veröffentlichung.
