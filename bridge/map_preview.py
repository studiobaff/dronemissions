"""Bounded static map viewport and route for the mission title thumbnail."""
import math,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QPainterPath,QFont
from core import BridgeError

def world(lat,lng,zoom):
    scale=256*(2**zoom);lat=max(-85.0511,min(85.0511,lat))
    return ((lng+180)/360*scale,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*scale)

def map_background(details,destination,cache):
    points=details['points'];latitudes=[p['lat'] for p in points];longitudes=[p['lng'] for p in points]
    if max(longitudes)-min(longitudes)>180:raise BridgeError('Karte über der Datumsgrenze noch nicht unterstützt.')
    austrian=all(46.35<=p['lat']<=49.05 and 9.45<=p['lng']<=17.2 for p in points)
    if not austrian:raise BridgeError('Automatische Kartenansicht derzeit für Österreich verfügbar. Route wird ohne Karte dargestellt.')
    for zoom in range(18,2,-1):
        coords=[world(p['lat'],p['lng'],zoom) for p in points];xs,ys=zip(*coords)
        if max(xs)-min(xs)<=700 and max(ys)-min(ys)<=280:break
    left=(min(xs)+max(xs))/2-450;top=(min(ys)+max(ys))/2-210
    tiles=[(x,y) for x in range(math.floor(left/256),math.ceil((left+900)/256))
                 for y in range(math.floor(top/256),math.ceil((top+420)/256))]
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    def fetch(item):
        x,y=item;path=cache/f'{zoom}-{x}-{y}.jpg'
        if path.is_file():return x,y,path.read_bytes()
        url=f'https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{zoom}/{y}/{x}.jpeg'
        request=urllib.request.Request(url,headers={'User-Agent':'studiobaff-DroneMissionsBridge/0.4'})
        with urllib.request.urlopen(request,timeout=5) as response:
            raw=response.read(2*1024*1024)
        image=QImage.fromData(raw)
        if image.isNull():raise BridgeError('Kartenkachel konnte nicht geladen werden.')
        path.write_bytes(raw);return x,y,raw
    # A viewport only, no offline region prefetching. Any missing tile fails to a schematic.
    with ThreadPoolExecutor(max_workers=4) as pool:loaded=list(pool.map(fetch,tiles))
    image=QImage(900,600,QImage.Format_RGB32);image.fill(QColor('#e6ebe1'));painter=QPainter(image)
    for x,y,raw in loaded:painter.drawImage(round(x*256-left),round(y*256-top),QImage.fromData(raw))
    painter.setRenderHint(QPainter.Antialiasing);route=QPainterPath();starts={s['start'] for s in details['segments']}
    for i,(x,y) in enumerate(coords):
        if i in starts:route.moveTo(x-left,y-top)
        else:route.lineTo(x-left,y-top)
    painter.setPen(QPen(QColor('#20392d'),8));painter.drawPath(route)
    painter.setPen(QPen(QColor('#d9ff63'),4));painter.drawPath(route)
    for i,(x,y) in enumerate(coords):
        if len(coords)>150 and i%3:continue
        painter.setPen(QPen(QColor('#20392d'),1.5));painter.setBrush(QColor('#d9ff63'));painter.drawEllipse(QRectF(x-left-3,y-top-3,6,6))
    painter.fillRect(105,393,690,25,QColor(255,255,255,220));painter.setFont(QFont('Helvetica Neue',10));painter.setPen(QColor('#17372b'))
    painter.drawText(QRectF(105,393,690,25),Qt.AlignCenter,'Datenquelle: basemap.at · CC BY 4.0')
    painter.end();destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if not image.save(str(destination),'JPEG',90):raise BridgeError('Kartenansicht konnte nicht gespeichert werden.')
    return destination
