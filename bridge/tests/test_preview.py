"""Title preview: projection geometry and offscreen rendering; synthetic data, no mission/device writes."""
import math,os,sys,tempfile,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    from PySide6.QtGui import QGuiApplication,QImage
    from preview import render_preview,route_scene
    HAS_QT=True
except ImportError:
    HAS_QT=False

def details(points,mode='relativeToStartPoint'):
    return {'points':points,'segments':[{'start':0,'count':len(points),'heightMode':mode}]}
def helix(n=117,turns=2,radius=40.0,height=60.0):
    points=[]
    for i in range(n):
        a=i/(n-1)*turns*2*math.pi;r=radius*math.sqrt(max(0.0,1-(i/(n-1))**2))
        points.append({'lat':47.9+r*math.sin(a)/110540,'lng':16.6+r*math.cos(a)/(111320*math.cos(math.radians(47.9))),'height':height*i/(n-1)})
    return {**details(points),'waypoints':n,'distance':1000.0}

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class GeometryTests(unittest.TestCase):
    def test_height_creates_vertical_separation(self):
        scene=route_scene(details([{'lat':48,'lng':16,'height':40},{'lat':48,'lng':16,'height':110}]))
        a,b=scene['points'];self.assertTrue(scene['is3d']);self.assertAlmostEqual(a[0],b[0]);self.assertGreater(a[1]-b[1],300)
    def test_altitude_offset_does_not_distort_shape(self):
        pts=[{'lat':48,'lng':16,'height':10},{'lat':48.001,'lng':16.001,'height':50}]
        shifted=[{**p,'height':p['height']+500} for p in pts]
        self.assertEqual([p[:3] for p in route_scene(details(pts))['points']],[p[:3] for p in route_scene(details(shifted))['points']])
    def test_missing_or_mixed_reference_uses_plan_view(self):
        pts=[{'lat':48,'lng':16,'height':None},{'lat':48.001,'lng':16,'height':50}]
        self.assertFalse(route_scene(details(pts))['is3d'])
        pts[0]['height']=10;d=details(pts);d['segments'].append({'start':1,'count':1,'heightMode':'WGS84'})
        self.assertFalse(route_scene(d)['is3d'])
        self.assertTrue(route_scene(details(pts))['is3d'])
    def test_single_point_is_finite_and_inside_preview(self):
        scene=route_scene(details([{'lat':48,'lng':16,'height':40}]))
        self.assertEqual(scene['points'][0][:2],(450,215))
    def test_helix_fits_the_plot_and_rises_above_its_footprint(self):
        scene=route_scene(helix()['points'] and helix());self.assertEqual(scene['heightMin'],0.0);self.assertAlmostEqual(scene['heightMax'],60.0)
        xs=[p[0] for p in scene['points']+scene['ground']];ys=[p[1] for p in scene['points']+scene['ground']]
        self.assertGreaterEqual(min(xs),59);self.assertLessEqual(max(xs),841);self.assertGreaterEqual(min(ys),39);self.assertLessEqual(max(ys),391)
        self.assertLess(scene['points'][-1][1],scene['ground'][-1][1])  # the top of the helix is drawn above its footprint
        flat=route_scene(details([{**p,'height':30.0} for p in helix()['points']]));self.assertEqual(flat['exaggeration'],1.0);self.assertEqual(flat['heightMin'],flat['heightMax'])
        shallow=route_scene(details([{**p,'height':30.0+i*0.01} for i,p in enumerate(helix()['points'])]));self.assertEqual(shallow['exaggeration'],1.0)  # never exaggerated

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QGuiApplication.instance() or QGuiApplication([])
    def test_render_writes_jpeg_with_title_band(self):
        with tempfile.TemporaryDirectory() as t:
            out=render_preview(Path(t)/'a'/'preview.jpg','Neusiedlersee · Doppelhelix mit sehr langem Titel der umbricht',helix())
            image=QImage(str(out));self.assertEqual((image.width(),image.height()),(900,600));self.assertEqual(out.read_bytes()[:2],b'\xff\xd8')
            self.assertLess(image.pixelColor(450,500).lightness(),80)  # dark title band kept
            self.assertTrue(any(image.pixelColor(x,200).green()>150 for x in range(100,800,5)))  # route visible above the band
            plan=render_preview(Path(t)/'plan.jpg','Draufsicht',details([{'lat':48,'lng':16,'height':None},{'lat':48.001,'lng':16.001,'height':None}]))
            self.assertTrue(plan.is_file())

if __name__=='__main__':unittest.main()
