#!/usr/bin/env python3
"""KMZ editor lifecycle and permissions; synthetic, loopback-only test installation."""
import argparse, hashlib, io, json, zipfile
from pathlib import Path
from urllib.parse import urlparse
from integration import Client, synthetic_kmz
from previews import png

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args();assert urlparse(a.base).hostname in ('127.0.0.1','localhost','::1')
 c=Client(a.base);c.call('kmz-edit-load&id=missing',expected=401);c.call('login',json.loads(a.access.read_text()))
 folder=c.call('folder',{'name':'KMZ-Editor · Test'})['id'];other=c.call('folder',{'name':'KMZ-Editor · Fremd'})['id'];raw=synthetic_kmz()
 mid=c.call('upload',{'folder':folder,'name':'Editor · Rundflug'},files={'kmz':('editor.kmz',raw)})['id']
 def mission():return next(m for m in c.call('library')['missions'] if m['id']==mid)
 m=mission();c.call('mission',{'id':mid,'revision':m['revision'],'overviewWaypoint':2});m=mission()
 settings={'mode':'3d','title':'Editor','provider':'map','yaw':-35,'pitch':25,'zoom':1,'x':0,'y':0,'mapZoom':16}
 image=c.call('preview-save',{'id':mid,'revision':m['revision'],'sourceVersion':m['versionId'],'settings':json.dumps(settings)},files={'image':('preview.png',png())})['image']
 loaded=c.call('kmz-edit-load&id='+mid);assert len(loaded['points'])==5 and loaded['structureEditable'];assert loaded['sha256']==hashlib.sha256(raw).hexdigest()
 body={k:loaded[k] for k in ('id','revision','version','sha256')};body.update(changes=[{'index':1,'lat':48.0015,'lng':16.0025,'height':82}])
 view=c.call('share',{'folder':folder,'role':'view'});v=Client(a.base);v.call('share-login',{'token':view['token']});v.call('kmz-edit-load&id='+mid,expected=403);v.call('kmz-edit-save',body,expected=403)
 foreign=c.call('share',{'folder':other,'role':'edit'});f=Client(a.base);f.call('share-login',{'token':foreign['token']});f.call('kmz-edit-load&id='+mid,expected=403);f.call('kmz-edit-save',body,expected=403)
 csrf=c.csrf;c.csrf='incorrect';c.call('kmz-edit-save',body,expected=403);c.csrf=csrf
 c.call('kmz-edit-save',dict(body,changes=[]),expected=400);c.call('kmz-edit-save',dict(body,changes=[{'index':1,'height':None}]),expected=400)
 result=c.call('kmz-edit-save',body);assert result['version']==2;new=c.call('kmz-edit-load&id='+mid);assert new['points'][1]['height']==82 and new['points'][1]['lat']==48.0015
 assert c.call('kmz&id='+mid+'&version='+loaded['version'])==raw
 assert len(c.call('versions&id='+mid)['versions'])==2
 assert mission()['overview_waypoint']==2 and mission()['overview_version']==new['version']
 pictures=c.call('previews&id='+mid);assert pictures['active'] is None and any(i['id']==image for i in pictures['images'])
 c.call('kmz-edit-save',body,expected=409) # stale source cannot overwrite new version
 edit=c.call('share',{'folder':folder,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':edit['token']})
 body={k:new[k] for k in ('id','revision','version','sha256')};body.update(changes=[],deletions=[1],insertions=[{'after':2,'lat':48.0001,'lng':16.003,'height':71}]);e.call('kmz-edit-save',body)
 latest=c.call('kmz-edit-load&id='+mid);assert len(latest['points'])==5 and latest['points'][2]['height']==71 and latest['ordinal']==3
 assert mission()['overview_waypoint'] is None and mission()['overview_version'] is None
 assert c.call('kmz&id='+mid+'&version='+loaded['version'])==raw
 assert mission()['details']['editor']['sourceVersion']==new['version']
 print('PASS: editor load/save/roundtrip, immutable V1, CAS, authentication, CSRF, customer/project scopes, preview history and overview remap/reset')
if __name__=='__main__':main()
