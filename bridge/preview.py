"""Title preview rendered with Qt. No network or map-provider dependency.

Without a background image the route is drawn as an oblique 3D view with the real waypoint heights,
so a helix or hemisphere stays recognizable. Missing heights or mixed vertical references fall back to a
labelled plan view; heights are never inferred. The title band at the bottom is unchanged; DJI Fly shows
this as a fixed picture, it cannot be rotated there.
"""
import math
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QFontMetrics,QPen,QPainterPath,QBrush
from core import BridgeError

W,H=900,600
PLOT=QRectF(60,40,780,350)   # area above the title band
AZIMUTH=math.radians(35)     # rotation around the vertical axis
ELEVATION=math.radians(25)   # camera elevation above the ground plane; exposes the dome's height
KNOWN_REFERENCES={'relativeToStartPoint','WGS84','EGM96'}

def _local_metres(points):
    lat0=(min(p['lat'] for p in points)+max(p['lat'] for p in points))/2
    lng0=(min(p['lng'] for p in points)+max(p['lng'] for p in points))/2
    kx=6371000*math.cos(math.radians(lat0))
    return [(math.radians(p['lng']-lng0)*kx,math.radians(p['lat']-lat0)*6371000) for p in points]

def route_scene(details):
    """Project the route into preview pixels.

    Returns points as (x,y,depth,height) plus the ground footprint, whether the scene is 3D, the height range
    and 'exaggeration' (always 1.0: horizontal distances and heights share one scale, heights are never
    exaggerated). Different vertical references or missing heights cannot be combined into one scene; those
    missions get a plan view.
    """
    points=details['points'];modes={s.get('heightMode','unbekannt') for s in details['segments']}
    use_height=all(isinstance(p.get('height'),(int,float)) and math.isfinite(p['height']) for p in points) and len(modes)==1 and modes<=KNOWN_REFERENCES
    heights=[float(p['height']) for p in points] if use_height else [0.0]*len(points)
    bottom=min(heights);top=max(heights);metres=_local_metres(points)
    spread=max(max(abs(x) for x,_ in metres),max(abs(y) for _,y in metres),1.0)*2
    exaggeration=1.0
    ca,sa=math.cos(AZIMUTH),math.sin(AZIMUTH);ce,se=math.cos(ELEVATION),math.sin(ELEVATION)
    def project(east,north,h):
        if not use_height:return east,-north,0.0
        x=east*ca-north*sa;depth=east*sa+north*ca
        return x,depth*se-(h-bottom)*exaggeration*ce,depth
    route=[project(e,n,h) for (e,n),h in zip(metres,heights)];ground=[project(e,n,bottom) for e,n in metres]
    allpts=route+ground;xs=[p[0] for p in allpts];ys=[p[1] for p in allpts]
    scale=min(PLOT.width()/max(max(xs)-min(xs),1e-6),PLOT.height()/max(max(ys)-min(ys),1e-6))
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    fit=lambda p:(PLOT.center().x()+(p[0]-cx)*scale,PLOT.center().y()+(p[1]-cy)*scale,p[2])
    projected=[(*fit(p),h) for p,h in zip(route,heights)];footprint=[fit(p) for p in ground]
    return {'points':projected,'ground':footprint,'is3d':use_height,'heightMin':bottom,'heightMax':top,'exaggeration':exaggeration,
            'project':lambda e,n,h:fit(project(e,n,h)),'spread':spread}

def draw_route(painter,details):
    scene=route_scene(details);points=scene['points'];starts={s['start'] for s in details['segments']}
    painter.save();painter.setClipRect(QRectF(PLOT.left()-30,PLOT.top()-30,PLOT.width()+60,PLOT.height()+40));painter.setRenderHint(QPainter.Antialiasing)
    if scene['is3d']:
        # Ground plane grid, footprint and drop lines give the eye a floor to measure heights against.
        half=scene['spread']*0.6;step=half/4;painter.setPen(QPen(QColor(255,255,255,22),1))
        for i in range(-4,5):
            a=scene['project'](-half,i*step,scene['heightMin']);b=scene['project'](half,i*step,scene['heightMin']);painter.drawLine(QPointF(a[0],a[1]),QPointF(b[0],b[1]))
            a=scene['project'](i*step,-half,scene['heightMin']);b=scene['project'](i*step,half,scene['heightMin']);painter.drawLine(QPointF(a[0],a[1]),QPointF(b[0],b[1]))
        shadow=QPainterPath()
        for i,g in enumerate(scene['ground']):
            if i in starts:shadow.moveTo(g[0],g[1])
            else:shadow.lineTo(g[0],g[1])
        painter.setPen(QPen(QColor(181,217,105,70),3));painter.drawPath(shadow)
        stride=max(1,len(points)//24);painter.setPen(QPen(QColor(181,217,105,45),1))
        for i in range(0,len(points),stride):painter.drawLine(QPointF(scene['ground'][i][0],scene['ground'][i][1]),QPointF(points[i][0],points[i][1]))
    # One continuous dark outline (no per-segment caps, so the line never looks dashed), then colour by height,
    # distant segments first so near ones remain visible at crossings.
    outline=QPainterPath()
    for i,p in enumerate(points):
        if i in starts:outline.moveTo(p[0],p[1])
        else:outline.lineTo(p[0],p[1])
    painter.setPen(QPen(QColor('#0b2422'),7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPath(outline)
    edges=[(points[i-1],p) for i,p in enumerate(points) if i and i not in starts];edges.sort(key=lambda edge:-(edge[0][2]+edge[1][2]))
    low=scene['heightMin'];span=max(scene['heightMax']-low,1)
    for a,b in edges:
        t=((a[3]+b[3])/2-low)/span
        colour=QColor(round(70+145*t),round(190+34*t),round(196-93*t)) if scene['is3d'] else QColor('#b5d969')
        painter.setPen(QPen(colour,3.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawLine(QPointF(a[0],a[1]),QPointF(b[0],b[1]))
    painter.setPen(QPen(QColor('#20392d'),2));painter.setBrush(QBrush(QColor('#d9ff63')));painter.drawEllipse(QPointF(points[0][0],points[0][1]),7,7)
    painter.setBrush(QBrush(QColor('#ffffff')));painter.drawEllipse(QPointF(points[-1][0],points[-1][1]),5.5,5.5)
    painter.restore()
    painter.setFont(QFont('Helvetica Neue',14));painter.setPen(QColor('#b1c6bc'))
    if scene['is3d']:label=f'3D · Höhe {low:.0f}–{scene["heightMax"]:.0f} m · {len(points)} Wegpunkte'
    else:label='Draufsicht · Höhen fehlen oder Höhenbezüge verschieden'
    painter.drawText(QRectF(115,392,670,25),Qt.AlignRight|Qt.AlignVCenter,label)  # upper left stays free for DJI Fly's cloud icon

def render_preview(destination,name,details,background=None):
    image=QImage(W,H,QImage.Format_RGB32);image.fill(QColor('#152e2b'))
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    if background:
        source=QImage(str(background))
        if source.isNull(): painter.end();raise BridgeError('Vorschaubild kann nicht gelesen werden.')
        source=source.scaled(W,H,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
        painter.drawImage((W-source.width())//2,(H-source.height())//2,source)
    else:
        draw_route(painter,details)
    # Avoid the cloud icon in the upper left and the cropped thumbnail edges.
    painter.fillRect(0,420,W,180,QColor('#122331'))
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
