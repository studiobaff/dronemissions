# Wiederverwendbare Panorama-Flugpunkte

Stand: 7. November 2026. Fachlicher Entwurf, keine Flugfreigabe und kein ausführbarer Missionsexport. Umfang ausschließlich `docs/panorama/`. Planung bleibt bei Litchi Hub und Map Creator; USB-Import und Webarchiv laufen unabhängig weiter.

## Ergebnis und belastbare Grenzen

Ein Panorama-Flugpunkt ist ein dauerhaft identifizierter Aufnahmeort mit explizitem Höhenbezug und Aufnahmeregeln. Eine Mission ist die terminbezogene Anfahrt zu einem oder mehreren dieser Orte. Ein Besuch speichert die tatsächlich entstandenen Aufnahmen und Abweichungen. Diese drei Objekte dürfen nicht zusammenfallen.

Vorgabe: Jeder Panorama-Aufnahmeablauf soll nach geografisch Norden ausgerichtet beginnen. Eine frei wählbare Startausrichtung ist später vorgesehen; sie ist heute nicht aktiviert. Der geografische Abflugort bleibt ein gesondertes Objekt.

DJI Fly unterstützt gespeicherte, wiederholbare Waypoint-Flüge für die Zielmodelle. Der DJI-Support beschreibt aber keinen regulären KML-Import für DJI Fly. Ein funktionierender Datei-/USB-Transfer beweist daher weder offiziellen Importsupport noch die Ausführung einer Panorama-Aktion. [DJI Fly Waypoint Flight](https://support.dji.com/help/content?customId=en-us03400007343&documentType=artical&lang=en&paperDocType=paper&re=ID&spaceId=34)

Die öffentliche Cloud-WPML-Referenz nennt bei den relevanten Feldern Enterprise-Modelle; Mavic 3 Cine und Mavic 4 Pro stehen dort nicht als unterstützte Produkte. Sie dient als Begriffshilfe, nicht als Kompatibilitätszusage für DJI Fly. Insbesondere bedeutet `heading=0` keine nachgewiesene identische Panorama-Orientierung beider Modelle. [DJI WPML Common Elements](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html)

## Vier getrennte Ausrichtungen

| Begriff | Bedeutung im Prozess | Nachweis |
| --- | --- | --- |
| Flug-/Waypoint-Heading | Richtung der Flugzeugnase; abhängig von Heading-Modus, POI und Flugsegment | Sollwert, Modus und beobachteter Wert getrennt erfassen |
| Gimbal-Yaw | Kameraschwenk um die Hochachse; Bezug entweder Flugzeug oder geografischer Norden | Bezugsrahmen zwingend speichern; fehlend bedeutet unbekannt |
| Panorama-Startausrichtung | Optische Richtung unmittelbar vor Beginn der Aufnahmesequenz und Richtung des ersten tatsächlich aufgenommenen Bilds | Beide beobachten: Automatik kann vor dem ersten Bild drehen |
| Panoramabild-/Viewer-Ausrichtung | Zuordnung von Pixelkoordinate bzw. Viewer-Pan zu geografischem Norden; zusätzlich Standardblick | Nach Stitching anhand eines festen Landmarkenbezugs prüfen |

Für diese Fachdatensätze gilt Azimut im Uhrzeigersinn ab geografisch Nord: 0° Nord, 90° Ost, 180° Süd, 270° West. Eine spätere WPML-Abbildung muss Wertebereich und Vorzeichen ausdrücklich anpassen. Die WPML-`rotateYaw`-Aktion verwendet ±180° und geografisch Norden; Gimbal-Parameter besitzen eigene Bezugsfelder. Das ist kein Nachweis des Consumer-Verhaltens. [DJI WPML Common Elements](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/common-element.html)

Das Modell unterscheidet deshalb `requested_pre_capture_camera_azimuth_deg` und `observed_first_frame_azimuth_deg`. Solange letzteres nicht geprüft ist, heißt der Status `unverified`; ein nachträglich richtig gedrehtes Bild hebt diesen Status für die Aufnahme nicht auf.

## Höhen und wechselnde Abflugorte

WGS84 als horizontales Koordinatensystem sagt nichts über den Höhenbezug aus. Höhen explizit unterscheiden:

- `relative_to_takeoff`: Meter über dem Höhen-Nullpunkt des jeweiligen Starts; zugehörigen Startdatensatz verknüpfen.
- `wgs84_ellipsoid`: absolute ellipsoidische Höhe mit Quelle und Unsicherheit.
- `egm96_orthometric`: eigener Höhenbezug, nicht stillschweigend WGS84 nennen.
- `agl`: tatsächlicher Abstand zum örtlichen Gelände; Geländequelle, Zeitpunkt und Unsicherheit erforderlich. Eine geplante AGL-Höhe ist keine Messung des tatsächlichen Abstands.

Die WPML-Vorlage unterscheidet EGM96, relativ zum Start und geländebezogene Planung. Die Ausführungshöhe besitzt wiederum einen expliziten Bezugsmodus. Keine dieser Enterprise-Funktionen wird damit den Consumer-Modellen zugesagt. [DJI Template KML](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/template-kml.html), [DJI Waylines WPML](https://developer.dji.com/doc/cloud-api-tutorial/en/api-reference/dji-wpml/waylines-wpml.html)

Das Mavic-3-Handbuch beschreibt Waypoint-Höhen relativ zum Abflug und empfiehlt bei Wiederholungen dieselbe Abflughöhe. [DJI Mavic 3 Handbuch v2.2](https://dl.djicdn.com/downloads/DJI_Mavic_3/DJI_Mavic_3_User_Manual_v2.2_en.pdf)

Bei Wechsel des Abflugorts kann dieselbe relative Höhe den Aufnahmeort vertikal verschieben. Fachliche Umrechnung nur bei gemeinsamem, ausreichend genauem Höhenbezug: `neue_relative_Höhe = Zielhöhe_absolut − neue_Starthöhe_absolut`. Beispiel rein synthetisch: Ziel 150 m, Start A 100 m → 50 m relativ; Start B 110 m → 40 m relativ. Ohne belastbare Höhenmessung keine automatische Korrektur. GNSS-/Barometerfehler bleiben auch nach rechnerischer Umrechnung bestehen.

Baufortschritt kann das Gelände verändern: gleiche absolute Kameraposition und gleiche AGL-Höhe sind dann unterschiedliche Ziele. Für Zeitvergleich zunächst dieselbe räumliche Kameraposition bevorzugen; Hindernisse und aktuelle Umgebung können einen neuen Punkt oder eine neue Revision erzwingen. Home Point/RTH-Ziel und Start-Höhenreferenz separat behandeln; eine Home-Point-Aktualisierung darf nicht als nachgewiesene Neuinitialisierung des Höhen-Nullpunkts gelten.

## Arbeitsablauf

1. **Punkt anlegen:** stabile ID, Standort, Höhenbezug, gewünschte Kamera, Panorama-Typ, Norden als Startvorgabe, Landmarke und Qualitätsziele erfassen. Keine Genauigkeit behaupten, die nicht gemessen wurde.
2. **Kartenentwurf abstimmen:** Kunden sehen Punkt-ID, Zweck, Blick-/Abdeckungsinformation, geplante Höhe samt Bezug und Status. Änderungswünsche an einer konkreten Revision sammeln; Kundenfreigabe des Inhalts und operative Freigabe durch den Piloten getrennt halten.
3. **Termin planen:** kompatible Route in Litchi Hub/Map Creator vorbereiten. Startort, aktuellen Baustellenzustand, An-/Abflug und Rückkehr prüfen. Kein generierter Panorama-Actuator wird vorausgesetzt.
4. **Vor Ort:** tatsächlich verwendete Drohne, Controller, Firmware und DJI-Fly-Version erfassen. Gespeicherte Route und Höhenbezug prüfen. Punkt anfliegen, stabilisieren, Kamerablick nach Norden prüfen.
5. **Aufnahme:** bis zum erfolgreichen Gerätestest als betreuter Ablauf behandeln: Anfahrt und Panorama-Auslösung getrennt; nur einen vor Ort bestätigten Moduswechsel verwenden. Falls Waypoint-Modus kein Panorama zulässt, erst sicher pausieren/beenden und Position sowie Heading erneut kontrollieren. Keine unbeaufsichtigte automatische Sequenz zusagen.
6. **Material zuordnen:** Rohbilder, DJI-Ergebnis, Aufnahmezeit und tatsächlichen Punktbesuch verknüpfen; unvollständige Sequenzen kennzeichnen. Stitching-Version und Einstellungen protokollieren.
7. **Ausrichten und prüfen:** Landmarke im Stitch identifizieren, Nordbezug korrigieren, Viewer-Standardblick separat setzen; Folgetermine auf dieselbe Referenz ausrichten.
8. **Bereitstellen:** nur ausdrücklich freigegebene Termine und Informationen in das Kundenprojekt übernehmen. Rohdaten, interne Testbelege und genaue Geodaten nicht versehentlich veröffentlichen.

## Pano2VR, 3D und 3DGS

Pano2VR kann den Nordbezug eines Panoramas nachträglich setzen, auch anhand einer Landmarke auf der Karte. Das unterstützt die visuelle Zeitvergleichbarkeit, beweist aber nicht die Flug- oder Erstbildausrichtung. [Pano2VR: Setting Location](https://cdn.ggnome.com/doc/pano2vr/guide/getting-started/project-setup/image-preparation/set-location/)

Die Pano2VR-8-Dokumentation führt Mesh (glTF/GLB), Gaussian Splat und 3D Tiles als Modelltypen auf. Modellposition, Rotation und Maßstab müssen passen. [3D Model Properties](https://cdn.ggnome.com/doc/pano2vr/workspace/properties/3d-model/)

Verknüpfung von Modell und Tourknoten ist vorgesehen. Für dieses Projekt müssen zusätzlich lokale Modellachsen, Metermaßstab, Höhenbezug und Kameraposition je Panorama registriert und geprüft werden. [Pano2VR: Modell mit Tour verbinden](https://ggnome.com/doc/pano2vr/8_0/guide/model/3dmodel-tour/)

Fachliche Schlussfolgerung: Ein festes Panorama liefert eine Rundumsicht, aber allein keine ausreichende räumliche Abdeckung für ein belastbares 3DGS-Modell. Dessen Aufnahme-/Rekonstruktionsprozess bleibt separat. Panoramen und 3DGS teilen stabile Punkt-/Termin-IDs und eine dokumentierte Transformation; Dateiformat, Leistung und Übergänge sind mit der tatsächlich installierten Pano2VR-Version zu testen.

### Ziel: automatische gemeinsame Ausrichtung

Nutzerergänzung vom 07.11.2026: Die Georeferenzierung der verwendeten Gaussian Splats ist im bestehenden Ablauf noch nicht gelöst. Die konkrete Integration soll gemeinsam mit Thomas Rauscher von Panotoury geklärt werden. Das ist eine offene Projektanforderung, keine Aussage über generell fehlende Georeferenzierungsverfahren oder bereits zugesagte Produktfunktionen.

Ziel ist, Panorama-GPS und Splat-Georeferenz zusammenzuführen und Panoramen anschließend automatisch im Modell zu platzieren und auszurichten. Eine einmal ermittelte Modellregistrierung soll für alle passenden Panoramen und Folgetermine wiederverwendbar sein. Manuelle Einzelkorrekturen bleiben ein nachvollziehbarer Ausnahmefall.

Dafür sind zwei Schritte nötig: (1) Die Panorama-Kameraposition einschließlich Höhe in das lokale Splat-Koordinatensystem umrechnen; (2) den geografischen Nordbezug des fertigen Panoramabilds in die Modellorientierung umrechnen. Eine einzelne GPS-Position legt weder Modellrotation noch Maßstab oder Kamerablickrichtung fest. Erforderlich sind daher eine dokumentierte Transformation mit Achsen, Maßstab und Höhenbezug sowie ein verifizierter Nordbezug nach dem Stitching. Der Nordstart der Aufnahme unterstützt dies, ersetzt den Bild-Nordbezug aber nicht.

Mit Thomas zu klären: Welches Georeferenz-/Transformationsformat lässt sich austauschen? Wie werden Kameraposition und Panorama-Nordoffset übernommen? Können diese Daten gesammelt importiert werden? Wie werden Modellrevisionen und manuelle Korrekturen erhalten? Bis das geklärt und getestet ist, bleibt dies das gewünschte Zielverhalten.

## Read-only-Befund Map Creator

Am 07.11.2026 wurden sechs KMZ im lokalen Missionsordner ausschließlich strukturell gelesen. Keine Kundennamen oder Koordinaten werden hier übernommen. Beobachtet: `executeHeightMode=relativeToStartPoint`; Heading-Modi `followWayline` und `towardPOI`; Aktionen `gimbalEvenlyRotate`, `gimbalRotate`, `takePhoto`; `gimbalHeadingYawBase=aircraft`, `gimbalRotateMode=absoluteAngle`. Keine XML-Tag-Namen mit „pano“. Das beweist weder Panorama-Unterstützung noch deren Ausschluss in anderen Dateien oder Parametern. Die Abweichung `aircraft` gegenüber der öffentlichen Cloud-Referenz verhindert blindes Übertragen ihrer Gimbal-Semantik.

Weitere Dateien: [Datenmodell](data-model.md), [Bedien- und Kompatibilitätstests](test-plan.md), [synthetisches Beispiel](examples/synthetic-point.json).
