import io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import inspect_kmz,BridgeError,plan,apply,digest,BASE,atomic_json
UID='12345678-1234-1234-1234-123456789ABC'
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
if __name__=='__main__':unittest.main()
