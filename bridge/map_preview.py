"""Bounded static map viewport and route for the mission title thumbnail.

Kartenquellen (nur ein Ausschnitt von wenigen Kacheln, kein Offline-Download):
- Österreich: basemap.at Orthofoto plus Beschriftungs-Overlay (bmapoverlay), CC BY 4.0.
- Weltweit: Esri World Imagery als Luftbild-Rückfall (Nutzung mit Quellenangabe nach den Esri-Bedingungen);
  fällt auch das aus, OpenStreetMap-Standardkarte (ODbL). Die Quelle steht immer im Bild.
"""
import math,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QPainterPath,QFont
from core import BridgeError
from preview import draw_markers

USER_AGENT='studiobaff-DroneMissionsBridge/0.5 (+https://github.com/studiobaff/dronemissions)'
PROVIDERS={
 'basemap':{'layers':[('https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg','jpg'),('https://mapsneu.wien.gv.at/basemap/bmapoverlay/normal/google3857/{z}/{y}/{x}.png','png')],
             'credit':'Datenquelle: basemap.at · CC BY 4.0','max_zoom':19},
 'esri':{'layers':[('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}','jpg')],
         'credit':'Luftbild: Esri World Imagery · Esri, Maxar, Earthstar Geographics, GIS User Community','max_zoom':18},
 'osm':{'layers':[('https://tile.openstreetmap.org/{z}/{x}/{y}.png','png')],
        'credit':'Karte: © OpenStreetMap-Mitwirkende · ODbL','max_zoom':18},
}
def provider_for(points):
    """basemap.at deckt nur Österreich ab; außerhalb Luftbild weltweit, danach Karte."""
    austrian=all(46.35<=p['lat']<=49.05 and 9.45<=p['lng']<=17.2 for p in points)
    return ['basemap','esri','osm'] if austrian else ['esri','osm']

def world(lat,lng,zoom):
    scale=256*(2**zoom);lat=max(-85.0511,min(85.0511,lat))
    return ((lng+180)/360*scale,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*scale)

def map_background(details,destination,cache,providers=None):
    points=details['points'];latitudes=[p['lat'] for p in points];longitudes=[p['lng'] for p in points]
    if max(longitudes)-min(longitudes)>180:raise BridgeError('Karte über der Datumsgrenze noch nicht unterstützt.')
    errors=[]
    for name in providers or provider_for(points):
        try:return _render(name,points,details,destination,cache)
        except Exception as e:errors.append(f'{name}: {e}')
    raise BridgeError('Keine Kartenquelle erreichbar ('+'; '.join(errors)+'). Route wird ohne Karte dargestellt.')

def _render(name,points,details,destination,cache):
    provider=PROVIDERS[name]
    for zoom in range(provider['max_zoom'],2,-1):
        coords=[world(p['lat'],p['lng'],zoom) for p in points];xs,ys=zip(*coords)
        if max(xs)-min(xs)<=700 and max(ys)-min(ys)<=280:break
    left=(min(xs)+max(xs))/2-450;top=(min(ys)+max(ys))/2-210
    tiles=[(x,y) for x in range(math.floor(left/256),math.ceil((left+900)/256))
                 for y in range(math.floor(top/256),math.ceil((top+420)/256))]
    cache=Path(cache)/name;cache.mkdir(parents=True,exist_ok=True)
    def fetch(item):
        x,y,layer=item;url,ext=provider['layers'][layer];path=cache/f'{zoom}-{x}-{y}-{layer}.{ext}'
        if path.is_file():return x,y,layer,path.read_bytes()
        request=urllib.request.Request(url.format(z=zoom,x=x,y=y),headers={'User-Agent':USER_AGENT})
        with urllib.request.urlopen(request,timeout=6) as response:
            raw=response.read(2*1024*1024)
        image=QImage.fromData(raw)
        if image.isNull():raise BridgeError('Kartenkachel konnte nicht geladen werden.')
        path.write_bytes(raw);return x,y,layer,raw
    # A viewport only, no offline region prefetching. Any missing tile fails over to the next provider.
    jobs=[(x,y,layer) for layer in range(len(provider['layers'])) for x,y in tiles]
    with ThreadPoolExecutor(max_workers=4) as pool:loaded=list(pool.map(fetch,jobs))
    image=QImage(900,600,QImage.Format_RGB32);image.fill(QColor('#e6ebe1'));painter=QPainter(image)
    for x,y,layer,raw in loaded:painter.drawImage(round(x*256-left),round(y*256-top),QImage.fromData(raw))
    painter.setRenderHint(QPainter.Antialiasing);route=QPainterPath();starts={s['start'] for s in details['segments']}
    for i,(x,y) in enumerate(coords):
        if i in starts:route.moveTo(x-left,y-top)
        else:route.lineTo(x-left,y-top)
    painter.setPen(QPen(QColor('#20392d'),8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPath(route)
    painter.setPen(QPen(QColor('#d9ff63'),4,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPath(route)
    draw_markers(painter,[(x-left,y-top) for x,y in coords],starts,dark_background=False)
    painter.fillRect(105,393,690,25,QColor(255,255,255,220));painter.setFont(QFont('Helvetica Neue',10));painter.setPen(QColor('#17372b'))
    painter.drawText(QRectF(105,393,690,25),Qt.AlignCenter,provider['credit'])
    painter.end();destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if not image.save(str(destination),'JPEG',90):raise BridgeError('Kartenansicht konnte nicht gespeichert werden.')
    return destination
