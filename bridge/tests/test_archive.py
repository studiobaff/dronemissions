"""Archive client against a local fake of api.php; no network, no real archive."""
import hashlib,json,sys,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from archive import ArchiveClient,normalize_url,safe_filename
from core import BridgeError
from test_core import fixture

KMZ=fixture();SHA=hashlib.sha256(KMZ).hexdigest()
LIBRARY={'role':'owner','folders':[{'id':'f1','parent':None,'name':'Demo'},{'id':'f2','parent':'f1','name':'Süd'}],
 'missions':[{'id':'m1','name':'Rundflug','folder':'f2','archived':False,'filename':'a.kmz','sha256':SHA,'bytes':len(KMZ),'versionId':'v1','version':2,'updated':'2026-11-07T10:00:00+00:00','details':{'sourceFormat':'dji-kmz','count':2,'distance':150.0}},
  {'id':'m2','name':'Projekt','folder':None,'archived':True,'filename':'b.mproj','sha256':'x','bytes':10,'versionId':'v2','version':1,'updated':'','details':{'sourceFormat':'mapcreator-project','count':None,'distance':0}}]}

class Handler(BaseHTTPRequestHandler):
 state={'logged':False,'csrf':'token-1','tampered':False}
 def log_message(self,*a):pass
 def send(self,code,body,content_type='application/json'):
  self.send_response(code);self.send_header('Content-Type',content_type);self.send_header('Set-Cookie','dm_session=abc; Path=/');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  action=parse_qs(urlparse(self.path).query).get('action',[''])[0]
  if action=='session':return self.send(200,json.dumps({'authenticated':False,'csrf':self.state['csrf']}).encode())
  if not self.state['logged']:return self.send(401,b'{"error":"Bitte anmelden."}')
  if action=='library':return self.send(200,json.dumps(LIBRARY).encode())
  if action=='preview':return self.send(200,b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>','image/svg+xml')
  if action=='original':return self.send(200,KMZ[:-1]+b'!' if self.state['tampered'] else KMZ,'application/vnd.google-earth.kmz')
  self.send(404,b'{"error":"Nicht gefunden."}')
 def do_POST(self):
  action=parse_qs(urlparse(self.path).query).get('action',[''])[0];self.raw_body=self.rfile.read(int(self.headers.get('Content-Length',0)) or 0);body=json.loads(self.raw_body or b'{}') if self.headers.get('Content-Type','').startswith('application/json') else {}
  if self.headers.get('X-CSRF-Token')!=self.state['csrf']:return self.send(403,b'{"error":"Sitzung abgelaufen."}')
  if action=='upload':
   body=self.rfile.read(0);raw=self.raw_body;assert b'name="kmz"; filename="a.kmz"' in raw and b'name="name"\r\n\r\nRundflug' in raw and b'name="folder"\r\n\r\nf2' in raw and b'name="preview"; filename="preview.jpg"' in raw and KMZ in raw,'multipart body'
   return self.send(200,b'{"id":"m3","version":1}')
  if action=='login':
   if body.get('password')!='richtig':return self.send(401,b'{"error":"Zugangsschl\\u00fcssel nicht korrekt."}')
   self.state['logged']=True;self.state['csrf']='token-2';return self.send(200,json.dumps({'ok':True,'csrf':'token-2'}).encode())
  self.send(404,b'{"error":"Nicht gefunden."}')

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=HTTPServer(('127.0.0.1',0),Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}/dronemissions/'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown()
 def setUp(self):Handler.state.update(logged=False,csrf='token-1',tampered=False)
 def test_normalize_url_requires_https_except_loopback(self):
  self.assertEqual(normalize_url('service.example.com/dronemissions/index.php'),'https://service.example.com/dronemissions/')
  self.assertEqual(normalize_url(self.url),self.url)
  with self.assertRaises(BridgeError):normalize_url('http://service.example.com/dronemissions/')
  with self.assertRaises(BridgeError):normalize_url('')
 def test_safe_filename(self):
  self.assertEqual(safe_filename('Seeufer · Rundflug: Morgen/2026'),'Seeufer · Rundflug_ Morgen_2026');self.assertEqual(safe_filename('   '),'Mission')
 def test_login_errors_are_readable(self):
  c=ArchiveClient(self.url)
  with self.assertRaisesRegex(BridgeError,'nicht korrekt'):c.login('falsch')
  with self.assertRaises(BridgeError):c.login('')
  with self.assertRaisesRegex(BridgeError,'anmelden'):ArchiveClient(self.url).library()
 def test_library_maps_paths_and_formats(self):
  c=ArchiveClient(self.url);c.login('richtig');rows=c.library()
  self.assertEqual(c.role,'owner');self.assertEqual(rows[0]['folder'],'Demo / Süd');self.assertTrue(rows[0]['transferable']);self.assertEqual(rows[0]['waypoints'],2)
  self.assertEqual(rows[1]['folder'],'Ohne Projekt');self.assertEqual(rows[1]['format'],'MPROJ');self.assertFalse(rows[1]['transferable']);self.assertTrue(rows[1]['archived'])
  raw,content_type=c.preview(rows[0]);self.assertIn('svg',content_type);self.assertTrue(raw.startswith(b'<svg'))
 def test_download_verifies_checksum_and_rejects_non_kmz(self):
  c=ArchiveClient(self.url);c.login('richtig');rows=c.library()
  with tempfile.TemporaryDirectory() as t:
   path=c.download(rows[0],Path(t)/'a'/'Rundflug.kmz');self.assertEqual(path.read_bytes(),KMZ)
   with self.assertRaisesRegex(BridgeError,'KMZ'):c.download(rows[1],Path(t)/'b.kmz')
   Handler.state['tampered']=True
   with self.assertRaisesRegex(BridgeError,'Prüfsumme'):c.download(rows[0],Path(t)/'c.kmz')
   self.assertFalse((Path(t)/'c.kmz').exists());self.assertFalse((Path(t)/'c.kmz.part').exists())

class UploadTests(Tests):
 def test_upload_sends_multipart_and_refreshes_library(self):
  c=ArchiveClient(self.url);c.login('richtig');rows=c.library();self.assertEqual([f['path'] for f in c.folders],['Demo','Demo / Süd']);self.assertEqual(c.find_by_sha(SHA)['name'],'Rundflug');self.assertIsNone(c.find_by_sha('x'*64))
  result=c.upload('Rundflug','a.kmz',KMZ,'f2',b'\xff\xd8preview');self.assertEqual(result['id'],'m3')
  with self.assertRaises(BridgeError):c.upload('Groß','b.kmz',b'x'*(16*1024*1024+1))

if __name__=='__main__':unittest.main()

class MoveTests(unittest.TestCase):
 def test_move_uses_revision_and_verifies_same_file_and_id(self):
  from unittest.mock import patch
  c=ArchiveClient('https://archive.test/');old={'id':'a','folderId':'old','sha256':'hash','revision':3};new={**old,'folderId':'new','revision':4}
  with patch.object(c,'_request',return_value={'ok':True}) as request,patch.object(c,'library',return_value=[new]):
   self.assertEqual(c.move_existing(old,'new'),new)
   request.assert_called_once_with('missions-move',{'folder':'new','missions':[{'id':'a','revision':3}]})
 def test_move_rejects_missing_revision_and_changed_file(self):
  from unittest.mock import patch
  c=ArchiveClient('https://archive.test/')
  with patch.object(c,'_request') as request:
   with self.assertRaises(BridgeError):c.move_existing({'id':'a','folderId':'old'},'new')
   request.assert_not_called()
  old={'id':'a','folderId':'old','sha256':'hash','revision':3}
  with patch.object(c,'_request',return_value={'ok':True}),patch.object(c,'library',return_value=[{**old,'folderId':'new','sha256':'different'}]):
   with self.assertRaises(BridgeError):c.move_existing(old,'new')
