# Drone Missions

Eine private Web-Bibliothek für DJI-WPML-Missionen: Projekte, Originaldateien (KMZ, CSV, LCHM/LCHZ), Versionen, Kartenansicht und widerrufbare Projektfreigaben.

![Drone Missions mit synthetischen Beispieldaten](dronemissions/docs/screenshots/library.png)

Der Web-Quellcode liegt in [`dronemissions/`](dronemissions/README.md). Die Anwendung verwendet PHP 8.3, SQLite und lokal eingebundenes Leaflet; ein Node-Build ist nicht nötig.

- [Funktionen und Grenzen](dronemissions/README.md)
- [Installation und Betrieb](dronemissions/docs/DEPLOYMENT.md)
- [Tests und Prüfbericht](dronemissions/docs/QA.md)
- [Übergabe: Oberfläche, Gestaltung und offene Punkte](dronemissions/docs/HANDOFF.md)

Die USB-/DJI-Fly-Bridge (Desktop-App) wird separat entwickelt und ist noch nicht Teil dieses Repositorys. Es gibt aktuell keine geprüften Bridge-Downloads und keine bestätigte Flugfreigabe. Planungspunkte dienen der Vorbereitung und erzeugen noch keine ausführbaren Panoramaaktionen.

Die Beispiele sind synthetisch. Private Missionen, Zugangsschlüssel, Datenbanken und Serverkonfiguration sind nicht Bestandteil dieses Repositorys.
