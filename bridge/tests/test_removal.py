"""Selected iPad removal: exact scope, immutable archive/originals, CAS and rollback."""
import sys,json,sqlite3,tempfile,unittest,asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ios
from core import BridgeError
from test_ios import Afc,database
UID='12345678-1234-1234-1234-123456789ABC'
UID2='22345678-1234-1234-1234-123456789ABC'

class RemovalTests(unittest.TestCase):
 def prepare(self,root):
  p=root/'source.db';database(p)
  with sqlite3.connect(p) as c:
   c.execute("INSERT INTO kmzTable(missionId,name,deleteTime,updateTime) VALUES(?,'Broken',-1,2)",(UID,))
   c.execute('CREATE TABLE extra(value TEXT)');c.execute("INSERT INTO extra VALUES('keep')")
  return p.read_bytes()
 def test_database_removes_only_selected_and_keeps_other_tables(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);raw=self.prepare(p);updated=ios.removal_database(raw,p/'out.db',[{'uuid':UID,'name':'Broken','updated':'2'}]);self.assertNotEqual(raw,updated)
   with sqlite3.connect(p/'out.db') as c:
    self.assertEqual(c.execute('SELECT name FROM kmzTable').fetchall(),[('Original',)]);self.assertEqual(c.execute('SELECT * FROM extra').fetchall(),[('keep',)])
 def test_stale_missing_duplicate_invalid_and_shared_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);raw=self.prepare(p)
   for targets in [[{'uuid':UID,'name':'wrong'}],[{'uuid':UID,'updated':'3'}],[{'uuid':UID2}],[{'uuid':UID}]*2,[{'uuid':'../unsafe'}],[]]:
    with self.assertRaises(BridgeError):ios.removal_database(raw,p/'out.db',targets)
   with sqlite3.connect(p/'source.db') as c:c.execute('UPDATE kmzTable SET coverImagePath=? WHERE missionId="original"',(UID+'.jpg',))
   with self.assertRaises(BridgeError):ios.removal_database((p/'source.db').read_bytes(),p/'out.db',[{'uuid':UID}])
 def exercise(self,fail=None):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);raw=self.prepare(p);a=Afc(raw);owned=ios.BASE+'/'+UID+'/'+UID+'.kmz';pic=ios.BASE+'/map_preview/'+UID+'/'+UID+'.jpg';other=ios.BASE+'/untouched.bin';a.content.update({owned:b'broken source',pic:b'\xff\xd8pic',other:b'keep'});before=dict(a.content)
   if fail=='rename':a.fail_rename=True
   if fail=='remove':
    original_remove=a.rm_single
    async def remove(path,force=False):
     if path==pic:
      a.content.pop(path,None);raise OSError('delete response lost')
     return await original_remove(path,force)
    a.rm_single=remove
   if fail=='file-change':
    original_set=a.set_file_contents
    async def setter(path,data):
     await original_set(path,data)
     if '.missionbridge-' in path:a.content[other]=b'external change'
    a.set_file_contents=setter
   @asynccontextmanager
   async def connect(serial):yield a,'container','version'
   with patch.object(ios,'connect',connect):
    if fail:
     with self.assertRaises((OSError,BridgeError)):ios.run(ios.remove_missions('demo',[{'uuid':UID,'name':'Broken','updated':'2'}],p/'remove',fly_closed=True))
     if fail=='file-change':self.assertEqual(a.content[ios.DB],raw);self.assertIn(owned,a.content);self.assertEqual(a.content[other],b'external change')
     else:self.assertEqual(a.content,before);self.assertEqual(json.loads((p/'remove/transfer.json').read_text())['rollback'],'verified')
    else:
     result=ios.run(ios.remove_missions('demo',[{'uuid':UID,'name':'Broken','updated':'2'}],p/'remove',fly_closed=True));self.assertEqual(result['removed'],1);self.assertEqual(result['status'],'removed-and-verified');self.assertNotIn(owned,a.content);self.assertNotIn(pic,a.content);self.assertEqual(a.content[other],b'keep');self.assertEqual((p/'remove/before/mission_db/wpmz.sqlite3').read_bytes(),raw)
 def test_full_removal(self):self.exercise()
 def test_ambiguous_db_rename_rolls_back(self):self.exercise('rename')
 def test_partial_delete_rolls_back_all_files_and_database(self):self.exercise('remove')
 def test_changed_file_prevents_database_write(self):self.exercise('file-change')
 def test_requires_closed_fly(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(BridgeError):ios.run(ios.remove_missions('demo',[{'uuid':UID}],Path(d)/'remove',fly_closed=False))
