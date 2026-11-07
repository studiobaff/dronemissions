"""Verified ADB mission-file transport. DJI Fly registration is a separate result."""
from __future__ import annotations
import hashlib,io,json,math,os,re,shlex,shutil,subprocess,time,uuid,zipfile
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET

BASE='/sdcard/Android/data/dji.go.v5/files/waypoint'
UUID=re.compile(r'^[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$')
class BridgeError(RuntimeError):pass

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def atomic_json(path:Path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def local_name(tag):return tag.rsplit('}',1)[-1]
def value(root,tag,default=None):
 return next((e.text.strip() for e in root.iter() if local_name(e.tag)==tag and e.text),default)
def number(raw,default=None):
 try:n=float(raw)
 except (TypeError,ValueError):return default
 return n if math.isfinite(n) else default

def inspect_kmz(raw:bytes)->dict:
 if len(raw)>16*1024*1024:raise BridgeError('KMZ ist größer als 16 MB.')
 try:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   infos=z.infolist()
   if len(infos)>1000 or sum(i.file_size for i in infos)>64*1024*1024:raise BridgeError('KMZ-Inhalt ist zu groß.')
   if any('..' in Path(i.filename).parts or i.filename.startswith('/') for i in infos):raise BridgeError('Ungültiger KMZ-Pfad.')
   def xml(name):
    try:b=z.read(name)
    except KeyError:raise BridgeError('DJI-WPML-Datei fehlt: '+name)
    if len(b)>8*1024*1024 or re.search(br'<!\s*(DOCTYPE|ENTITY)',b,re.I):raise BridgeError('Unzulässige XML-Definition.')
    return ET.fromstring(b)
   template=xml('wpmz/template.kml');route=xml('wpmz/waylines.wpml')
   if z.testzip():raise BridgeError('KMZ-Prüfsumme ungültig.')
 except (zipfile.BadZipFile,ET.ParseError,RuntimeError) as e:raise BridgeError('Ungültige KMZ-Datei: '+str(e)) from e
 points=[];segments=[]
 for folder in route.iter():
  if local_name(folder.tag)!='Folder':continue
  start=len(points);seen_indices=set()
  for p in folder:
   if local_name(p.tag)!='Placemark':continue
   index=value(p,'index');coords=value(p,'coordinates')
   if index is None or coords is None:continue
   if not index.isdigit() or int(index) in seen_indices:raise BridgeError('Doppelte oder ungültige Wegpunktnummer '+str(index)+'. Originaldatei vor Übertragung bereinigen.')
   seen_indices.add(int(index))
   c=coords.split(',');lat=number(c[1] if len(c)>1 else None);lng=number(c[0])
   if lat is None or lng is None or abs(lat)>90 or abs(lng)>180:raise BridgeError('Ungültige Wegpunktkoordinaten.')
   points.append({'lat':lat,'lng':lng,'index':index,'height':number(value(p,'executeHeight')),'speed':number(value(p,'waypointSpeed'),number(value(folder,'autoFlightSpeed')))})
  if seen_indices and sorted(seen_indices)!=list(range(len(seen_indices))):raise BridgeError('Wegpunktnummern sind nicht lückenlos ab 0.')
  if len(points)>start:segments.append({'start':start,'count':len(points)-start,'heightMode':value(folder,'executeHeightMode','unbekannt')})
 if not points:raise BridgeError('Keine ausführbaren Wegpunkte gefunden.')
 distance=0.0;seconds=0.0
 for s in segments:
  for i in range(s['start']+1,s['start']+s['count']):
   a,b=points[i-1],points[i];dp=math.radians(b['lat']-a['lat']);dl=math.radians(b['lng']-a['lng']);h=math.sin(dp/2)**2+math.cos(math.radians(a['lat']))*math.cos(math.radians(b['lat']))*math.sin(dl/2)**2;d=6371000*2*math.asin(min(1,math.sqrt(h)));distance+=d
   if b['speed'] and b['speed']>0:seconds+=d/b['speed']
 return {'sha256':digest(raw),'bytes':len(raw),'waypoints':len(points),'points':points,'segments':segments,'distance':round(distance,2),'estimatedSeconds':round(seconds),'droneEnum':value(template,'droneEnumValue'),'droneSubEnum':value(template,'droneSubEnumValue'),'author':value(template,'author',''),'name':value(template,'name','')}

@dataclass
class Adb:
 executable:str
 serial:str
 def command(self,args,*,raw=False,input=None,timeout=45,check=True):
  r=subprocess.run([self.executable,'-s',self.serial]+list(args),input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
  if check and r.returncode:raise BridgeError(r.stderr.decode(errors='replace').strip() or r.stdout.decode(errors='replace').strip() or 'ADB fehlgeschlagen.')
  return r.stdout if raw else r.stdout.decode(errors='replace').strip()
 def shell(self,command,**kw):return self.command(['shell','-T',command],**kw)
 def read(self,path):return self.command(['exec-out','cat '+shlex.quote(path)],raw=True)
 def exists(self,path):return self.shell('if test -e '+shlex.quote(path)+'; then printf yes; fi')=='yes'
 def mkdir(self,path):self.shell('mkdir -p '+shlex.quote(path))
 def write(self,path,raw):
  # shell -T carries binary stdin; unlike adb push this does not attempt unsupported fchown.
  self.shell('cat > '+shlex.quote(path),input=raw,timeout=90)
  self.shell('chmod 0644 '+shlex.quote(path))
  if digest(self.read(path))!=digest(raw):raise BridgeError('Rückleseprüfung fehlgeschlagen: '+path)
 def rename(self,a,b):self.shell('mv -f '+shlex.quote(a)+' '+shlex.quote(b))
 def remove_file(self,path):self.shell('rm -f '+shlex.quote(path))
 def files(self):
  result=self.shell('find '+BASE+' -type f')
  files=result.splitlines() if result else []
  if len(files)>10000:raise BridgeError('Zu viele Missionsdateien; Sicherung abgebrochen.')
  if any(not p.startswith(BASE+'/') or '..' in Path(p).parts or '\x00' in p or '\\' in p or ':' in p for p in files):raise BridgeError('Ungültiger Gerätepfad.')
  return sorted(files)
 def list_missions(self):
  names=self.shell('ls -1 '+BASE).splitlines();out=[]
  for uid in names:
   if not UUID.fullmatch(uid):continue
   files=self.shell('find '+BASE+'/'+uid+' -maxdepth 1 -type f').splitlines()
   candidates=[p for p in files if p.lower().endswith('.kmz')]
   out.append({'uuid':uid,'path':candidates[0] if len(candidates)==1 else None,'localState':'local' if len(candidates)==1 else 'cloud-or-missing' if not candidates else 'ambiguous','preview':self.exists(f'{BASE}/map_preview/{uid}/{uid}.jpg')})
  return out
 def stop_fly(self):
  self.shell('am force-stop dji.go.v5')
  if self.shell('pidof dji.go.v5',check=False):raise BridgeError('DJI Fly läuft noch. Bitte vollständig schließen.')
 def snapshot(self,destination:Path):
  destination.mkdir(parents=True,exist_ok=False);os.chmod(destination,0o700)
  self.stop_fly();before=self.files();manifest={};total=0
  for remote in before:
   raw=self.read(remote);total+=len(raw)
   if total>512*1024*1024:raise BridgeError('Missionssicherung größer als 512 MB.')
   relative=remote[len(BASE)+1:];p=destination/'waypoint'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);os.chmod(p,0o600)
   if digest(self.read(remote))!=digest(raw):raise BridgeError('Datei änderte sich während der Sicherung: '+relative)
   manifest[relative]={'sha256':digest(raw),'bytes':len(raw)}
  if before!=self.files():raise BridgeError('Missionsbestand hat sich während der Sicherung geändert.')
  result={'format':'dronemissions-device-snapshot/1','device':self.serial,'created':datetime.now(timezone.utc).isoformat(),'files':manifest,'complete':True}
  atomic_json(destination/'manifest.json',result);return result

def devices(executable):
 r=subprocess.run([executable,'devices','-l'],capture_output=True,text=True,timeout=20,check=True);out=[]
 for line in r.stdout.splitlines()[1:]:
  f=line.split()
  if len(f)>=2:out.append({'serial':f[0],'state':f[1],'description':' '.join(f[2:])})
 return out

def plan(adb:Adb,source:Path,name:str,preview:Path|None=None,replace:str|None=None,extension='.KMZ'):
 raw=source.read_bytes();details=inspect_kmz(raw);name=name.strip()
 if not name or len(name)>200:raise BridgeError('Missionsname fehlt oder ist zu lang.')
 if replace and not UUID.fullmatch(replace):raise BridgeError('Ungültige Ziel-UUID.')
 uid=replace or str(uuid.uuid4()).upper();folder=f'{BASE}/{uid}'
 if replace:
  found=next((m for m in adb.list_missions() if m['uuid']==uid),None)
  if not found or not found['path']:raise BridgeError('Ersetzen erfordert eine eindeutige lokal vorhandene KMZ.')
  path=found['path']
 else:
  if adb.exists(folder):raise BridgeError('UUID existiert bereits.')
  path=f'{folder}/{uid}{extension}'
 if preview:
  picture=preview.read_bytes()
  if not picture.startswith(b'\xff\xd8') or len(picture)>8*1024*1024:raise BridgeError('Bitte ein JPEG-Vorschaubild bis 8 MB wählen.')
 else:picture=None
 return {'format':'dronemissions-transfer-plan/1','created':datetime.now(timezone.utc).isoformat(),'serial':adb.serial,'mode':'replace' if replace else 'new-experimental','uuid':uid,'remotePath':path,'previewPath':f'{BASE}/map_preview/{uid}/{uid}.jpg','source':str(source.resolve()),'sourceSha256':digest(raw),'expectedTargetSha256':digest(adb.read(path)) if replace else None,'preview':str(preview.resolve()) if preview else None,'previewSha256':digest(picture) if picture else None,'name':name,'nameStatus':'Archivname; DJI-Fly-Anzeigename auf Android noch nicht bestätigt','kmz':details,'status':'prepared'}

def apply(adb:Adb,p:dict,work:Path):
 if p['serial']!=adb.serial:raise BridgeError('Plan gehört zu einem anderen Gerät.')
 uid=p['uuid']
 if not UUID.fullmatch(uid) or p['remotePath'] not in [f'{BASE}/{uid}/{uid}.kmz',f'{BASE}/{uid}/{uid}.KMZ'] or p['previewPath']!=f'{BASE}/map_preview/{uid}/{uid}.jpg':raise BridgeError('Ungültiger Transferplan.')
 raw=Path(p['source']).read_bytes();inspect_kmz(raw)
 if digest(raw)!=p['sourceSha256']:raise BridgeError('Quelldatei wurde seit der Vorbereitung geändert.')
 picture=Path(p['preview']).read_bytes() if p.get('preview') else None
 if picture is not None and digest(picture)!=p['previewSha256']:raise BridgeError('Vorschaubild wurde seit der Vorbereitung geändert.')
 is_new=p['mode']=='new-experimental'
 if not is_new and p['mode']!='replace':raise BridgeError('Unbekannter Übertragungsmodus.')
 if is_new and adb.exists(f'{BASE}/{uid}'):raise BridgeError('Ziel-UUID existiert inzwischen.')
 if not is_new and not adb.exists(p['remotePath']):raise BridgeError('Zu ersetzende Datei fehlt inzwischen.')
 if not is_new and digest(adb.read(p['remotePath']))!=p.get('expectedTargetSha256'):raise BridgeError('Zielmission wurde seit der Vorbereitung geändert.')
 work.mkdir(parents=True,exist_ok=False);os.chmod(work,0o700)
 journal={**p,'status':'backing-up','flyVisibility':'not-checked'};atomic_json(work/'transfer.json',journal)
 adb.snapshot(work/'before')
 old=adb.read(p['remotePath']) if not is_new else None
 if old is not None and digest(old)!=p.get('expectedTargetSha256'):raise BridgeError('Zielmission änderte sich während der Sicherung.')
 old_preview=adb.read(p['previewPath']) if adb.exists(p['previewPath']) else None
 changes=[];staged=[];committed=False
 try:
  adb.stop_fly()
  adb.mkdir(f'{BASE}/{uid}')
  if picture is not None:adb.mkdir(f'{BASE}/map_preview/{uid}')
  # Stage and verify every new file before replacing any original.
  for path,contents in [(p['remotePath'],raw)]+([(p['previewPath'],picture)] if picture is not None else []):
   tmp=path+'.missionbridge-'+uuid.uuid4().hex+'.tmp';staged.append(tmp);adb.write(tmp,contents);changes.append((tmp,path,contents))
  journal['status']='staged-verified';atomic_json(work/'transfer.json',journal)
  adb.stop_fly()
  for tmp,path,contents in changes:
   committed=True;adb.rename(tmp,path)
   if digest(adb.read(path))!=digest(contents):raise BridgeError('Datei nach Umbenennen nicht identisch.')
  journal['status']='files-verified';journal['flyVisibility']='not-checked';atomic_json(work/'transfer.json',journal)
  return journal
 except Exception as exc:
  journal['status']='failed';journal['error']=str(exc)
  if committed:
   try:
    adb.stop_fly()
    for path,contents in [(p['remotePath'],old),(p['previewPath'],old_preview)] if picture is not None else [(p['remotePath'],old)]:
     if contents is None:adb.remove_file(path)
     else:
      tmp=path+'.missionbridge-restore.tmp';adb.write(tmp,contents);adb.rename(tmp,path)
      if digest(adb.read(path))!=digest(contents):raise BridgeError('Wiederherstellung nicht verifiziert.')
    journal['rollback']='verified'
   except Exception as rollback:journal['rollback']='failed: '+str(rollback)
  atomic_json(work/'transfer.json',journal);raise
 finally:
  for tmp in staged:
   try:adb.remove_file(tmp)
   except Exception:pass
