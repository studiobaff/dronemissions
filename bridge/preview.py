"""Title preview rendered with Qt. No network or map-provider dependency."""
from pathlib import Path
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QFontMetrics,QPen
from core import BridgeError

def route_scene(details):
    """Local metres, equal horizontal/vertical scale; never infer missing heights.

    Different vertical reference systems cannot be combined into one 3D scene.
    Such missions, and missions with missing heights, use a labelled plan view.
    """
    points=details['points']
    lat0=(min(p['lat'] for p in points)+max(p['lat'] for p in points))/2
    lng0=(min(p['lng'] for p in points)+max(p['lng'] for p in points))/2
    modes={s.get('heightMode','unbekannt') for s in details['segments']}
    use_height=all(isinstance(p.get('height'),(int,float)) and math.isfinite(p['height']) for p in points) and len(modes)==1 and modes.issubset({'relativeToStartPoint','WGS84','EGM96'})
    heights=[p['height'] for p in points] if use_height else [0.0]*len(points)
    bottom=min(heights);top=max(heights);vertices=[]
    # 25-degree elevation and 35-degree azimuth expose the dome's height.
    azimuth=math.radians(35);elevation=math.radians(25)
    for p,h in zip(points,heights):
        east=math.radians(p['lng']-lng0)*6371000*math.cos(math.radians(lat0))
        north=math.radians(p['lat']-lat0)*6371000
        x=east*math.cos(azimuth)-north*math.sin(azimuth)
        depth=east*math.sin(azimuth)+north*math.cos(azimuth)
        y=depth*math.sin(elevation)-(h-bottom)*math.cos(elevation) if use_height else -north
        vertices.append((x if use_height else east,y,depth,h))
    xs=[p[0] for p in vertices];ys=[p[1] for p in vertices]
    scale=min(660/max(max(xs)-min(xs),1),310/max(max(ys)-min(ys),1))
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    projected=[(450+(x-cx)*scale,215+(y-cy)*scale,depth,h) for x,y,depth,h in vertices]
    return {'points':projected,'is3d':use_height,'heightMin':bottom,'heightMax':top}

def draw_route(painter,details):
    scene=route_scene(details);points=scene['points'];starts={s['start'] for s in details['segments']}
    edges=[(points[i-1],p) for i,p in enumerate(points) if i and i not in starts]
    # Draw distant segments first; near segments remain visible at crossings.
    edges.sort(key=lambda edge:-(edge[0][2]+edge[1][2]))
    painter.save();painter.setClipRect(QRectF(105,42,690,350))
    low=scene['heightMin'];span=max(scene['heightMax']-low,1)
    for a,b in edges:
        t=((a[3]+b[3])/2-low)/span
        color=QColor(round(70+145*t),round(190+34*t),round(196-93*t)) if scene['is3d'] else QColor('#b5d969')
        painter.setPen(QPen(QColor('#0b2422'),7,Qt.SolidLine,Qt.RoundCap));painter.drawLine(QPointF(a[0],a[1]),QPointF(b[0],b[1]))
        painter.setPen(QPen(color,3.8,Qt.SolidLine,Qt.RoundCap));painter.drawLine(QPointF(a[0],a[1]),QPointF(b[0],b[1]))
    painter.restore()
    painter.setFont(QFont('Helvetica Neue',14));painter.setPen(QColor('#b1c6bc'))
    label=f'3D · Höhenunterschied {scene["heightMax"]-low:.0f} m' if scene['is3d'] else 'Draufsicht · Höhen fehlen oder Höhenbezüge verschieden'
    painter.drawText(QRectF(115,385,670,25),Qt.AlignRight|Qt.AlignVCenter,label)

def render_preview(destination,name,details,background=None):
    image=QImage(900,600,QImage.Format_RGB32);image.fill(QColor('#152e2b'))
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    if background:
        source=QImage(str(background))
        if source.isNull(): painter.end();raise BridgeError('Vorschaubild kann nicht gelesen werden.')
        source=source.scaled(900,600,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
        painter.drawImage((900-source.width())//2,(600-source.height())//2,source)
    else:
        draw_route(painter,details)
    # Avoid the cloud icon in the upper left and the cropped thumbnail edges.
    painter.fillRect(0,420,900,180,QColor('#122331'))
    font=QFont('Helvetica Neue',44,QFont.Bold);painter.setFont(font);metrics=QFontMetrics(font)
    width=670;words=name.split();lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if line and metrics.horizontalAdvance(candidate)>width:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    if len(lines)>2:lines=[lines[0],metrics.elidedText(' '.join(lines[1:]),Qt.ElideRight,width)]
    lines=[metrics.elidedText(line,Qt.ElideRight,width) for line in lines]
    painter.setPen(QColor('white'))
    painter.drawText(QRectF(115,432,670,152),Qt.AlignVCenter|Qt.AlignLeft,'\n'.join(lines))
    painter.end();Path(destination).parent.mkdir(parents=True,exist_ok=True)
    if not image.save(str(destination),'JPEG',92):raise BridgeError('Titelvorschau konnte nicht gespeichert werden.')
    return Path(destination)
