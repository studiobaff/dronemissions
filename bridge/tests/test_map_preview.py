"""Kartenvorschau gegen lokale Kachel-Fakes; kein Netz."""
import os,sys,tempfile,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from test_core import fixture
from core import inspect_kmz,BridgeError
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage,QColor
    import map_preview
    HAS_QT=True
except ImportError:HAS_QT=False

def tile_bytes(colour,fmt):
    image=QImage(256,256,QImage.Format_ARGB32);image.fill(QColor(colour))
    from PySide6.QtCore import QBuffer,QIODevice
    buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,fmt);return bytes(buffer.data())

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def fake_urlopen(self,fail_hosts=()):
        urls=[]
        class Response:
            def __init__(self,raw):self.raw=raw
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n=-1):return self.raw
        def urlopen(request,timeout=0):
            url=request.full_url;urls.append(url);self.assertIn('DroneMissionsBridge',request.get_header('User-agent'))
            if any(h in url for h in fail_hosts):raise OSError('unreachable')
            return Response(tile_bytes('#3366cc','PNG') if 'overlay' in url or 'openstreetmap' in url else tile_bytes('#558833','JPEG'))
        return urlopen,urls
    def test_austria_uses_basemap_with_label_overlay(self):
        details=inspect_kmz(fixture());self.assertEqual(map_preview.provider_for(details['points']),['basemap','esri','osm'])
        urlopen,urls=self.fake_urlopen()
        with tempfile.TemporaryDirectory() as t,patch('map_preview.urllib.request.urlopen',urlopen):
            out=map_preview.map_background(details,Path(t)/'map.jpg',Path(t)/'cache');self.assertTrue(out.is_file())
            self.assertTrue(any('bmaporthofoto30cm' in u for u in urls));self.assertTrue(any('bmapoverlay' in u for u in urls));self.assertFalse(any('arcgis' in u for u in urls))
            image=QImage(str(out));self.assertEqual((image.width(),image.height()),(900,600))
            # zweiter Aufruf kommt aus dem Cache
            before=len(urls);map_preview.map_background(details,Path(t)/'map2.jpg',Path(t)/'cache');self.assertEqual(len(urls),before)
    def test_outside_austria_falls_back_to_world_imagery_then_osm(self):
        details=inspect_kmz(fixture())
        for p in details['points']:p['lng']+=10  # Richtung Osten, außerhalb Österreichs
        self.assertEqual(map_preview.provider_for(details['points']),['esri','osm'])
        urlopen,urls=self.fake_urlopen()
        with tempfile.TemporaryDirectory() as t,patch('map_preview.urllib.request.urlopen',urlopen):
            map_preview.map_background(details,Path(t)/'map.jpg',Path(t)/'cache');self.assertTrue(all('arcgisonline' in u for u in urls))
        urlopen,urls=self.fake_urlopen(fail_hosts=('arcgisonline',))
        with tempfile.TemporaryDirectory() as t,patch('map_preview.urllib.request.urlopen',urlopen):
            map_preview.map_background(details,Path(t)/'map.jpg',Path(t)/'cache');self.assertTrue(any('openstreetmap' in u for u in urls))
        urlopen,urls=self.fake_urlopen(fail_hosts=('arcgisonline','openstreetmap'))
        with tempfile.TemporaryDirectory() as t,patch('map_preview.urllib.request.urlopen',urlopen):
            with self.assertRaisesRegex(BridgeError,'Keine Kartenquelle'):map_preview.map_background(details,Path(t)/'map.jpg',Path(t)/'cache')
            self.assertFalse((Path(t)/'map.jpg').exists())

if __name__=='__main__':unittest.main()
