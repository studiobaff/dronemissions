#!/usr/bin/env python3
"""Project-reference privacy and active POIs on a dedicated synthetic loopback installation."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args()
 assert urlparse(a.base).hostname in ('127.0.0.1','localhost','::1')
 c=Client(a.base);c.call('login',json.loads(a.access.read_text()))
 root=c.call('folder',{'name':'Reference test A'})['id'];sub=c.call('folder',{'parent':root,'name':'Child'})['id'];other=c.call('folder',{'name':'Reference test B'})['id']
 before=len(c.call('library')['missions']);geo=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'LineString','coordinates':[[16,48],[16.001,48.001]]},'properties':{'name':'Synthetic line'}}]}).encode()
 original=io.BytesIO()
 with zipfile.ZipFile(original,'w') as z:z.writestr('doc.kml','<kml><Placemark><LineString><coordinates>16,48 16.001,48.001</coordinates></LineString></Placemark></kml>')
 raw=original.getvalue()
 ref=c.call('layer-upload',{'folder':root,'name':'Project line'},files={'file':('ref.geojson',geo),'source':('reference.kmz',raw)})['id']
 assert len(c.call('library')['missions'])==before
 l=next(l for l in c.call('library')['layers'] if l['id']==ref);assert l['folder']==root
 assert c.call('layer-original&id='+ref)==raw
 c.call('layer-project',{'id':ref,'folder':'missing'},expected=404)
 view=c.call('share',{'folder':root,'role':'view'});v=Client(a.base);v.call('share-login',{'token':view['token']})
 edit=c.call('share',{'folder':root,'role':'edit'});e=Client(a.base);e.call('share-login',{'token':edit['token']})
 foreign=c.call('share',{'folder':other,'role':'edit'});f=Client(a.base);f.call('share-login',{'token':foreign['token']})
 assert not any(l['id']==ref for l in v.call('library')['layers']);v.call('layer-data&id='+ref,expected=403);v.call('layer-original&id='+ref,expected=403)
 assert any(l['id']==ref for l in e.call('library')['layers']);assert json.loads(e.call('layer-data&id='+ref))['features'];e.call('layer-original&id='+ref,expected=403)
 assert not any(l['id']==ref for l in f.call('library')['layers']);f.call('layer-data&id='+ref,expected=403);e.call('layer-project',{'id':ref,'folder':other},expected=403)
 c.call('layer-project',{'id':ref,'folder':other});assert not any(l['id']==ref for l in e.call('library')['layers']);e.call('layer-data&id='+ref,expected=403)
 assert any(l['id']==ref for l in f.call('library')['layers'])
 c.call('folder-delete',{'id':other,'name':'Reference test B','parent':None},expected=409)
 # Place active WPML POIs into a synthetic executable KMZ. Inactive placeholder ignored, repeated POI merged.
 source=synthetic_kmz();b=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(source)) as z,zipfile.ZipFile(b,'w') as out:
  for name in z.namelist():
   content=z.read(name)
   if name.endswith('.wpml'):
    text=content.decode();parts=text.split('</Placemark>')
    active='<wpml:waypointHeadingParam><wpml:waypointHeadingMode>towardPOI</wpml:waypointHeadingMode><wpml:waypointPoiPoint>48.002,16.003,5</wpml:waypointPoiPoint><wpml:waypointHeadingPoiIndex>2</wpml:waypointHeadingPoiIndex></wpml:waypointHeadingParam>'
    parts[0]+=active;parts[1]+=active;parts[2]+='<wpml:waypointHeadingParam><wpml:waypointHeadingMode>followWayline</wpml:waypointHeadingMode><wpml:waypointPoiPoint>0,0,0</wpml:waypointPoiPoint></wpml:waypointHeadingParam>';content='</Placemark>'.join(parts).encode()
   out.writestr(name,content)
 kmz=b.getvalue();m=c.call('upload',{'folder':sub,'name':'POI synthetic'},files={'kmz':('poi.kmz',kmz)})['id']
 mission=next(x for x in c.call('library')['missions'] if x['id']==m);pois=mission['details']['pois'];assert len(pois)==1 and pois[0]['lat']==48.002 and pois[0]['lng']==16.003 and pois[0]['waypoints']==[0,1] and pois[0]['label']=='POI 3',pois
 extra=c.call('preview-details&id='+m);assert extra['pois']==pois and extra['versionId']==mission['versionId']
 v.call('preview-details&id='+m,expected=403);f.call('preview-details&id='+m,expected=403)
 assert c.call('original&id='+m)==kmz;assert len(c.call('versions&id='+m)['versions'])==1
 assert b'POI 3' in c.call('preview&id='+m)
 c.call('layer-delete',{'id':ref});c.call('layer-data&id='+ref,expected=404)
 print('PASS: project association/reassignment, independent mission count, original byte identity, viewer/foreign-project denial, editor scope, delete guard, active POI coordinate order/deduplication, preview API and immutable KMZ/version')
if __name__=='__main__':main()
