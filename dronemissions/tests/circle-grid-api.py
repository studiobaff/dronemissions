import sys,json,io,zipfile,argparse
from urllib.parse import urlparse
from pathlib import Path
from integration import Client,synthetic_kmz
parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--access',type=Path,required=True);args=parser.parse_args();assert urlparse(args.base).hostname in ('127.0.0.1','localhost','::1')
c=Client(args.base);c.call('login',json.loads(args.access.read_text()))
f=c.call('folder',{'name':'Synthetic 3DGS QA'})['id'];profile=c.call('upload',{'folder':f,'name':'Synthetic device'},files={'kmz':('device.kmz',synthetic_kmz())})['id']
p={'name':'3DGS circle-grid QA','type':'circleGrid','cameraId':'mavic3','geometry':{'type':'Polygon','coordinates':[[[16,48],[16.0004,48],[16.0004,48.0004],[16,48.0004],[16,48]]]},'params':{'captureMode':'video','bottom':30,'top':55,'orbitRadius':30,'circleOverlap':50,'orbitLevels':2,'speed':3,'maxYawRate':6,'sampleFps':2,'photoLimit':150,'terrainMode':'off','poiReference':'relative','pitchMode':'auto'}}
b={'folder':f,'profileMission':profile,'plan':p};r=c.call('planner-preview',b);assert r['circleGrid']['orbits']==4
saved=c.call('planner-save',b);loaded=c.call('planner-load&id='+saved['id']);replay=c.call('planner-preview',{'folder':f,'plan':loaded['body']});assert r['routeSha256']==replay['routeSha256']
b.update(saved);raw=c.call('planner-export',b);z=zipfile.ZipFile(io.BytesIO(raw));assert len([n for n in z.namelist() if n.endswith('.kmz')])==4
print('PASS: API preview, draft save/load/replay and four-orbit video KMZ bundle export')
# Both capture modes, with separate and continuous paths, must export valid action lifecycles.
import copy,xml.etree.ElementTree as E
for mode in ['photo','video']:
 for path in ['continuous','separate']:
  q=copy.deepcopy(p);q['params'].update({'captureMode':mode,'orbitPath':path,'photoDistance':5,'photoLimit':200})
  body={'folder':f,'profileMission':profile,'plan':q};preview=c.call('planner-preview',body)
  assert (preview['summary']['photos']>0)==(mode=='photo')
  raw=c.call('planner-export',body);outer=zipfile.ZipFile(io.BytesIO(raw))
  bundles=[outer.read(n) for n in outer.namelist() if n.endswith('.kmz')] if 'wpmz/waylines.wpml' not in outer.namelist() else [raw]
  for data in bundles:
   exported=zipfile.ZipFile(io.BytesIO(data));xml=E.fromstring(exported.read('wpmz/waylines.wpml'))
   funcs=[e.text for e in xml.iter() if e.tag.rsplit('}',1)[-1]=='actionActuatorFunc']
   assert funcs.count('startRecord')==(1 if mode=='video' else 0) and funcs.count('stopRecord')==(1 if mode=='video' else 0)
   assert ('takePhoto' in funcs)==(mode=='photo')
print('PASS: photo/video × continuous/separate API export and recording/photo actions.')
