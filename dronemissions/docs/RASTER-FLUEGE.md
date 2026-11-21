# Gemeinsames Raster mit Flügen

Eine gespeicherte Planung bleibt die bearbeitbare Quelle. Flug 1, Flug 2 usw. sind daraus erzeugte Abschnitte im selben Projekt. Eine neue Aufteilung verändert weder Polygon noch Rastergeometrie. Bereits exportierte Dateien bleiben als frühere Exporte mit Planungsrevision erhalten; sie werden nicht stillschweigend ersetzt.

Im Planer stehen drei Aufteilungen zur Wahl:
- Bisheriges Wegpunktlimit (bestehende Planungen bleiben kompatibel).
- Automatisch nach Minuten pro Akku, inklusive geschätztem Anflug, Rückflug und Reserve.
- Feste Anzahl Flüge, z. B. zwei statt drei. Budgetüberschreitungen werden ausgewiesen.

Der H-Marker wird gesetzt oder gezogen. Er dient für die Routenreihenfolge und die Akku-Zeitschätzung. Die Höhenreferenz wird nicht durch Ziehen des Markers geändert. Bei DEM müssen H und der DEM-Startpunkt übereinstimmen.

An-/Rückflug werden horizontal als Luftlinie und vertikal mit einstellbarer Geschwindigkeit geschätzt. Diese Wege werden nicht als hindernisgeprüfte Flugwege exportiert. Manöver werden mit einem pauschalen Stoppzuschlag sowie der gewählten Reserve berücksichtigt. Wind, Akku und tatsächliche Rückkehrhöhe bleiben vor Ort zu prüfen. Die Zeit ist keine garantierte Akkulaufzeit.

Fortsetzungen überlappen um bis zur gewünschten Strecke; die Überlappung wird bei kurzen Flügen auf ein Viertel der vorherigen Flugstrecke begrenzt. Lange gerade Bahnen können im Inneren geteilt werden. Löcher, getrennte Bereiche und Kreuzraster bleiben getrennt. Eine feste Anzahl unterhalb dieser Mindestanzahl oder oberhalb der Wegpunktkapazität wird abgelehnt.

Die Projektansicht gruppiert exportierte Flüge unter der gemeinsamen Planung. Frühere Exportrevisionen bleiben zugänglich. Die Kamerawahl ist weiterhin ein Berechnungsprofil; die DJI-Gerätekennung wird einmal pro Planung aus einer passenden Referenz-KMZ zugeordnet und mitgespeichert.


## Manuelle Aufteilung einschließlich Helix

Unter „Flüge innerhalb dieser Planung → Manuell: Anzahl Abschnitte festlegen“ ist 1 eine zusammenhängende Mission. Helix, Doppelhelix und Kreis unterstützen dieselbe Einstellung wie Raster, Korridor und Linie. Zeitüberschreitung oder mehr als 200 Wegpunkte erzeugen Hinweise, erhöhen aber die manuelle Anzahl nicht. Physisch getrennte Rasterketten (z. B. ausgesparte Flächen) werden nicht automatisch überbrückt.

Bei manueller Doppelhelix werden Auf- und Abstieg verbunden: an der Spitze der Halbkugel/Kalotte direkt, beim Zylinder über Stützpunkte am oberen Halbkreis. Diese Verbindung enthält keine Fotoaktionen. Bestehende Flugdateien bleiben unverändert. Ohne H werden bei manueller Aufteilung keine An-/Rückflugzeiten erfunden; die Anzeige weist darauf hin. Die DJI-App muss Import und Fortsetzen für das konkrete Gerät unterstützen; dies wurde nicht durch einen Flugtest bestätigt.

Automatische Trennstellen verwenden den letzten passenden Stützpunkt nahe der Zeitgrenze. Zuvor wurde durch eine veränderte Suchgrenze irrtümlich der erste Kandidat gewählt, wodurch bis zu 15 Prozent Abschnittslänge verloren gingen. Flugdetails zeigen Route, An-/Rückflug und Reserve getrennt.

## Fotos ohne erzwungene Stopps

Ab Generator 0.7.3 bedeutet Fotopause 0 s bei Routenaufnahmen: Innenpunkte im Durchflug, keine Hover-Aktionen, keine zeitgesteuerte Kameraausrichtung an jedem Foto. Die Kamera wird am Abschnittsanfang ausgerichtet und ihre Neigung zwischen benachbarten Punkten interpoliert. Start und Ende jedes Abschnitts bleiben Haltepunkte. Nur Aufnahmepunkte lösen Fotos aus; Verbindungs- und Geländepunkte erhalten keine Fotoaktion.

Die nominale Routenzeit enthält bei 0 s keine pauschalen zwei Sekunden pro Foto mehr. Vorschau, Abschnittsbudget und KMZ-Dauer verwenden denselben entfallenen Fotozuschlag. Tatsächliches Abbremsen an engen Wendungen ist damit nicht ausgeschlossen. Eine ausdrücklich gesetzte positive Fotopause und stationäre Panoramen behalten ihre Stopps. Vorhandene KMZ-Dateien ändern sich nicht: Planung mit 0 s Pause erneut speichern und exportieren. Tests prüfen beide XML-Dokumente, Fotoanzahl, Durchflugmodus, fehlende Hovers und die Zeitberechnung; kein Hardware-Flugtest.
