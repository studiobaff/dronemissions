"""Title preview rendering; offscreen, synthetic data."""
import math,os,sys,tempfile,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    from PySide6.QtGui import QGuiApplication,QImage
    from preview import render_preview,oblique_view
    HAS_QT=True
except ImportError:
    HAS_QT=False

def helix(n=117,turns=2,radius=40.0,height=60.0):
    points=[]
    for i in range(n):
        a=i/(n-1)*turns*2*math.pi;r=radius*math.sqrt(max(0.0,1-(i/(n-1))**2))
        points.append({'lat':47.9+r*math.sin(a)/110540,'lng':16.6+r*math.cos(a)/(111320*math.cos(math.radians(47.9))),'height':height*i/(n-1)})
    return {'points':points,'segments':[{'start':0,'count':n,'heightMode':'relativeToStartPoint'}],'waypoints':n,'distance':1000.0}

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QGuiApplication.instance() or QGuiApplication([])
    def test_oblique_view_uses_heights_and_fits_the_plot(self):
        view=oblique_view(helix()['points']);self.assertEqual(view['z0'],0.0);self.assertAlmostEqual(view['z1'],60.0)
        xs=[p.x() for p in view['route']+view['ground']];ys=[p.y() for p in view['route']+view['ground']]
        self.assertGreaterEqual(min(xs),59);self.assertLessEqual(max(xs),841);self.assertGreaterEqual(min(ys),39);self.assertLessEqual(max(ys),391)
        self.assertLess(view['route'][-1].y(),view['ground'][-1].y())  # the top of the helix is drawn above its footprint
        flat=oblique_view([{**p,'height':30.0} for p in helix()['points']]);self.assertEqual(flat['exaggeration'],1.0);self.assertEqual(flat['z0'],flat['z1'])
    def test_render_writes_jpeg_with_title_band(self):
        with tempfile.TemporaryDirectory() as t:
            out=render_preview(Path(t)/'a'/'preview.jpg','Neusiedlersee · Doppelhelix mit sehr langem Titel der umbricht',helix())
            image=QImage(str(out));self.assertEqual((image.width(),image.height()),(900,600));self.assertEqual(out.read_bytes()[:2],b'\xff\xd8')
            band=image.pixelColor(450,500);self.assertLess(band.lightness(),80)  # dark title band kept
            self.assertTrue(any(image.pixelColor(x,200).green()>150 for x in range(100,800,5)))  # route visible above the band

if __name__=='__main__':unittest.main()
