# Kleines fachliches Datenmodell

Version 0.1; bewusst kein WPML- oder DJI-Fly-Schema. `null` bedeutet unbekannt, niemals stillschweigend 0. Beispiele sind synthetisch und nicht flugfähig.

| Objekt | Pflichtinhalt | Zweck |
| --- | --- | --- |
| `point` | ID, Projekt-ID, Revision, Status, horizontales CRS und Koordinaten, Höhe mit Bezug/Quelle, Aufnahmerezept | Dauerhaft wiederkehrender Aufnahmeort |
| `takeoff` | eigene ID, horizontale Position, Höhe mit Bezug/Quelle/Unsicherheit, Datum | Terminbezogener Abflug und Höhenbezug |
| `mission_binding` | Punkt-ID/Revision, Planer/Version, Quelldatei-Hash, Geräteprofil, Start-ID, abgeleitete Ausführungshöhe und deren Bezug | Spätere Verbindung zur extern geplanten Route; keine Kopie als neue Punktidentität |
| `visit` | ID, Punkt-ID/Revision, Zeitpunkt mit Zeitzone, Geräte-/Versionsprofil, Start-ID, Soll-/Istwerte und Prüfstatus, Asset-IDs | Ein Baustellentermin, auch bei fehlgeschlagener Aufnahme |
| `asset` | ID, Besuch-ID, Typ, interner Speicherverweis, Prüfsumme, Verarbeitungsversion, geografischer Nordbezug/Viewer-Standardblick | Rohsequenz, Stitch, Tourknoten oder 3D-Verknüpfung |
| `approval` | Punktrevision oder Asset-ID, Umfang, Status, Zeitpunkt, Akteur | Kundeninhalt und operative Freigabe getrennt |

## Feldregeln

- Horizontale Position als benanntes `latitude_deg`/`longitude_deg`, CRS `EPSG:4326`; bei GeoJSON wäre die Reihenfolge dagegen Longitude, Latitude. Kein eigener Export jetzt.
- Höhe als `{value_m, reference, source, uncertainty_m, takeoff_id}`. `takeoff_id` ist bei `relative_to_takeoff` Pflicht. Absolute Höhen dürfen nicht ohne Datum konvertiert werden. `agl` benötigt Geländequelle und Erfassungsdatum. Unbekannte Unsicherheit bleibt `null` und sperrt eine behauptete Genauigkeitsfreigabe.
- `capture_recipe` speichert Panorama-Art, Kamera/Objektiv, Aufnahmeformat sowie Belichtungs-/Weißabgleichsstrategie. Einzelbildzahl und Reihenfolge erst nach verifiziertem Geräteprofil festlegen.
- Alle fachlichen Azimute sind Grad im Uhrzeigersinn ab geografischem Norden, Bereich `[0,360)`. Heading-Modus, Flugzeugazimut, Gimbal-Yaw und dessen Bezug sind eigenständige Felder. Herstellerspezifische Rohwerte zusätzlich unverändert mit Herkunft speichern.
- Aktuell `start_policy=north`, `requested_pre_capture_camera_azimuth_deg=0`. Eine spätere wählbare Ausrichtung erfordert eine neue Rezeptrevision, nicht Umdeutung bestehender Besuche.
- `visit.orientation` unterscheidet `observed_pre_capture_camera_azimuth_deg`, `observed_first_frame_azimuth_deg` und jeweilige Nachweismethode/Unsicherheit. `unverified`, `passed`, `failed` oder `not_supported`; keine leere Prüfung als Erfolg auslegen.
- `asset.alignment` speichert ermittelte Richtung der Bildmitte und zugehörige Pixelkonvention, angewendete Rotation, Landmarkenreferenz, Unsicherheit und separat `default_view_azimuth_deg`. Pano2VR-interne Pan-Werte separat speichern, bis deren Transformation geprüft ist.
- `asset.model_binding` hält Modell-ID/Revision, lokales Koordinatensystem, Transformation, Maßstab, Kamerapose und Prüfstatus. GNSS allein ist kein Nachweis einer korrekten Modellregistrierung.
- Toleranzen für Position, Höhe, Erstbildazimut und Viewer-Nordbezug sind projektbezogen zu vereinbaren. Ohne Werte kann ein Test messen, aber keine Eignung für den Kundenzeitvergleich bestätigen.
- Präzise Koordinaten und Rohdateipfade sind intern. Kundenausgabe erfolgt als explizite Auswahl freigegebener Felder und Revisionen.

## Vorbereitung der automatischen Splat-Zuordnung

`model_georeference` ergänzt das Modell um `model_id`, `model_revision`, geografisches und vertikales Bezugssystem, lokalen Ursprung, Achsenkonvention, Einheiten und die Transformation zwischen geografischem Bezug und Modell. Methode, Kontrollreferenzen, Unsicherheit und Prüfstatus gehören dazu. Die konkrete Serialisierung wird mit Thomas Rauscher von Panotoury abgestimmt; aktuell ist kein Austauschformat zugesagt.

Eine abgeleitete `panorama_model_pose` verknüpft Asset-ID, Modellrevision und Transformationsrevision mit lokaler Kameraposition und Blickorientierung. Position kommt aus der georeferenzierten Kameraposition; Orientierung aus dem Nordbezug des fertigen Panoramas und der Modellrotation. Berechnete Werte und manuelle Korrekturen getrennt speichern. Fehlt ein erforderlicher Bezug, Ergebnis als unvollständig markieren und keine automatische Ausrichtung als erfolgreich ausgeben.

## Revisionsregeln

Ein neuer Termin erzeugt einen Besuch, keinen neuen Punkt. Eine beabsichtigte Positions-/Höhen- oder Rezeptänderung erzeugt eine Punktrevision mit Begründung. Wird wegen Baufortschritt ein anderer Blickort benötigt, als neuer Punkt mit Verweis auf den Vorgänger kennzeichnen; keine scheinbar identischen Vorher-/Nachher-Bilder behaupten. Geräteprofil-Prüfungen gelten nur für die getestete Kombination aus Modell, Controller, Firmware, DJI Fly und Transfer-/Planerversion.
