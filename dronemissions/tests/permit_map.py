#!/usr/bin/env python3
"""Only synthetic missions in an explicitly selected loopback QA installation."""
import argparse,json,sys,io,zipfile,re
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);p.add_argument('--allow-test-writes',action='store_true',required=True);a=p.parse_args();assert urlparse(a.base).hostname in ('127.0.0.1','localhost')
c=Client(a.base);c.call('mission-start',{'id':'missing','lat':48,'lng':16},expected=401);c.call('nature',{'category':'NP','bbox':[16,47,17,48]},expected=401);c.call('login',json.loads(a.access.read_text()))
root=c.call('folder',{'name':'Freigabekarte Demo'})['id'];outside=c.call('folder',{'name':'Privater anderer Ordner'})['id']
raw=synthetic_kmz();buf=io.BytesIO()
with zipfile.ZipFile(io.BytesIO(raw)) as src,zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as out:
 for name in src.namelist():
  text=src.read(name).decode();text=re.sub(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',lambda m:f'{float(m[1])-16+16.367:.6f},{float(m[2])-48+47.874:.6f}',text);out.writestr(name,text)
raw=buf.getvalue();mid=c.call('upload',{'folder':root,'name':'Demo · Panorama Freigabe'},files={'kmz':('pano-demo.kmz',raw)})['id']
get=lambda:next(m for m in c.call('library')['missions'] if m['id']==mid)
m=get();assert m['takeoffPoint'] is None and m['panoPoint']=={'lat':47.875,'lng':16.369}
c.call('mission-start',{'id':mid,'revision':m['revision'],'lat':91,'lng':16},expected=400)
c.call('mission-start',{'id':mid,'revision':0,'lat':47.8725,'lng':16.3655},expected=409)
c.call('mission-start',{'id':mid,'revision':m['revision'],'lat':47.8725,'lng':16.3655});m=get();assert m['takeoffPoint']=={'lat':47.8725,'lng':16.3655} and m['overviewPoint']==m['panoPoint'];assert c.call('original&id='+mid)==raw
for capture in ['photo','video','panorama','sphere']:
 m=get();c.call('mission-map-type',{'id':mid,'revision':m['revision'],'captureType':capture});assert get()['captureType']==capture
m=get();c.call('mission-map-type',{'id':mid,'revision':m['revision'],'captureType':'invalid'},expected=400);assert c.call('original&id='+mid)==raw
c.call('share',{'folder':root,'role':'edit','presentation':'map'},expected=400)
share=c.call('share',{'folder':root,'role':'view','presentation':'map'});v=Client(a.base);v.call('share-login',{'token':share['token']});lib=v.call('library');assert lib['presentation']=='map' and len(lib['missions'])==1
public=lib['missions'][0];assert public['captureType']=='sphere';v.call('mission-map-type',{'id':mid,'revision':m['revision'],'captureType':'video'},expected=403);assert public['takeoffPoint']==m['takeoffPoint'] and public['panoPoint']==m['panoPoint'] and len(public['details']['points'])==1 and public['details']['routes']==[] and 'sha256' not in public and 'attachments' not in public
for endpoint in ['versions','original','package']:v.call(endpoint+'&id='+mid,expected=403)
v.call('mission-start',{'id':mid,'revision':m['revision'],'lat':48,'lng':16},expected=403)
edit=c.call('share',{'folder':outside,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':edit['token']});e.call('mission-start',{'id':mid,'revision':m['revision'],'lat':48,'lng':16},expected=403)
c.call('mission-start',{'id':mid,'revision':m['revision'],'lat':None,'lng':None});assert get()['takeoffPoint'] is None
m=get();c.call('mission-start',{'id':mid,'revision':m['revision'],'lat':47.8725,'lng':16.3655});assert c.call('original&id='+mid)==raw
c.call('nature',{'category':'INVALID','bbox':[16,47,17,48]},expected=400);c.call('nature',{'category':'NP','bbox':[9,46,18,49]},expected=400)
Path('work/permit-qa.json').write_text(json.dumps({'folder':root,'mission':mid,'shareToken':share['token']}));Path('work/permit-qa.json').chmod(0o600)
print('PASS: independent start point, exact waypoint 2, revision/coordinate checks, viewer redaction and write denial, project scope denial, clear/reset, byte-identical original, map-only share presentation, nature request validation')
