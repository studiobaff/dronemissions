#!/usr/bin/env python3
"""Planner archive/export permissions and lifecycle. Synthetic loopback data only."""
import argparse,io,json,zipfile,xml.etree.ElementTree as E
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz

def plan():
 return {'name':'Planner API demo','type':'grid','cameraId':'mavic3','geometry':{'type':'Polygon','coordinates':[[[16,48],[16.001,48],[16.001,48.001],[16,48.001],[16,48]]]},'params':{'height':60,'bottom':15,'top':40,'standoff':10,'frontOverlap':80,'sideOverlap':70,'photoLimit':150,'sectionOverlap':2}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args();assert urlparse(a.base).hostname in ('127.0.0.1','localhost','::1')
 c=Client(a.base);c.call('planner-catalog',expected=401);c.login(json.loads(a.access.read_text()));folder=c.call('folder',{'name':'Planner synthetic'})['id'];other=c.call('folder',{'name':'Planner foreign'})['id']
 raw=synthetic_kmz();# The profile needs a real device ID, synthetic fixture has 99, not a claimed product enum.
 profile=c.call('upload',{'folder':folder,'name':'Synthetic device profile'},files={'kmz':('device.kmz',raw)})['id']
 body={'folder':folder,'profileMission':profile,'plan':plan()};cat=c.call('planner-catalog')['cameras'];assert len(cat)==6 and {v['id'] for v in cat}=={'mini4','mini5','air3','air3s','mavic3','mavic4'}
 imported=c.call('planner-height-import',{'folder':folder},files={'file':('reference.kmz',synthetic_kmz(20))})['heightReference'];assert imported['heightMode']=='relativeToStartPoint' and not imported['enabled'] and len(imported['points'])==5
 archive_ref=c.call('planner-height-import',{'folder':folder,'mission':profile})['heightReference']
 local_ref=c.call('planner-height-import',{'folder':folder},files={'file':('device.kmz',raw)})['heightReference']
 assert archive_ref['points']==local_ref['points'] and archive_ref['sha256']==local_ref['sha256'] and archive_ref['name'].endswith(' · V1') and not archive_ref['enabled'] and archive_ref['datum']==''
 c.call('planner-height-import',{'folder':folder,'mission':'missing'},expected=404)
 imported.update({'datum':'sameStart','enabled':True,'margin':10});body['plan']['heightReference']=imported
 r=c.call('planner-preview',body);assert r['summary']['photos']>0 and len(r['parts'])==1
 saved=c.call('planner-save',body);body.update(saved);assert saved['revision']==1
 assert c.call('planner-catalog')['deviceProfiles']['mavic3']==profile
 # Optional zero-valued fields serialize identically and must not create false ambiguity.
 source=zipfile.ZipFile(io.BytesIO(raw));buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as target:
  for name in source.namelist():
   contents=source.read(name)
   if name.endswith('template.kml') and b'payloadPositionIndex' not in contents:contents=contents.replace(b'</wpml:missionConfig>',b'<wpml:payloadPositionIndex>0</wpml:payloadPositionIndex></wpml:missionConfig>')
   target.writestr(name,contents)
 equivalent=c.call('upload',{'folder':folder,'name':'Equivalent device defaults'},files={'kmz':('equivalent.kmz',buf.getvalue())})['id']
 c.call('planner-save',{'folder':folder,'profileMission':equivalent,'plan':plan()})
 assert c.call('planner-catalog')['deviceProfiles']['mavic3'] in (profile,equivalent)
 auto={'folder':folder,'plan':plan()};auto['plan']['name']='Automatic remembered device';auto.update(c.call('planner-save',auto))
 assert c.call('planner-load&id='+auto['id'])['body']['profileMission'] in (profile,equivalent)
 auto_raw=c.call('planner-export',auto);auto_zip=zipfile.ZipFile(io.BytesIO(auto_raw));assert b'<wpml:droneEnumValue>99</wpml:droneEnumValue>' in auto_zip.read('wpmz/waylines.wpml')
 assert c.call('planner-archive',auto)['ids']
 unknown={'folder':folder,'plan':plan()};unknown['plan']['cameraId']='mavic4';c.call('planner-export',unknown,expected=400)
 assigned=c.call('planner-device-assign',{'cameraId':'mavic4','profileMission':profile});assert assigned['deviceProfiles']['mavic4']==profile
 assert c.call('planner-export',unknown)[:2]==b'PK'
 # Simulate the old production foreign-key schema, then exercise lazy migration.
 import sqlite3
 with sqlite3.connect(a.access.parent/'missions.sqlite') as legacy:
  legacy.execute('DROP TABLE planner_device_profiles')
  legacy.execute('CREATE TABLE planner_device_profiles(camera TEXT PRIMARY KEY,mission TEXT NOT NULL REFERENCES missions(id),updated TEXT NOT NULL)')
  legacy.execute('INSERT INTO planner_device_profiles VALUES(?,?,?)',('mavic4',profile,'2026-01-01'))
  legacy.execute('DELETE FROM planner_device_snapshots')
 assert c.call('planner-catalog')['deviceProfiles']['mavic4']==profile
 with sqlite3.connect(a.access.parent/'missions.sqlite') as migrated:
  assert not migrated.execute('PRAGMA foreign_key_list(planner_device_profiles)').fetchall()
  assert migrated.execute('SELECT count(*) FROM planner_device_snapshots').fetchone()[0]>=2
 c.call('planner-device-assign',{'cameraId':'custom','profileMission':profile},expected=400)
 listed=next(p for p in c.call('library')['plans'] if p['id']==saved['id']);assert listed['folder']==folder and 'body' not in listed
 loaded=c.call('planner-load&id='+saved['id']);assert loaded['body']['heightReference']==imported;assert loaded['body']['profileMission']==profile and loaded['body']['geometry']==body['plan']['geometry']
 single=c.call('planner-export',body);assert single[:2]==b'PK';z=zipfile.ZipFile(io.BytesIO(single));assert {'wpmz/template.kml','wpmz/waylines.wpml'}<=set(z.namelist());xml=E.fromstring(z.read('wpmz/waylines.wpml'));tags=lambda tag:[e for e in xml.iter() if e.tag.rsplit('}',1)[-1]==tag];assert tags('droneEnumValue')[0].text=='99' and len(tags('Placemark'))==r['summary']['photos']
 archived=c.call('planner-archive',body);assert len(archived['ids'])==1 and not archived['existing'];again=c.call('planner-archive',body);assert again['existing'] and again['ids']==archived['ids']
 m=next(m for m in c.call('library')['missions'] if m['id']==archived['ids'][0]);assert m['details']['plannerId']==saved['id'] and m['folder']==folder
 altered=json.loads(json.dumps(body));altered['plan']['params']['height']=75;c.call('planner-archive',altered,expected=409)
 rev=c.call('planner-save',altered);assert rev['revision']==2;c.call('planner-save',altered,expected=409)
 view=c.call('share',{'folder':folder,'role':'view'});v=Client(a.base);v.call('share-login',{'token':view['token']})
 assert v.call('library')['plans']==[]
 for action in ['planner-catalog','planner-list','planner-load&id='+saved['id']]:v.call(action,expected=403)
 v.call('planner-height-import',{'folder':folder},expected=403,files={'file':('reference.kmz',synthetic_kmz(20))});v.call('planner-preview',body,expected=403);v.call('planner-export',body,expected=403);v.call('planner-archive',body,expected=403)
 edit=c.call('share',{'folder':folder,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':edit['token']});assert any(x['id']==saved['id'] for x in e.call('planner-list')['plans']);e.call('planner-load&id='+saved['id']);e.call('planner-preview',body);assert any(p['id']==saved['id'] for p in e.call('library')['plans'])
 outsider=c.call('share',{'folder':other,'role':'edit'});f=Client(a.base);f.call('share-login',{'token':outsider['token']});assert f.call('planner-catalog')['deviceProfiles']=={};assert not f.call('planner-list')['plans'];assert f.call('library')['plans']==[];f.call('planner-load&id='+saved['id'],expected=403);f.call('planner-preview',body,expected=403)
 f.call('planner-height-import',{'folder':folder},expected=403,files={'file':('reference.kmz',synthetic_kmz(20))})
 v.call('planner-height-import',{'folder':folder,'mission':profile},expected=403)
 f.call('planner-height-import',{'folder':other,'mission':profile},expected=403) # permitted destination, forbidden source
 e.call('planner-height-import',{'folder':other,'mission':profile},expected=403) # permitted source, forbidden destination
 assert e.call('planner-height-import',{'folder':folder,'mission':profile})['heightReference']['sha256']==archive_ref['sha256']
 for guest in (e,f,v):guest.call('planner-device-assign',{'cameraId':'mavic4','profileMission':profile},expected=403)
 assert f.call('planner-catalog')['deviceProfiles']=={}
 archive_plan={'folder':folder,'plan':plan()};archive_plan['plan']['heightReference']=archive_ref
 ah=c.call('planner-save',archive_plan);assert c.call('planner-load&id='+ah['id'])['body']['heightReference']==archive_ref
 pm=next(m for m in c.call('library')['missions'] if m['id']==profile)
 c.call('upload',{'mission':profile,'revision':pm['revision']},files={'kmz':('device-v2.kmz',synthetic_kmz(10))})
 newer=c.call('planner-height-import',{'folder':folder,'mission':profile})['heightReference'];assert newer['name'].endswith(' · V2') and newer['sha256']!=archive_ref['sha256']
 assert c.call('planner-load&id='+ah['id'])['body']['heightReference']==archive_ref # imported snapshot stays pinned
 print('PASS: archive height-reference import, source/destination permissions, checksum and saved snapshot')
 forged={'folder':other,'plan':plan(),'profileMission':profile};f.call('planner-export',forged,expected=403)
 c.call('folder-delete',{'id':folder,'name':'Planner synthetic','parent':None},expected=409)
 c.call('planner-osm',{'south':48,'north':49,'west':16,'east':17},expected=400)
 multi={'folder':folder,'profileMission':profile,'plan':plan()};multi['plan']['type']='doubleHelix';multi['plan']['geometry']={'type':'Point','coordinates':[16,48]};multi['plan']['params'].update({'radius':30,'photoLimit':150});r=c.call('planner-preview',multi);assert len(r['parts'])>1
 bundle=c.call('planner-export',multi);z=zipfile.ZipFile(io.BytesIO(bundle));kmzs=[n for n in z.namelist() if n.endswith('.kmz')];assert len(kmzs)==len(r['parts']) and 'planung.dmplan.json' in z.namelist()
 for n in kmzs:
  inner=zipfile.ZipFile(io.BytesIO(z.read(n)));route=E.fromstring(inner.read('wpmz/waylines.wpml'));points=[e for e in route.iter() if e.tag.rsplit('}',1)[-1]=='Placemark'];assert 1<=len(points)<=150
 missing=plan();missing['params']['terrainMode']='follow';c.call('planner-preview',{'folder':folder,'plan':missing},expected=400)
 video={'folder':folder,'profileMission':profile,'plan':plan()};video['plan']['params']['captureMode']='video'
 vr=c.call('planner-preview',video);assert vr['summary']['photos']==0 and len(vr['points'])==2*vr['summary']['rows']
 vs=c.call('planner-save',video);video.update(vs);vl=c.call('planner-load&id='+vs['id']);assert vl['body']['params']['captureMode']=='video'
 exported=c.call('planner-export',video);vz=zipfile.ZipFile(io.BytesIO(exported));vx=E.fromstring(vz.read('wpmz/waylines.wpml'));vf=[e.text for e in vx.iter() if e.tag.rsplit('}',1)[-1]=='actionActuatorFunc'];assert vf.count('startRecord')==vf.count('stopRecord')==1 and 'takePhoto' not in vf
 va=c.call('planner-archive',video);assert len(va['ids'])==1
 vm=next(m for m in c.call('library')['missions'] if m['id']==va['ids'][0]);assert vm['captureType']=='video'
 c.call('mission-map-type',{'id':vm['id'],'revision':vm['revision'],'captureType':'photo'})
 assert next(m for m in c.call('library')['missions'] if m['id']==vm['id'])['captureType']=='photo'
 video['plan']['params']['captureMode']='photo';c.call('planner-archive',video,expected=409)
 # Whole old export deletion: exact snapshot, current revision and scope guards.
 dp={'folder':folder,'profileMission':profile,'plan':plan()};dp['plan']['name']='Synthetic removable export';dp['plan']['params'].update({'flightSplit':'count','flightCount':2,'photoPause':0})
 dp.update(c.call('planner-save',dp));oldrun=c.call('planner-archive',dp);assert len(oldrun['ids'])==2
 dp['plan']['name']='Synthetic current export';dp.update(c.call('planner-save',dp));currentrun=c.call('planner-archive',dp)
 lib=c.call('library');oldrows=[m for m in lib['missions'] if m['id'] in oldrun['ids']]
 delete={'id':dp['id'],'revision':dp['revision'],'exportRevision':1,'missions':[{'id':m['id'],'revision':m['revision']} for m in oldrows]}
 v.call('planner-export-delete',delete,expected=403);f.call('planner-export-delete',delete,expected=403)
 c.call('planner-export-delete',dict(delete,exportRevision=2),expected=409)
 c.call('planner-export-delete',dict(delete,revision=1),expected=409)
 c.call('planner-export-delete',dict(delete,missions=delete['missions'][:1]),expected=409)
 # A dependent plan keeps an independent device snapshot after source deletion.
 dependent={'folder':folder,'profileMission':oldrun['ids'][0],'plan':plan()};dependent.update(c.call('planner-save',dependent))
 c.call('planner-device-assign',{'cameraId':'mavic4','profileMission':oldrun['ids'][0]})
 # A concurrent edit to any member invalidates the complete deletion snapshot.
 c.call('mission-map-type',{'id':oldrows[0]['id'],'revision':oldrows[0]['revision'],'captureType':'video'})
 c.call('planner-export-delete',delete,expected=409)
 oldrows=[m for m in c.call('library')['missions'] if m['id'] in oldrun['ids']];assert len(oldrows)==2
 delete['missions']=[{'id':m['id'],'revision':m['revision']} for m in oldrows]
 token=c.csrf;c.csrf='invalid';c.call('planner-export-delete',delete,expected=403);c.csrf=token
 result=e.call('planner-export-delete',delete);assert result['deleted']==2 and set(result['ids'])==set(oldrun['ids'])
 lib=c.call('library');ids={m['id'] for m in lib['missions']};assert not ids.intersection(oldrun['ids']) and set(currentrun['ids'])<=ids and profile in ids
 assert c.call('planner-load&id='+dp['id'])['revision']==2
 # Both a saved plan and a new mission still export after the profile source is gone.
 assert c.call('planner-export',dependent)[:2]==b'PK'
 assert c.call('planner-catalog')['deviceProfiles']['mavic4']==oldrun['ids'][0]
 assert c.call('planner-export',unknown)[:2]==b'PK'
 f.call('planner-export',dict(unknown,folder=other,profileMission=oldrun['ids'][0]),expected=403)
 assert c.call('planner-save',dependent)['revision']==2
 assert c.call('planner-archive',dp)['ids']==currentrun['ids']
 c.call('planner-export-delete',delete,expected=409)
 print('PASS: atomic old export deletion, current-plan/current-export preservation, device dependencies, CAS, CSRF, scope and replay')
 print('PASS: video draft persistence, endpoint grid export and archive mode conflict')
 print('PASS: planner catalog, preview, draft CAS/reopen, device profile, KMZ/section ZIP, archive idempotency/linkage, customer/foreign-project denial, delete guard and OSM bounds')
if __name__=='__main__':
 main()
 # The existing archive/planner CI entry point also checks versioned KMZ editing.
 import subprocess,sys
 subprocess.run([sys.executable,str(Path(__file__).with_name('kmz-editor-api.py')),*sys.argv[1:]],check=True)
