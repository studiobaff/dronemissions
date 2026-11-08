"""Active WPML POIs, synthetic coordinates; no device or network access."""
import io,os,sys,tempfile,unittest,zipfile
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import inspect_kmz

def fixture(headings):
    marks=''.join(f'<Placemark><Point><coordinates>{16+i*.001},48</coordinates></Point><wpml:index>{i}</wpml:index><wpml:executeHeight>60</wpml:executeHeight><wpml:waypointHeadingParam>{h}</wpml:waypointHeadingParam></Placemark>' for i,h in enumerate(headings))
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('wpmz/template.kml','<kml/>')
        z.writestr('wpmz/waylines.wpml',f'<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Folder><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>{marks}</Folder></kml>')
    return b.getvalue()
def heading(mode='towardPOI',coords='48.002,16.004,5',index='2'):
    return f'<wpml:waypointHeadingMode>{mode}</wpml:waypointHeadingMode><wpml:waypointPoiPoint>{coords}</wpml:waypointPoiPoint><wpml:waypointHeadingPoiIndex>{index}</wpml:waypointHeadingPoiIndex>'

class POITests(unittest.TestCase):
    def test_latitude_order_deduplication_and_active_only(self):
        raw=fixture([heading(),heading(),heading('followWayline','0,0,0'),heading(coords='48.003,16.005,10',index='3')]);original=bytes(raw)
        d=inspect_kmz(raw);self.assertEqual(raw,original);self.assertEqual(len(d['pois']),2)
        p=d['pois'][0];self.assertEqual((p['lat'],p['lng'],p['altitude']),(48.002,16.004,5));self.assertEqual(p['waypoints'],[0,1]);self.assertEqual(p['label'],'POI 3')
    def test_missing_malformed_or_nonfinite_never_invents_poi(self):
        d=inspect_kmz(fixture(['',heading(coords='nan,16,3'),heading(coords='91,16,3'),heading(coords='48,16'),heading('smoothTransition')]))
        self.assertEqual(d['pois'],[]);self.assertEqual(d['waypoints'],5)
    def test_outside_poi_fits_and_render_is_distinct(self):
        from PySide6.QtGui import QGuiApplication,QImage
        from preview import route_scene,render_preview
        app=QGuiApplication.instance() or QGuiApplication([])
        d=inspect_kmz(fixture([heading(coords='48.006,16.008,500'),heading()]));scene=route_scene(d)
        for _,x,y,_ in scene['pois']:
            self.assertTrue(59<=x<=841);self.assertTrue(39<=y<=391)
        with tempfile.TemporaryDirectory() as t:
            out=render_preview(Path(t)/'poi.jpg','POI Test',d);image=QImage(str(out))
            self.assertTrue(any(image.pixelColor(x,y).red()>100 and image.pixelColor(x,y).blue()>130 and image.pixelColor(x,y).green()<140 for x in range(50,850,2) for y in range(30,400,2)))
            self.assertLess(image.pixelColor(450,510).lightness(),100)
    def test_map_contains_poi_without_network(self):
        from PySide6.QtGui import QGuiApplication,QImage,QColor
        from unittest.mock import patch
        import map_preview
        app=QGuiApplication.instance() or QGuiApplication([])
        d=inspect_kmz(fixture([heading(),heading()]))
        tile=QImage(256,256,QImage.Format_RGB32);tile.fill(QColor('#eeeeee'))
        from PySide6.QtCore import QBuffer,QByteArray,QIODevice
        buf=QByteArray();device=QBuffer(buf);device.open(QIODevice.WriteOnly);tile.save(device,'PNG');raw=bytes(buf)
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return raw
        with tempfile.TemporaryDirectory() as t,patch('map_preview.urllib.request.urlopen',return_value=Response()),patch('map_preview.draw_pois',wraps=map_preview.draw_pois) as painter:
            out=map_preview.map_background(d,Path(t)/'map.jpg',Path(t)/'cache',providers=['osm'])
            self.assertTrue(out.is_file());items=painter.call_args.args[1];self.assertEqual(len(items),1);self.assertEqual(items[0][0]['label'],'POI 3');self.assertTrue(0<items[0][1]<900)
