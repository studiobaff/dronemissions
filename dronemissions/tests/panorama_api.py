#!/usr/bin/env python3
import argparse,json,io,zipfile
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);p.add_argument('--allow-test-writes',action='store_true',required=True);a=p.parse_args();assert urlparse(a.base).hostname in ('127.0.0.1','localhost')
c=Client(a.base);c.call('login',json.loads(a.access.read_text()));folder=c.call('folder',{'name':'Pano Reorder QA'})['id'];outside=c.call('folder',{'name':'Foreign reorder QA'})['id'];raw=synthetic_kmz();ids=[]
for name in ['OeBB.EF.Pano.008','OeBB.EF.Pano010','OeBB.EF.Pano.003']:
 ids.append(c.call('upload',{'folder':folder,'name':name},files={'kmz':(name+'.kmz',raw)})['id'])
get=lambda:[m for m in c.call('library')['missions'] if m['id'] in ids]
rows=lambda:[{'id':m['id'],'revision':m['revision']} for m in sorted(get(),key=lambda m:ids.index(m['id']))]
before=rows();c.call('mission-map-order',{'items':list(reversed(before))});assert [m['id'] for m in sorted(get(),key=lambda m:m['mapOrder'])]==list(reversed(ids));c.call('mission-map-order',{'items':before},expected=409)
c.call('mission-map-order',{'items':[rows()[0],rows()[0]]},expected=400)
for mid in ids:assert c.call('original&id='+mid)==raw
view=c.call('share',{'folder':folder,'role':'view','presentation':'map'});v=Client(a.base);v.call('share-login',{'token':view['token']});v.call('mission-map-order',{'items':rows()},expected=403);assert all('mapOrder' in m for m in v.call('library')['missions'])
share=c.call('share',{'folder':outside,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':share['token']});e.call('mission-map-order',{'items':rows()},expected=403)
c.call('mission-map-order',{'items':rows(),'reset':True});assert all(m['mapOrder'] is None for m in get())
for mode in ['panorama','sphere']:
 plan={'name':'Synthetic '+mode,'type':mode,'cameraId':'mavic3','geometry':{'type':'LineString','coordinates':[[16,48],[16.001,48.001]]},'params':{'height':60,'panoOverlap':30,'panoPitch':0,'panoUpperPitch':20,'captureMode':mode}}
 body={'folder':folder,'profileMission':ids[0],'plan':plan};preview=c.call('planner-preview',body);assert len(preview['points'])==2 and preview['panorama']['photos']>3
 body.update(c.call('planner-save',body));loaded=c.call('planner-load&id='+body['id']);assert loaded['body']['params']['captureMode']==mode
 data=c.call('planner-export',body);z=zipfile.ZipFile(io.BytesIO(data));assert z.read('wpmz/waylines.wpml').count(b'<wpml:actionActuatorFunc>takePhoto</wpml:actionActuatorFunc>')==preview['summary']['photos']
 archived=c.call('planner-archive',body)['ids'];m=next(m for m in c.call('library')['missions'] if m['id']==archived[0]);assert m['captureType']==mode and m['overview_waypoint']==1 and m['panoPoint']=={'lat':48.001,'lng':16.001}
print('PASS: panorama preview/save/load/export/archive, WP2 capture metadata, manual order persistence/reset/CAS, original integrity and viewer/foreign-scope write denial')
