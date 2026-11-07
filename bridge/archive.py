"""GPL-3.0-or-later. Read-only client for the Drone Missions web archive (api.php).

Logs in with the owner's access key, lists the library and downloads verified KMZ originals.
Only the standard library is used; the access key is kept in memory for the session and never written to disk.
"""
from __future__ import annotations
import http.cookiejar,json,re,urllib.error,urllib.parse,urllib.request,uuid
from pathlib import Path
from core import BridgeError,digest

MAX_KMZ=16*1024*1024
USER_AGENT='studiobaff-DroneMissionsBridge/0.4'

def normalize_url(url:str)->str:
 url=(url or '').strip()
 if not url:raise BridgeError('Bitte die Adresse des Webarchivs eingeben.')
 if not re.match(r'^https?://',url):url='https://'+url
 parts=urllib.parse.urlsplit(url)
 if parts.scheme!='https' and parts.hostname not in ('127.0.0.1','localhost','::1'):raise BridgeError('Das Webarchiv muss über HTTPS erreichbar sein.')
 path=parts.path.rsplit('/',1)[0] if parts.path.endswith(('.php','.html')) else parts.path
 return urllib.parse.urlunsplit((parts.scheme,parts.netloc,path.rstrip('/')+'/','',''))

class ArchiveClient:
 def __init__(self,url:str,timeout=30):
  self.base=normalize_url(url);self.timeout=timeout;self.csrf='';self.role=None;self.folders=[];self.missions=[]
  self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def _request(self,action:str,body=None,raw=False,limit=4*1024*1024,multipart=None):
  url=self.base+'api.php?action='+action;headers={'User-Agent':USER_AGENT,'Accept':'application/json' if not raw else '*/*'};data=None
  if body is not None:data=json.dumps(body).encode();headers.update({'X-CSRF-Token':self.csrf,'Content-Type':'application/json'})
  if multipart is not None:
   fields,files=multipart;boundary='----DroneMissionsBridge'+uuid.uuid4().hex;chunks=[]
   for key,value in fields.items():chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
   for key,(filename,content,mime) in files.items():chunks+=[f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode(),content,b'\r\n']
   data=b''.join(chunks)+f'--{boundary}--\r\n'.encode();headers.update({'X-CSRF-Token':self.csrf,'Content-Type':'multipart/form-data; boundary='+boundary})
  try:
   with self.opener.open(urllib.request.Request(url,data=data,headers=headers),timeout=self.timeout) as response:
    payload=response.read(limit+1);content_type=response.headers.get('Content-Type','')
  except urllib.error.HTTPError as error:
   try:message=json.loads(error.read(65536)).get('error','')
   except Exception:message=''
   raise BridgeError(message or f'Webarchiv antwortet mit HTTP {error.code}.')
  except urllib.error.URLError as error:raise BridgeError('Webarchiv nicht erreichbar: '+str(error.reason))
  if len(payload)>limit:raise BridgeError('Antwort des Webarchivs ist zu groß.')
  if raw:return payload,content_type
  if 'application/json' not in content_type:raise BridgeError('Unerwartete Antwort des Webarchivs. Adresse prüfen.')
  return json.loads(payload)
 def login(self,password:str):
  if not password:raise BridgeError('Bitte den Zugangsschlüssel eingeben.')
  session=self._request('session');self.csrf=session['csrf']
  result=self._request('login',{'password':password});self.csrf=result['csrf'];return result
 def library(self):
  data=self._request('library');self.role=data.get('role');folders={f['id']:f for f in data['folders']}
  def path(folder_id):
   names=[];seen=set();f=folders.get(folder_id)
   while f and f['id'] not in seen:seen.add(f['id']);names.insert(0,f['name']);f=folders.get(f.get('parent'))
   return ' / '.join(names)
  missions=[]
  for m in data['missions']:
   details=m.get('details') or {};fmt={'litchi-csv':'CSV','litchi-lchm':'LCHM','litchi-lchz':'LCHZ','mapcreator-project':'MPROJ'}.get(details.get('sourceFormat'),'KMZ')
   missions.append({'id':m['id'],'revision':int(m.get('revision') or 0),'folderId':m.get('folder'),'name':m['name'],'folder':path(m.get('folder')) or 'Ohne Projekt','archived':bool(m.get('archived')),'format':fmt,'filename':m.get('filename',''),'sha256':m.get('sha256',''),'bytes':int(m.get('bytes') or 0),'versionId':m.get('versionId'),'version':m.get('version'),'updated':m.get('updated',''),'waypoints':details.get('count'),'distance':details.get('distance') or 0,'transferable':fmt=='KMZ'})
  self.folders=[{'id':f['id'],'path':path(f['id']),'archived':bool(f.get('archived'))} for f in data['folders']];self.folders.sort(key=lambda f:f['path'].lower());self.missions=missions
  return missions
 def find_by_sha(self,sha256:str):
  return next((m for m in self.missions if m.get('sha256')==sha256),None)
 def matches_by_sha(self,sha256:str):
  return [m for m in self.missions if sha256 and m.get('sha256')==sha256]
 def move_existing(self,mission,folder):
  """Move one exact loaded revision; never upload a duplicate or overwrite data."""
  if mission.get('folderId')==folder:return mission
  revision=mission.get('revision')
  if not isinstance(revision,int) or revision<1:raise BridgeError('Archiv-Version fehlt. Bitte Bibliothek neu laden, bevor ein Eintrag verschoben wird.')
  self._request('missions-move',{'folder':folder,'missions':[{'id':mission['id'],'revision':revision}]})
  rows=self.library();updated=next((m for m in rows if m['id']==mission['id']),None)
  if not updated or updated.get('folderId')!=folder or updated.get('sha256')!=mission.get('sha256'):
   raise BridgeError('Verschieben wurde angefragt, der aktuelle Stand konnte aber nicht bestätigt werden. Bitte im Webarchiv prüfen; keine neue Datei wurde hochgeladen.')
  return updated
 def upload(self,name:str,filename:str,raw:bytes,folder:str|None=None,preview:bytes|None=None):
  """Upload a KMZ as a new archive mission; the archive verifies the checksum and keeps the original unchanged."""
  if len(raw)>MAX_KMZ:raise BridgeError('KMZ ist größer als 16 MB.')
  fields={'name':name[:200],'folder':folder or ''};files={'kmz':(safe_filename(filename,'Mission.kmz'),raw,'application/vnd.google-earth.kmz')}
  if preview and preview.startswith(b'\xff\xd8') and len(preview)<=3*1024*1024:files['preview']=('preview.jpg',preview,'image/jpeg')
  result=self._request('upload',multipart=(fields,files));self.library();return result
 def preview(self,mission):
  payload,content_type=self._request(f'preview&id={urllib.parse.quote(mission["id"])}&version={urllib.parse.quote(str(mission.get("versionId") or ""))}',raw=True,limit=3*1024*1024)
  return payload,content_type
 def download(self,mission,destination:Path)->Path:
  if not mission.get('transferable'):raise BridgeError('Nur DJI-KMZ-Exporte lassen sich übertragen. Planungsdateien zuerst als KMZ exportieren.')
  payload,_=self._request(f'original&id={urllib.parse.quote(mission["id"])}',raw=True,limit=MAX_KMZ)
  if mission.get('sha256') and digest(payload)!=mission['sha256']:raise BridgeError('Prüfsumme der heruntergeladenen KMZ stimmt nicht mit dem Archiv überein.')
  destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);tmp=destination.with_name(destination.name+'.part')
  tmp.write_bytes(payload)
  if digest(tmp.read_bytes())!=digest(payload):tmp.unlink(missing_ok=True);raise BridgeError('Datei konnte nicht fehlerfrei gespeichert werden.')
  tmp.replace(destination);return destination

def safe_filename(name:str,fallback='Mission')->str:
 cleaned=re.sub(r'[^\w .\-·]+','_',name or '',flags=re.UNICODE).strip(' .')
 return (cleaned or fallback)[:120]
