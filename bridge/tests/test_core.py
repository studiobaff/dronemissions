import io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import inspect_kmz,BridgeError,plan,apply,digest,BASE,atomic_json,sanitize_kmz,prepare_source
UID='12345678-1234-1234-1234-123456789ABC'
def helix_fixture(last_turn='toPointAndStopWithDiscontinuityCurvature',twin_lat='48.002',twin_index='2',actions=True,twin_turn='toPointAndPassWithContinuityCurvature'):
 """Map-Creator-Muster: letzter Wegpunkt doppelt, Unterschied nur im Abbiegemodus (Durchfahren, dann Stopp)."""
 def mark(i,lat,turn,with_actions):
  group=f'<wpml:actionGroup><wpml:actionGroupId>{i}</wpml:actionGroupId><wpml:actionGroupStartIndex>{i}</wpml:actionGroupStartIndex><wpml:actionGroupEndIndex>{i}</wpml:actionGroupEndIndex><wpml:actionGroupMode>sequence</wpml:actionGroupMode><wpml:action><wpml:actionId>0</wpml:actionId><wpml:actionActuatorFunc>takePhoto</wpml:actionActuatorFunc></wpml:action></wpml:actionGroup>' if with_actions else ''
  return f'<Placemark><Point><coordinates>16.00{i},{lat}</coordinates></Point><wpml:index>{i}</wpml:index><wpml:executeHeight>60</wpml:executeHeight><wpml:waypointSpeed>4</wpml:waypointSpeed><wpml:waypointTurnParam><wpml:waypointTurnMode>{turn}</wpml:waypointTurnMode><wpml:waypointTurnDampingDist>0</wpml:waypointTurnDampingDist></wpml:waypointTurnParam>{group}</Placemark>'
 t='<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><wpml:droneEnumValue>68</wpml:droneEnumValue></Document></kml>'
 marks=mark(0,'48.0','toPointAndPassWithContinuityCurvature',actions)+mark(1,'48.001','toPointAndPassWithContinuityCurvature',actions)+mark(2,'48.002',twin_turn,actions)+mark(twin_index,twin_lat,last_turn,actions)
 w=f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><Folder><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>{marks}</Folder></Document></kml>'
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:z.writestr('wpmz/template.kml',t);z.writestr('wpmz/waylines.wpml',w);z.writestr('wpmz/res/readme.txt','untouched')
 return b.getvalue()
def fixture(lat='48.0',entity=False):
 t='<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><wpml:droneEnumValue>68</wpml:droneEnumValue></Document></kml>'
 w=f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><Folder><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode><Placemark><Point><coordinates>16,{lat}</coordinates></Point><wpml:index>0</wpml:index><wpml:executeHeight>60</wpml:executeHeight><wpml:waypointSpeed>4</wpml:waypointSpeed></Placemark><Placemark><Point><coordinates>16.001,48.001</coordinates></Point><wpml:index>1</wpml:index><wpml:executeHeight>65</wpml:executeHeight><wpml:waypointSpeed>4</wpml:waypointSpeed></Placemark></Folder></Document></kml>'
 if entity:t='<!DOCTYPE x [<!ENTITY a "x">]>'+t
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:z.writestr('wpmz/template.kml',t);z.writestr('wpmz/waylines.wpml',w)
 return b.getvalue()
class FakeAdb:
 serial='test-device'
 def __init__(self):self.content={f'{BASE}/{UID}/{UID}.kmz':fixture()};self.fail_stage=False;self.fail_after_commit=False;self.renamed=0
 def exists(self,p):return p in self.content or any(x.startswith(p+'/') for x in self.content)
 def read(self,p):return self.content[p]
 def list_missions(self):return [{'uuid':UID,'path':f'{BASE}/{UID}/{UID}.kmz'}]
 def stop_fly(self):pass
 def mkdir(self,p):pass
 def write(self,p,b):
  if self.fail_stage and '.missionbridge-' in p:raise BridgeError('injected stage failure')
  self.content[p]=b
 def rename(self,a,b):
  self.content[b]=self.content.pop(a);self.renamed+=1
  if self.fail_after_commit and self.renamed==1:self.content[b]=b'corrupted'
 def remove_file(self,p):self.content.pop(p,None)
 def snapshot(self,p):p.mkdir();atomic_json(p/'manifest.json',{'complete':True});return {'complete':True}
