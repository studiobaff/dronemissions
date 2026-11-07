"""Title preview rendered with Qt. No network or map-provider dependency.

Without a background image the route is drawn as an oblique 3D view with the real waypoint heights,
so a helix or hemisphere stays recognizable. The title band at the bottom is unchanged; DJI Fly shows
this as a fixed picture, it cannot be rotated there.
"""
import math
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QFontMetrics,QPen,QPainterPath,QBrush
from core import BridgeError

W,H=900,600
PLOT=QRectF(60,40,780,350)   # area above the title band
AZIMUTH=math.radians(32)     # rotation around the vertical axis
TILT=math.radians(28)        # camera elevation above the ground plane

def _local_metres(points):
    lat0=sum(p['lat'] for p in points)/len(points);lng0=sum(p['lng'] for p in points)/len(points)
    kx=111320*math.cos(math.radians(lat0));ky=110540
    return [((p['lng']-lng0)*kx,(p['lat']-lat0)*ky,p['height'] if p.get('height') is not None else 0.0) for p in points]

def oblique_view(points):
    """Return projected (x,y) for route and ground footprint plus metadata, in image pixels."""
    xyz=_local_metres(points);zs=[z for _,_,z in xyz];z0=min(zs);z1=max(zs)
    spread=max(max(abs(x) for x,_,_ in xyz),max(abs(y) for _,y,_ in xyz),1.0)*2
    height_span=z1-z0
    # True scale, but lift flat routes a little so the third dimension stays visible.
    exaggeration=1.0 if height_span<=0 else min(3.0,max(1.0,0.22*spread/height_span))
    ca,sa=math.cos(AZIMUTH),math.sin(AZIMUTH);ct,st=math.cos(TILT),math.sin(TILT)
    def project(x,y,z):
        rx=x*ca-y*sa;ry=x*sa+y*ca
        return rx,-(ry*st+(z-z0)*exaggeration*ct)
    route=[project(x,y,z) for x,y,z in xyz];ground=[project(x,y,z0) for x,y,_ in xyz]
    allpts=route+ground;minx=min(p[0] for p in allpts);maxx=max(p[0] for p in allpts);miny=min(p[1] for p in allpts);maxy=max(p[1] for p in allpts)
    scale=min(PLOT.width()/max(maxx-minx,1e-6),PLOT.height()/max(maxy-miny,1e-6))
    ox=PLOT.center().x()-(minx+maxx)/2*scale;oy=PLOT.center().y()-(miny+maxy)/2*scale
    fit=lambda p:QPointF(p[0]*scale+ox,p[1]*scale+oy)
    return {'route':[fit(p) for p in route],'ground':[fit(p) for p in ground],'heights':zs,'z0':z0,'z1':z1,'exaggeration':exaggeration,'project':lambda x,y,z:fit(project(x,y,z)),'scale':scale,'spread':spread}

def draw_route_3d(painter,details):
    view=oblique_view(details['points']);route,ground=view['route'],view['ground'];starts={s['start'] for s in details['segments']}
    painter.setRenderHint(QPainter.Antialiasing)
    # Ground plane grid for depth; sized to the route footprint.
    half=view['spread']*0.6;step=half/4;pen=QPen(QColor(255,255,255,22),1);painter.setPen(pen)
    for i in range(-4,5):
        painter.drawLine(view['project'](-half,i*step,view['z0']),view['project'](half,i*step,view['z0']))
        painter.drawLine(view['project'](i*step,-half,view['z0']),view['project'](i*step,half,view['z0']))
    # Footprint on the ground and vertical drop lines.
    shadow=QPainterPath()
    for i,p in enumerate(ground):
        if i in starts:shadow.moveTo(p)
        else:shadow.lineTo(p)
    painter.setPen(QPen(QColor(181,217,105,70),3));painter.drawPath(shadow)
    stride=max(1,len(route)//24);painter.setPen(QPen(QColor(181,217,105,45),1))
    for i in range(0,len(route),stride):painter.drawLine(ground[i],route[i])
    # The flight path itself, colour graded by height.
    z0,z1=view['z0'],view['z1'];outline=QPainterPath()
    for i,p in enumerate(route):
        if i in starts:outline.moveTo(p)
        else:outline.lineTo(p)
    painter.setPen(QPen(QColor(20,45,40),7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPath(outline)
    for i in range(1,len(route)):
        if i in starts:continue
        t=0.0 if z1<=z0 else ((view['heights'][i]-z0)/(z1-z0))
        painter.setPen(QPen(QColor(int(120+135*t),int(205+40*t),int(90+60*(1-t))),3.5,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawLine(route[i-1],route[i])
    painter.setPen(QPen(QColor('#20392d'),2));painter.setBrush(QBrush(QColor('#d9ff63')));painter.drawEllipse(route[0],7,7)
    painter.setBrush(QBrush(QColor('#ffffff')));painter.drawEllipse(route[-1],5.5,5.5)
    # Height legend, top right (the upper left is covered by DJI Fly's cloud icon).
    painter.setPen(QColor(200,220,190));painter.setFont(QFont('Helvetica Neue',13))
    note=f'Höhe {z0:.0f}–{z1:.0f} m · {len(route)} Wegpunkte · Ansicht schräg'+(f' · Höhe ×{view["exaggeration"]:.1f}' if view['exaggeration']>1.05 else '')
    painter.drawText(QRectF(420,8,470,24),Qt.AlignRight|Qt.AlignVCenter,note)

def render_preview(destination,name,details,background=None):
    image=QImage(W,H,QImage.Format_RGB32);image.fill(QColor('#152e2b'))
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    if background:
        source=QImage(str(background))
        if source.isNull(): painter.end();raise BridgeError('Vorschaubild kann nicht gelesen werden.')
        source=source.scaled(W,H,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
        painter.drawImage((W-source.width())//2,(H-source.height())//2,source)
    else:
        draw_route_3d(painter,details)
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
