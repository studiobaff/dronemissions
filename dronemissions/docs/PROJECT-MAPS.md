# Kartenreferenzen je Projekt

Im Projekt **Projektkarte …** öffnen. Unter „Vektor-Ebene hochladen“ ist das aktuelle Projekt vorausgewählt. Eine lokale KMZ/KML, GeoJSON oder ein WGS84-Shapefile-ZIP auswählen und hochladen. Der Browser liest Punkte, Linien und Flächen; der Server validiert das GeoJSON und sichert zusätzlich die unveränderte Originaldatei mit SHA-256 im privaten Blob-Speicher. Es entsteht keine ausführbare DJI-Mission und keine Missionsversion.

Die Referenz wird auf der Projektkarte automatisch eingeblendet und in Unterordnern geerbt. Andere Projekte und „Alle Missionen“ zeigen diese projektbezogene Ebene nicht. Auf Missionskarten zählt der Ordner der Mission. Im Panel „Karte & Zonen“ lässt sie sich vorübergehend ausblenden. Routen und Wegpunkte bleiben über den Referenzebenen. Der Bildausschnitt der Projektkarte berücksichtigt auch die Linie, selbst wenn noch keine Mission vorhanden ist.

In **Einstellungen → Kartenebenen** lässt sich die Projektzuordnung einer vorhandenen Vektor-Ebene ändern und ihr Original herunterladen. Ein Projekt mit Kartenreferenzen kann nicht versehentlich gelöscht werden: Referenzen zuvor anders zuordnen oder entfernen. Hintergrundkarten bleiben global. Die ausdrückliche Auswahl „Global · alle Karten und Freigaben“ behält das bisherige Verhalten für allgemeine Referenzebenen; solche globalen Ebenen sind auch für Kunden sichtbar.

Projektbezogene Vektoren sind für Kundenlinks weder gelistet noch abrufbar. Bearbeitungslinks erhalten nur Referenzen innerhalb ihres freigegebenen Projektbaums; Verwaltung und Originaldownload bleiben beim Eigentümer. Eine außerhalb des freigegebenen Baums liegende Elternreferenz wird nicht zusätzlich offengelegt.

Eine reine Google-My-Maps-NetworkLink-KMZ enthält nur einen Online-Verweis. Die Anwendung lädt ihn nicht automatisch nach. Stattdessen die tatsächlichen Kartendaten als KML/KMZ exportieren. Referenzlinien sind keine DJI-WPML-Missionen und werden nicht an DJI Fly übertragen.

Prüfung: synthetische API-Tests für Zuordnung, Verschieben, Rechte, Originalprüfsumme, getrennte Missionsanzahl und Löschschutz; Browserprüfung für automatische Anzeige, Projektwechsel und vorausgewählten Projektordner.

## Farbe und Linienbreite

Unter **Einstellungen → Kartenebenen → Farbe & Breite** pro Vektor-Ebene wählen: **KMZ/KML-Stil verwenden** erhält unterschiedliche Farben, Transparenz und Breiten der einzelnen Linien. Lokale `StyleMap`-Verweise verwenden den Normalzustand; Highlight-Stile werden nicht dauerhaft angewendet und externe Stiladressen werden nicht geladen. KML-Farben sind AABBGGRR und werden nach RGB plus Transparenz übersetzt.

Für eine einheitliche Darstellung Originalstil ausschalten, Farbe und **0,5–32 Pixel** Breite einstellen und **Stil speichern**. Ein Beispielstrich zeigt die eigene Einstellung. Ohne Originalwerte dienen diese Ebenenwerte als Rückfall. Die Einstellung gilt auf Projekt- und Missionskarten. Sie verändert weder Originaldateien noch Flugmissionen oder die Ebenenreihenfolge. Nur der Eigentümer darf Ebenenstile ändern; Kundenrechte bleiben unverändert.

Bei früher importierten Dateien fehlen die stilbezogenen GeoJSON-Eigenschaften. Ein erneutes Einlesen derselben gesicherten Originaldatei kann sie ergänzen, ohne die Ebenenkennung zu wechseln; eine abweichende Originaldatei wird dafür abgewiesen. Die beiden Pottendorfer Referenzkarten wurden nach dem Update entsprechend ergänzt.
