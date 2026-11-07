"""Geometry checks for the static 3D title preview; no mission/device writes."""
import os,sys,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preview import route_scene

def details(points,mode='relativeToStartPoint'):
 return {'points':points,'segments':[{'start':0,'count':len(points),'heightMode':mode}]}
class GeometryTests(unittest.TestCase):
 def test_height_creates_vertical_separation(self):
  scene=route_scene(details([{'lat':48,'lng':16,'height':40},{'lat':48,'lng':16,'height':110}]))
  a,b=scene['points'];self.assertTrue(scene['is3d']);self.assertEqual(a[0],b[0]);self.assertGreater(a[1]-b[1],300)
 def test_altitude_offset_does_not_distort_shape(self):
  pts=[{'lat':48,'lng':16,'height':10},{'lat':48.001,'lng':16.001,'height':50}]
  shifted=[{**p,'height':p['height']+500} for p in pts]
  self.assertEqual([p[:3] for p in route_scene(details(pts))['points']],[p[:3] for p in route_scene(details(shifted))['points']])
 def test_missing_or_mixed_reference_uses_plan_view(self):
  pts=[{'lat':48,'lng':16,'height':None},{'lat':48.001,'lng':16,'height':50}]
  self.assertFalse(route_scene(details(pts))['is3d'])
  pts[0]['height']=10;d=details(pts);d['segments'].append({'start':1,'count':1,'heightMode':'WGS84'})
  self.assertFalse(route_scene(d)['is3d'])
 def test_single_point_is_finite_and_inside_preview(self):
  scene=route_scene(details([{'lat':48,'lng':16,'height':40}]))
  self.assertEqual(scene['points'][0][:2],(450,215))
