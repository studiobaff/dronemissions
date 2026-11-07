"""GPL-3.0-or-later. Read-only client for the Drone Missions web archive (api.php).

Logs in with the owner's access key, lists the library and downloads verified KMZ originals.
Only the standard library is used; the access key is kept in memory for the session and never written to disk.
"""
from __future__ import annotations
import http.cookiejar,json,re,urllib.error,urllib.parse,urllib.request
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
  self.base=normalize_url(url);self.timeout=timeout;self.csrf='';self.role=None
  self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def _request(self,action:str,body=None,raw=False,limit=4*1024*1024):
  url=self.base+'api.php?action='+action;headers={'User-Agent':USER_AGENT,'Accept':'application/json' if not raw else '*/*'};data=None
  if body is not None:data=json.dumps(body).encode();headers.update({'X-CSRF-Token':self.csrf,'Content-Type':'application/json'})
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
   missions.append({'id':m['id'],'name':m['name'],'folder':path(m.get('folder')) or 'Ohne Projekt','archived':bool(m.get('archived')),'format':fmt,'filename':m.get('filename',''),'sha256':m.get('sha256',''),'bytes':int(m.get('bytes') or 0),'versionId':m.get('versionId'),'version':m.get('version'),'updated':m.get('updated',''),'waypoints':details.get('count'),'distance':details.get('distance') or 0,'transferable':fmt=='KMZ'})
  return missions
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