class Tests(unittest.TestCase):
 def test_parse_execution_points(self):
  d=inspect_kmz(fixture());self.assertEqual(d['waypoints'],2);self.assertGreater(d['distance'],100);self.assertEqual(d['segments'][0]['heightMode'],'relativeToStartPoint')
 def test_reject_duplicate_indices(self):
  b=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(fixture())) as original,zipfile.ZipFile(b,'w') as out:
   for name in original.namelist():out.writestr(name,original.read(name).replace(b'<wpml:index>1</wpml:index>',b'<wpml:index>0</wpml:index>'))
  with self.assertRaisesRegex(BridgeError,'Wegpunktnummer'):inspect_kmz(b.getvalue())
 def test_reject_entity(self):
  with self.assertRaises(BridgeError):inspect_kmz(fixture(entity=True))
 def test_reject_nan_coordinates(self):
  with self.assertRaises(BridgeError):inspect_kmz(fixture('NaN'))
 def test_reject_non_zip(self):
  with self.assertRaises(BridgeError):inspect_kmz(b'not zip')
 def test_stage_failure_preserves_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture('48.002'));a=FakeAdb();old=dict(a.content);p=plan(a,s,'Test',replace=UID);a.fail_stage=True
   with self.assertRaises(BridgeError):apply(a,p,root/'backup')
   self.assertEqual(a.content,old)
 def test_verify_failure_restores_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture('48.002'));a=FakeAdb();old=dict(a.content);p=plan(a,s,'Test',replace=UID);a.fail_after_commit=True
   with self.assertRaises(BridgeError):apply(a,p,root/'backup')
   self.assertEqual(a.content,old);self.assertEqual(json.loads((root/'backup/transfer.json').read_text())['rollback'],'verified')
 def test_new_transfer_does_not_replace_any_existing(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture('48.002'));a=FakeAdb();old=dict(a.content);p=plan(a,s,'Test');r=apply(a,p,root/'backup');self.assertEqual(r['status'],'files-verified');self.assertEqual(r['flyVisibility'],'not-checked')
   for k,v in old.items():self.assertEqual(a.content[k],v)
   self.assertEqual(digest(a.content[p['remotePath']]),p['sourceSha256'])
 def test_changed_source_is_rejected_before_backup(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture());a=FakeAdb();p=plan(a,s,'Test');s.write_bytes(fixture('48.002'))
   with self.assertRaises(BridgeError):apply(a,p,root/'backup')
   self.assertFalse((root/'backup').exists())
 def test_changed_target_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture('48.002'));a=FakeAdb();p=plan(a,s,'Test',replace=UID);a.content[p['remotePath']]=fixture('48.003')
   with self.assertRaises(BridgeError):apply(a,p,root/'backup')
   self.assertFalse((root/'backup').exists())
 def test_forged_remote_path_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'new.kmz';s.write_bytes(fixture());a=FakeAdb();p=plan(a,s,'Test');p['remotePath']='/sdcard/other'
   with self.assertRaises(BridgeError):apply(a,p,root/'backup')
 def test_sanitize_merges_duplicated_final_waypoint_and_keeps_stop(self):
  raw=helix_fixture()
  with self.assertRaisesRegex(BridgeError,'Wegpunktnummer 2'):inspect_kmz(raw)
  cleaned,report=sanitize_kmz(raw);d=inspect_kmz(cleaned)
  self.assertEqual(d['waypoints'],3);self.assertEqual(report['merged'],[{'index':2,'kept':'toPointAndStopWithDiscontinuityCurvature','dropped':'toPointAndPassWithContinuityCurvature'}]);self.assertEqual(report['sha256'],digest(cleaned))
  with zipfile.ZipFile(io.BytesIO(cleaned)) as z:
   wayline=z.read('wpmz/waylines.wpml').decode();self.assertEqual(z.read('wpmz/res/readme.txt'),b'untouched');self.assertIn('xmlns:wpml="http://www.dji.com/wpmz/1.0.6"',wayline);self.assertNotIn('ns0',wayline)
   self.assertEqual(wayline.count('<Placemark>'),3);self.assertEqual(wayline.count('toPointAndStopWithDiscontinuityCurvature'),1);self.assertEqual(wayline.count('<wpml:actionGroup>'),3);self.assertIn('<wpml:actionGroupStartIndex>2</wpml:actionGroupStartIndex>',wayline)
  self.assertEqual(sanitize_kmz(cleaned),(cleaned,None))
  self.assertEqual(sanitize_kmz(fixture()),(fixture(),None))
 def test_sanitize_keeps_stop_when_order_is_reversed(self):
  cleaned,report=sanitize_kmz(helix_fixture(last_turn='toPointAndPassWithContinuityCurvature',twin_turn='toPointAndStopWithDiscontinuityCurvature'))
  self.assertEqual(report['merged'][0]['kept'],'toPointAndStopWithDiscontinuityCurvature');self.assertEqual(inspect_kmz(cleaned)['waypoints'],3)
 def test_sanitize_rejects_other_duplicates(self):
  for raw in [helix_fixture(twin_lat='48.003'),helix_fixture(twin_index='1'),helix_fixture(last_turn='toPointAndPassWithContinuityCurvature')]:
   self.assertEqual(sanitize_kmz(raw)[1],None,'should not merge')
   with self.assertRaises(BridgeError):inspect_kmz(raw)
  with self.assertRaises(BridgeError):sanitize_kmz(b'not zip')
 def test_prepare_source_keeps_original_and_writes_copy(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'Double Helix.kmz';raw=helix_fixture();src.write_bytes(raw)
   p=prepare_source(src,root/'cleaned');self.assertTrue(p['cleaned']);self.assertEqual(p['original'],src);self.assertEqual(src.read_bytes(),raw);self.assertEqual(p['path'].name,'Double Helix (bereinigt).kmz')
   self.assertEqual(inspect_kmz(p['path'].read_bytes())['waypoints'],3);self.assertEqual(json.loads((root/'cleaned'/'Double Helix (bereinigt).json').read_text())['originalSha256'],digest(raw))
   plain=root/'plain.kmz';plain.write_bytes(fixture());q=prepare_source(plain,root/'cleaned');self.assertFalse(q['cleaned']);self.assertEqual(q['path'],plain)
   bad=root/'bad.kmz';bad.write_bytes(helix_fixture(twin_lat='48.003'))
   with self.assertRaisesRegex(BridgeError,'Wegpunktnummer'):prepare_source(bad,root/'cleaned')
if __name__=='__main__':unittest.main()
