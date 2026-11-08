"""GPL-3.0-or-later. USB iPad/iPhone mission import with an offline DB transaction.

DJI Fly must be closed by the user. No root, jailbreak, or developer mode is used.
Only a new mission is supported; existing mission rows are never replaced.
"""
from __future__ import annotations
import asyncio, json, os, re, sqlite3, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from core import BridgeError, atomic_json, digest, inspect_kmz

BUNDLE = 'com.dji.golite'
BASE = '/Documents/wayline_mission'
DB = BASE + '/mission_db/wpmz.sqlite3'
COLUMNS = {'missionId','filePath','name','author','createTime','updateTime',
           'coverImagePath','waypointImageNames','poiImageNames','waypointCount',
           'mileage','waylineLatitude','waylineLongitude','locationDes','duration',
           'allPointLocations','deleteTime','lastSyncTime'}

def run(coroutine):
    # Do not cancel a database rename halfway through a commit.
    return asyncio.run(coroutine)

async def discover():
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    rows=[]
    for d in await list_devices():
        if not d.is_usb: continue
        try:
            async with await create_using_usbmux(serial=d.serial, connection_type='USB',
                                                  autopair=False, pair_timeout=5) as ld:
                name=await ld.get_value(key='DeviceName')
            rows.append({'serial':d.serial,'name':str(name),'kind':'ios','state':'device'})
        except Exception:
            rows.append({'serial':d.serial,'name':'iPad/iPhone – entsperren und Computer vertrauen',
                         'kind':'ios','state':'unpaired'})
    return rows

@asynccontextmanager
async def connect(serial):
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.house_arrest import HouseArrestService
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    async with await create_using_usbmux(serial=serial,connection_type='USB',
                                         autopair=False,pair_timeout=5) as ld:
        async with InstallationProxyService(ld) as proxy:
            apps=await proxy.lookup({'BundleIDs':[BUNDLE],
                'ReturnAttributes':['Container','CFBundleShortVersionString']})
        app=apps.get(BUNDLE)
        if not app: raise BridgeError('DJI Fly ist auf diesem Gerät nicht installiert.')
        container=app.get('Container','')
        if not re.fullmatch(r'/(?:private/)?var/mobile/Containers/Data/Application/[A-Fa-f0-9-]{36}',container):
            raise BridgeError('DJI-Fly-Dokumentenpfad konnte nicht sicher ermittelt werden.')
        async with await HouseArrestService.create(ld,BUNDLE,documents_only=True) as afc:
            yield afc,container,app.get('CFBundleShortVersionString','unbekannt')

async def files(afc,root=BASE):
    result=[]
    async def visit(folder):
        for name in await afc.listdir(folder):
            if name in ('.','..'): continue
            if '/' in name or '\\' in name or ':' in name or '\x00' in name:
                raise BridgeError('Unsicherer Dateiname auf dem Gerät.')
            path=folder+'/'+name
            stat=await afc.stat(path)
            if stat['st_ifmt']=='S_IFDIR': await visit(path)
            elif stat['st_ifmt']=='S_IFREG':
                if int(stat['st_size'])>64*1024*1024:
                    raise BridgeError('Einzelne Missionsdatei größer als 64 MB.')
                result.append(path)
            else: raise BridgeError('Unerwarteter Dateityp im Missionsbestand.')
            if len(result)>10000: raise BridgeError('Zu viele Missionsdateien.')
    await visit(root)
    return sorted(result)

async def database(afc):
    entries=await afc.listdir(BASE+'/mission_db')
    if any(n.endswith(('-wal','-journal')) for n in entries):
        raise BridgeError('DJI-Fly-Datenbank ist noch geöffnet. App vollständig schließen und erneut versuchen.')
    return await afc.get_file_contents(DB)

def validate_db(path):
    with sqlite3.connect(path) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise BridgeError('DJI-Fly-Datenbankprüfung fehlgeschlagen.')
        columns={r[1] for r in c.execute('PRAGMA table_info(kmzTable)')}
        if columns!=COLUMNS:
            raise BridgeError('Diese DJI-Fly-Datenbankversion wird noch nicht unterstützt.')

