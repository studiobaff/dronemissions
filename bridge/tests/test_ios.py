import asyncio,json,sqlite3,sys,tempfile,unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ios
from core import BridgeError,inspect_kmz
from test_core import fixture

def database(path):
    with sqlite3.connect(path) as c:
        fields=[]
        for name in sorted(ios.COLUMNS):
            fields.append('"'+name+'" '+('TEXT PRIMARY KEY' if name=='missionId' else 'TEXT'))
        c.execute('CREATE TABLE kmzTable ('+','.join(fields)+')')
        c.execute("INSERT INTO kmzTable(missionId,name,author,deleteTime,updateTime) VALUES('original','Original','test-author',-1,1)")
    return path.read_bytes()

class Afc:
    def __init__(self,db):self.content={ios.DB:db};self.fail_rename=False;self.change_db=False
    async def listdir(self,p):
        return sorted({x[len(p)+1:].split('/')[0] for x in self.content if x.startswith(p+'/')})
    async def stat(self,p):
        return {'st_ifmt':'S_IFREG','st_size':len(self.content[p])} if p in self.content else {'st_ifmt':'S_IFDIR'}
    async def get_file_contents(self,p):return self.content[p]
    async def set_file_contents(self,p,b):self.content[p]=b
    async def makedirs(self,p):pass
    async def rm_single(self,p,force=False):self.content.pop(p,None)
    async def rename(self,a,b):
        self.content[b]=self.content.pop(a)
        if self.fail_rename:self.fail_rename=False;raise OSError('rename result lost')

class Tests(unittest.TestCase):
    def test_new_row_preserves_original(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);original=database(p/'original.db')
            raw=ios.build_database(original,p/'new.db','/var/mobile/Containers/Data/Application/12345678-1234-1234-1234-123456789ABC','new','Test',inspect_kmz(fixture()))
            with sqlite3.connect(p/'new.db') as c:
                self.assertEqual(c.execute('select name from kmzTable where missionId="original"').fetchone()[0],'Original')
                self.assertEqual(c.execute('select waypointCount from kmzTable where missionId="new"').fetchone()[0],'2')
                self.assertEqual(len(json.loads(c.execute('select allPointLocations from kmzTable where missionId="new"').fetchone()[0])),2)
            self.assertNotEqual(original,raw)
    def exercise(self,fail=False):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);original=database(root/'original.db');a=Afc(original);a.fail_rename=fail
            source=root/'test.kmz';source.write_bytes(fixture());preview=root/'test.jpg';preview.write_bytes(b'\xff\xd8fake-jpeg')
            @asynccontextmanager
            async def connect(serial):yield a,'/var/mobile/Containers/Data/Application/12345678-1234-1234-1234-123456789ABC','test'
            with patch.object(ios,'connect',connect):
                if fail:
                    with self.assertRaises(OSError):ios.run(ios.apply_new('test',source,'Test',preview,root/'transfer',fly_closed=True))
                    self.assertEqual(a.content,{ios.DB:original})
                    receipt=json.loads((root/'transfer/transfer.json').read_text());self.assertEqual(receipt['rollback'],'verified')
                else:
                    result=ios.run(ios.apply_new('test',source,'Test',preview,root/'transfer',fly_closed=True))
                    self.assertEqual(result['status'],'files-and-db-verified')
                    self.assertEqual((root/'transfer/before/mission_db/wpmz.sqlite3').read_bytes(),original)
                    self.assertEqual(len(a.content),3)
    def test_transfer_creates_new_only(self):self.exercise()
    def test_ambiguous_rename_failure_restores_database(self):self.exercise(True)
    def rename(self,fail=False):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);original=database(root/'original.db');a=Afc(original);a.fail_rename=fail
            @asynccontextmanager
            async def connect(serial):yield a,'/var/mobile/Containers/Data/Application/12345678-1234-1234-1234-123456789ABC','test'
            with patch.object(ios,'connect',connect):
                uid='12345678-1234-1234-1234-123456789ABC'
                with sqlite3.connect(root/'original.db') as c:c.execute("INSERT INTO kmzTable(missionId,name,author,deleteTime,updateTime) VALUES(?,'Alt','x',-1,2)",(uid,))
                a.content[ios.DB]=original=(root/'original.db').read_bytes()
                if fail:
                    with self.assertRaises(OSError):ios.run(ios.rename_mission('test',uid,'Neu',root/'rename',fly_closed=True))
                    self.assertEqual(a.content,{ios.DB:original});self.assertEqual(json.loads((root/'rename/transfer.json').read_text())['rollback'],'verified')
                else:
                    result=ios.run(ios.rename_mission('test',uid,'Neu',root/'rename',fly_closed=True));self.assertEqual(result['status'],'db-verified')
                    (root/'after.db').write_bytes(a.content[ios.DB])
                    with sqlite3.connect(root/'after.db') as c:
                        self.assertEqual(c.execute('select name from kmzTable where missionId=?',(uid,)).fetchone()[0],'Neu')
                        self.assertEqual(c.execute('select name from kmzTable where missionId="original"').fetchone()[0],'Original')
                    self.assertEqual(len(a.content),1)
                    with self.assertRaises(BridgeError):ios.run(ios.rename_mission('test','00000000-0000-0000-0000-000000000000','X',root/'rename2',fly_closed=True))
    def test_rename_changes_only_the_name(self):self.rename()
    def test_rename_failure_restores_database(self):self.rename(True)
    def test_rename_requires_closed_fly_and_valid_name(self):
        with self.assertRaises(BridgeError):ios.run(ios.rename_mission('test','12345678-1234-1234-1234-123456789ABC','X',None,fly_closed=False))
    def test_live_database_sidecar_rejected(self):
        a=Afc(b'db');a.content[ios.DB+'-wal']=b'active'
        with self.assertRaises(BridgeError):ios.run(ios.database(a))
    def test_closed_confirmation_required(self):
        with self.assertRaises(BridgeError):ios.run(ios.apply_new('test',None,'Test',None,None,fly_closed=False))

if __name__=='__main__':unittest.main()
