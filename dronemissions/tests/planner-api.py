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
 c=Client(a.base);c.call('planner-catalog',expected=401);c.call('login',json.loads(a.access.read_text()));folder=c.call('folder',{'name':'Planner synthetic'})['id'];other=c.call('folder',{'name':'Planner foreign'})['id']
 raw=synthetic_kmz();# The profile needs a real device ID, synthetic fixture has 99, not a claimed product enum.
 profile=c.call('upload',{'folder':folder,'name':'Synthetic device profile'},files={'kmz':('device.kmz',raw)})['id']
 body={'folder':folder,'profileMission':profile,'plan':plan()};cat=c.call('planner-catalog')['cameras'];assert len(cat)==6 and {v['id'] for v in cat}=={'mini4','mini5','air3','air3s','mavic3','mavic4'}
 imported=c.call('planner-height-import',{'folder':folder},files={'file':('reference.kmz',synthetic_kmz(20))})['heightReference'];assert imported['heightMode']=='relativeToStartPoint' and not imported['enabled'] and len(imported['points'])==5
 imported.update({'datum':'sameStart','enabled':True,'margin':10});body['plan']['heightReference']=imported
 r=c.call('planner-preview',body);assert r['summary']['photos']>0 and len(r['parts'])==1
 saved=c.call('planner-save',body);body.update(saved);assert saved['revision']==1
 loaded=c.call('planner-load&id='+saved['id']);assert loaded['body']['heightReference']==imported;assert loaded['body']['profileMission']==profile and loaded['body']['geometry']==body['plan']['geometry']
 single=c.call('planner-export',body);assert single[:2]==b'PK';z=zipfile.ZipFile(io.BytesIO(single));assert {'wpmz/template.kml','wpmz/waylines.wpml'}<=set(z.namelist());xml=E.fromstring(z.read('wpmz/waylines.wpml'));tags=lambda tag:[e for e in xml.iter() if e.tag.rsplit('}',1)[-1]==tag];assert tags('droneEnumValue')[0].text=='99' and len(tags('Placemark'))==r['summary']['photos']
 archived=c.call('planner-archive',body);assert len(archived['ids'])==1 and not archived['existing'];again=c.call('planner-archive',body);assert again['existing'] and again['ids']==archived['ids']
 m=next(m for m in c.call('library')['missions'] if m['id']==archived['ids'][0]);assert m['details']['plannerId']==saved['id'] and m['folder']==folder
 altered=json.loads(json.dumps(body));altered['plan']['params']['height']=75;c.call('planner-archive',altered,expected=409)
 rev=c.call('planner-save',altered);assert rev['revision']==2;c.call('planner-save',altered,expected=409)
 view=c.call('share',{'folder':folder,'role':'view'});v=Client(a.base);v.call('share-login',{'token':view['token']})
 for action in ['planner-catalog','planner-list','planner-load&id='+saved['id']]:v.call(action,expected=403)
 v.call('planner-height-import',{'folder':folder},expected=403,files={'file':('reference.kmz',synthetic_kmz(20))});v.call('planner-preview',body,expected=403);v.call('planner-export',body,expected=403);v.call('planner-archive',body,expected=403)
 edit=c.call('share',{'folder':folder,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':edit['token']});assert any(x['id']==saved['id'] for x in e.call('planner-list')['plans']);e.call('planner-load&id='+saved['id']);e.call('planner-preview',body)
 outsider=c.call('share',{'folder':other,'role':'edit'});f=Client(a.base);f.call('share-login',{'token':outsider['token']});assert not f.call('planner-list')['plans'];f.call('planner-load&id='+saved['id'],expected=403);f.call('planner-preview',body,expected=403)
 f.call('planner-height-import',{'folder':folder},expected=403,files={'file':('reference.kmz',synthetic_kmz(20))})
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
 video['plan']['params']['captureMode']='photo';c.call('planner-archive',video,expected=409)
 print('PASS: video draft persistence, endpoint grid export and archive mode conflict')
 print('PASS: planner catalog, preview, draft CAS/reopen, device profile, KMZ/section ZIP, archive idempotency/linkage, customer/foreign-project denial, delete guard and OSM bounds')
if __name__=='__main__':main()