async def snapshot(afc,destination,serial):
    destination.mkdir(parents=True,exist_ok=False);os.chmod(destination,0o700)
    before=await files(afc);manifest={};total=0
    await database(afc)
    for remote in before:
        raw=await afc.get_file_contents(remote);total+=len(raw)
        if total>512*1024*1024: raise BridgeError('Sicherung größer als 512 MB.')
        local=destination/remote[len(BASE)+1:];local.parent.mkdir(parents=True,exist_ok=True)
        local.write_bytes(raw);os.chmod(local,0o600)
        manifest[remote]={'sha256':digest(raw),'bytes':len(raw)}
    # A complete second pass detects cloud sync or writes during the snapshot.
    if await files(afc)!=before: raise BridgeError('Missionsbestand änderte sich während der Sicherung.')
    for remote in before:
        if digest(await afc.get_file_contents(remote))!=manifest[remote]['sha256']:
            raise BridgeError('Missionsdatei wurde während der Sicherung geändert. DJI Fly schließen.')
    await database(afc)
    result={'complete':True,'device':serial,'files':manifest}
    atomic_json(destination/'manifest.json',result)
    return result

def build_database(original,destination,container,uid,name,details,replace=False):
    """One new row, all existing rows unchanged. Does not touch the device."""
    destination.write_bytes(original);os.chmod(destination,0o600);validate_db(destination)
    with sqlite3.connect(destination) as c:
        author=c.execute("SELECT author FROM kmzTable WHERE deleteTime=-1 AND author NOT IN ('UAV','') ORDER BY updateTime DESC LIMIT 1").fetchone()
        now=time.time();points=details['points']
        row=dict(missionId=uid,filePath=f'{container}{BASE}/{uid}/{uid}.kmz',name=name,
                 author=author[0] if author else 'UAV',createTime=now,updateTime=now,
                 coverImagePath=uid+'.jpg',waypointImageNames=','.join(['']*len(points)),
                 poiImageNames='',waypointCount=len(points),mileage=details['distance'],
                 waylineLatitude=points[0]['lat'],waylineLongitude=points[0]['lng'],
                 locationDes='',duration=details['estimatedSeconds'],
                 allPointLocations=json.dumps([{'latitude':p['lat'],'longitude':p['lng']} for p in points],separators=(',',':')),
                 deleteTime=-1,lastSyncTime=0)
        if replace:
            old=c.execute('SELECT createTime FROM kmzTable WHERE missionId=? AND deleteTime=-1',(uid,)).fetchone()
            if not old: raise BridgeError('Zu ersetzende iPad-Mission fehlt.')
            row['createTime']=old[0]
            c.execute('UPDATE kmzTable SET '+','.join(k+'=?' for k in row if k!='missionId')+' WHERE missionId=?',[v for k,v in row.items() if k!='missionId']+[uid])
        else:c.execute('INSERT INTO kmzTable ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
        c.commit()
    validate_db(destination)
    return destination.read_bytes()

async def list_missions(serial,work):
    work.mkdir(parents=True,exist_ok=True)
    async with connect(serial) as (afc,container,version):
        raw=await database(afc);p=work/('read-'+uuid.uuid4().hex+'.sqlite3')
        p.write_bytes(raw);os.chmod(p,0o600)
        try:
            validate_db(p)
            with sqlite3.connect(p) as c:
                rows=c.execute('SELECT missionId,name,waypointCount,mileage,updateTime FROM kmzTable WHERE deleteTime=-1 ORDER BY updateTime DESC').fetchall()
            found=set(await files(afc))
            result=[];total=0
            for uid,name,count,distance,updated in rows:
                path=f'{BASE}/{uid}/{uid}.kmz';local=path in found
                image=f'{BASE}/map_preview/{uid}/{uid}.jpg';mission={'uuid':uid,'name':name,'waypoints':count,'distance':distance,'updated':updated,'localState':'local' if local else 'cloud-or-missing','preview':image in found}
                if mission['preview']:
                    # DJI Flys Titelbild für die Liste mitlesen; kleine JPEGs, gleiches Gesamtbudget wie die KMZ-Dateien.
                    try:
                        stat=await afc.stat(image);size=int(stat.get('st_size',0))
                        if 0<size<=3*1024*1024 and total+size<=64*1024*1024:
                            raw=await afc.get_file_contents(image);total+=len(raw)
                            if raw.startswith(b'\xff\xd8'):mission['image']=raw
                    except Exception:pass
                if local:
                    try:
                        stat=await afc.stat(path);size=int(stat.get('st_size',0))
                        if size<=16*1024*1024 and total+size<=64*1024*1024:
                            raw=await afc.get_file_contents(path);total+=len(raw)
                            if len(raw)<=16*1024*1024:mission['sha256']=digest(raw)
                    except Exception:pass  # unreadable or budget-exceeding files stay unverified
                result.append(mission)
            return result
        finally: p.unlink(missing_ok=True)

async def read_mission(serial,uid):
    """Read one mission's KMZ and title picture from the device without changing anything."""
    if not re.fullmatch(r'[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}',uid):raise BridgeError('Ungültige Missionskennung.')
    async with connect(serial) as (afc,container,version):
        present=set(await files(afc));kmz=f'{BASE}/{uid}/{uid}.kmz';image=f'{BASE}/map_preview/{uid}/{uid}.jpg'
        return {'kmz':await afc.get_file_contents(kmz) if kmz in present else None,'preview':await afc.get_file_contents(image) if image in present else None}

def rename_database(original,destination,uid,name):
    """Set the display name of one existing row; everything else unchanged. Does not touch the device."""
    destination.write_bytes(original);os.chmod(destination,0o600);validate_db(destination)
    with sqlite3.connect(destination) as c:
        if not c.execute('SELECT 1 FROM kmzTable WHERE missionId=? AND deleteTime=-1',(uid,)).fetchone():raise BridgeError('Mission auf dem iPad nicht gefunden.')
        c.execute('UPDATE kmzTable SET name=?,updateTime=? WHERE missionId=? AND deleteTime=-1',(name,time.time(),uid));c.commit()
    validate_db(destination);return destination.read_bytes()

async def rename_mission(serial,uid,name,work,*,fly_closed):
    """Rename a mission in DJI Fly's database with the same stage, verify and rollback discipline as apply_new."""
    if not fly_closed: raise BridgeError('DJI Fly auf dem iPad/iPhone zuerst vollständig schließen.')
    if not re.fullmatch(r'[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}',uid):raise BridgeError('Ungültige Missionskennung.')
    name=name.strip()
    if not name or len(name)>200 or any(ord(ch)<32 for ch in name):raise BridgeError('Ungültiger Missionsname.')
    work.mkdir(parents=True,exist_ok=False);os.chmod(work,0o700)
    journal={'uuid':uid,'name':name,'device':serial,'mode':'rename','status':'backing-up'};atomic_json(work/'transfer.json',journal)
    async with connect(serial) as (afc,container,version):
        await snapshot(afc,work/'before',serial);original=(work/'before/mission_db/wpmz.sqlite3').read_bytes()
        updated=rename_database(original,work/'new.sqlite3',uid,name);temp=DB+'.missionbridge-'+uuid.uuid4().hex;attempted=False
        try:
            await afc.set_file_contents(temp,updated)
            if await afc.get_file_contents(temp)!=updated:raise BridgeError('Datenbank konnte nicht fehlerfrei übertragen werden.')
            if await database(afc)!=original:raise BridgeError('Datenbank wurde inzwischen geändert. Nichts umbenannt.')
            journal['status']='staged-verified';atomic_json(work/'transfer.json',journal)
            attempted=True;await afc.rename(temp,DB)
            if await afc.get_file_contents(DB)!=updated:raise BridgeError('Datenbank nach Übertragung nicht identisch.')
            journal.update(status='db-verified',flyVersion=version);atomic_json(work/'transfer.json',journal);return journal
        except Exception as error:
            journal.update(status='failed',error=str(error))
            if attempted:
                try:
                    current=await database(afc)
                    if current==updated:
                        await afc.set_file_contents(temp,original)
                        if await afc.get_file_contents(temp)!=original:raise BridgeError('Rollback-Staging fehlgeschlagen.')
                        await afc.rename(temp,DB)
                        if await afc.get_file_contents(DB)!=original:raise BridgeError('Rollback-Rückleseprüfung fehlgeschlagen.')
                    elif current!=original:raise BridgeError('Datenbank inzwischen geändert; Sicherung für manuelle Wiederherstellung erhalten.')
                    journal['rollback']='verified'
                except Exception as rollback:journal['rollback']='manual-recovery-required: '+str(rollback)
            atomic_json(work/'transfer.json',journal);raise
        finally:
            try:await afc.rm_single(temp,force=True)
            except Exception:pass

async def backup(serial,destination):
    async with connect(serial) as (afc,container,version):
        return await snapshot(afc,destination,serial)

async def apply_new(serial,source,name,preview,work,*,fly_closed,replace=None):
    if not fly_closed: raise BridgeError('DJI Fly auf dem iPad/iPhone zuerst vollständig schließen.')
    if replace and not re.fullmatch(r'[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}',replace):raise BridgeError('Ungültige Zielkennung.')
    raw=Path(source).read_bytes();details=inspect_kmz(raw);name=name.strip()
    if not name or len(name)>200 or any(ord(ch)<32 for ch in name):raise BridgeError('Ungültiger Missionsname.')
    picture=Path(preview).read_bytes()
    if not picture.startswith(b'\xff\xd8') or len(picture)>8*1024*1024:raise BridgeError('JPEG-Vorschau fehlt oder ist zu groß.')
    work.mkdir(parents=True,exist_ok=False);os.chmod(work,0o700)
    uid=replace or str(uuid.uuid4()).upper();journal={'uuid':uid,'name':name,'device':serial,'mode':'replace' if replace else 'new','status':'backing-up','flyVisibility':'not-checked','waypoints':details['waypoints'],'sourceSha256':digest(raw),'previewSha256':digest(picture)}
    atomic_json(work/'transfer.json',journal)
    async with connect(serial) as (afc,container,version):
        saved=await snapshot(afc,work/'before',serial);original=(work/'before/mission_db/wpmz.sqlite3').read_bytes()
        kmz=f'{BASE}/{uid}/{uid}.kmz';image=f'{BASE}/map_preview/{uid}/{uid}.jpg'
        if replace and kmz not in saved['files']:raise BridgeError('Ersetzen erfordert eine lokal vorhandene KMZ. Cloud-Mission zuerst in DJI Fly herunterladen.')
        if not replace and uid in await afc.listdir(BASE):raise BridgeError('Neue Kennung existiert bereits.')
        updated=build_database(original,work/'new.sqlite3',container,uid,name,details,replace=bool(replace))
        prior={path:(work/'before'/path[len(BASE)+1:]).read_bytes() if path in saved['files'] else None for path in (kmz,image)}
        temp=DB+'.missionbridge-'+uuid.uuid4().hex;staged=[];changed=False;db_attempted=False
        try:
            for path,content in [(kmz,raw),(image,picture)]:
                await afc.makedirs(path.rsplit('/',1)[0]);stage=path+'.missionbridge-'+uuid.uuid4().hex;staged.append((stage,path,content))
                await afc.set_file_contents(stage,content)
                if await afc.get_file_contents(stage)!=content:raise BridgeError('Rückleseprüfung der Missionsdatei fehlgeschlagen.')
            await afc.set_file_contents(temp,updated)
            if await afc.get_file_contents(temp)!=updated:raise BridgeError('Datenbank konnte nicht fehlerfrei übertragen werden.')
            if await database(afc)!=original:raise BridgeError('Datenbank wurde inzwischen geändert. Kein Eintrag ersetzt.')
            journal['status']='staged-verified';atomic_json(work/'transfer.json',journal)
            for stage,path,content in staged:
                changed=True;await afc.rename(stage,path)
                if await afc.get_file_contents(path)!=content:raise BridgeError('Dateiprüfung nach Umbenennen fehlgeschlagen.')
            db_attempted=True;await afc.rename(temp,DB)
            if await afc.get_file_contents(DB)!=updated:raise BridgeError('Datenbank nach Übertragung nicht identisch.')
            journal.update(status='files-and-db-verified',flyVersion=version);atomic_json(work/'transfer.json',journal);return journal
        except Exception as error:
            journal.update(status='failed',error=str(error))
            if changed or db_attempted:
                try:
                    current=await database(afc)
                    if current==updated:
                        await afc.set_file_contents(temp,original)
                        if await afc.get_file_contents(temp)!=original:raise BridgeError('Rollback-Staging fehlgeschlagen.')
                        await afc.rename(temp,DB)
                        if await afc.get_file_contents(DB)!=original:raise BridgeError('Rollback-Rückleseprüfung fehlgeschlagen.')
                    elif current!=original:raise BridgeError('Datenbank inzwischen geändert; Sicherung für manuelle Wiederherstellung erhalten.')
                    for path,content in prior.items():
                        if content is None:await afc.rm_single(path,force=True)
                        else:
                            stage=path+'.restore-'+uuid.uuid4().hex
                            await afc.set_file_contents(stage,content)
                            if await afc.get_file_contents(stage)!=content:raise BridgeError('Datei-Rollback-Staging fehlgeschlagen.')
                            await afc.rename(stage,path)
                            if await afc.get_file_contents(path)!=content:raise BridgeError('Datei-Rollback fehlgeschlagen.')
                    journal['rollback']='verified'
                except Exception as rollback:journal['rollback']='manual-recovery-required: '+str(rollback)
            atomic_json(work/'transfer.json',journal);raise
        finally:
            for path in [temp]+[stage for stage,_,_ in staged]:
                try:await afc.rm_single(path,force=True)
                except Exception:pass
