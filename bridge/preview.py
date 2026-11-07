"""Title preview rendered with Qt. No network or map-provider dependency."""
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QFontMetrics
from core import BridgeError

def render_preview(destination,name,details,background=None):
    image=QImage(900,600,QImage.Format_RGB32);image.fill(QColor('#152e2b'))
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    if background:
        source=QImage(str(background))
        if source.isNull(): painter.end();raise BridgeError('Vorschaubild kann nicht gelesen werden.')
        source=source.scaled(900,600,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
        painter.drawImage((900-source.width())//2,(600-source.height())//2,source)
    else:
        points=details['points'];lats=[p['lat'] for p in points];lngs=[p['lng'] for p in points]
        lo,hi=min(lats),max(lats);left,right=min(lngs),max(lngs)
        span=max(hi-lo,right-left,0.00001)
        from PySide6.QtGui import QPen,QPainterPath
        painter.setPen(QPen(QColor('#b5d969'),4));path=QPainterPath()
        starts={s['start'] for s in details['segments']}
        for i,p in enumerate(points):
            x=450+(p['lng']-(left+right)/2)/span*520;y=210-(p['lat']-(lo+hi)/2)/span*320
            if i in starts:path.moveTo(x,y)
            else:path.lineTo(x,y)
        painter.drawPath(path)
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
