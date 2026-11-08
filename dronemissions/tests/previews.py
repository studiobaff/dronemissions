#!/usr/bin/env python3
"""Preview history/selection/authorization regressions; synthetic loopback test only."""
import argparse, io, json, struct, zlib, zipfile
from pathlib import Path
from urllib.parse import urlparse
from integration import Client, synthetic_kmz

def png():
    def chunk(t, d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,20,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes([20,80,50])*32)*20))+chunk(b'IEND',b'')

def main():
    a=argparse.ArgumentParser();a.add_argument('--base',required=True);a.add_argument('--access',type=Path,required=True);o=a.parse_args()
    assert urlparse(o.base).hostname in ('127.0.0.1','localhost','::1')
    c=Client(o.base);c.call('login',json.loads(o.access.read_text()));folder=c.call('folder',{'name':'Vorschaubilder · Test'})['id'];other=c.call('folder',{'name':'Anderes Projekt · Test'})['id']
    m=c.call('upload',{'folder':folder,'name':'Halbkugel'},files={'kmz':('demo.kmz',synthetic_kmz())})['id']
    def mission(): return next(x for x in c.call('library')['missions'] if x['id']==m)
    before=mission();versions=c.call('versions&id='+m)['versions'];original=c.call('original&id='+m)
    initial=c.call('previews&id='+m);assert initial['images']==[] and initial['active'] is None
    settings={'mode':'3d','title':'Halbkugel','provider':'map','yaw':-35,'pitch':25,'zoom':1,'x':0,'y':0,'mapZoom':16}
    body={'id':m,'revision':before['revision'],'sourceVersion':before['versionId'],'settings':json.dumps(settings)}
    image=c.call('preview-save',body,files={'image':('render.png',png())})['image']
    c.call('preview-save',body,files={'image':('render.png',png())},expected=409)
    body['revision']=mission()['revision'];body['settings']=json.dumps(dict(settings,mode='photo'))
    photo=c.call('preview-save',body,files={'image':('render.png',png()),'photo':('source.png',png())})['image']
    pictures=c.call('previews&id='+m);assert len(pictures['images'])==2 and pictures['active']==photo
    assert pictures['images'][0]['source_version']==before['versionId']
    rendered=c.call('preview-image&id='+m+'&image='+image);assert rendered.startswith(b'\xff\xd8')
    assert c.call('preview-image&id='+m+'&image='+photo+'&source=1').startswith(b'\xff\xd8')
    c.call('preview-image&id='+m+'&image='+image+'&source=1',expected=404)
    c.call('preview-select',{'id':m,'revision':mission()['revision'],'image':image})
    assert c.call('previews&id='+m)['active']==image
    assert c.call('preview&id='+m)==rendered
    assert c.call('versions&id='+m)['versions']==versions and c.call('original&id='+m)==original
    assert mission()['versionId']==before['versionId'] and mission()['sha256']==before['sha256']
    with zipfile.ZipFile(io.BytesIO(c.call('package&id='+m))) as z: assert z.read('preview.jpg')==rendered
    body['revision']=mission()['revision'];body['photoImage']=photo
    copy=c.call('preview-save',body,files={'image':('render.png',png())})['image'];assert copy!=photo
    body['revision']=mission()['revision'];body['photoImage']=image
    c.call('preview-save',body,files={'image':('render.png',png())},expected=400)
    body['settings']=json.dumps(dict(settings,zoom=100));c.call('preview-save',body,files={'image':('render.png',png())},expected=400)
    body['settings']=json.dumps(settings);c.call('preview-save',body,files={'image':('evil.svg',b'<svg/>')},expected=400)
    bad=c.call('upload',{'folder':other,'name':'Privat'},files={'kmz':('other.kmz',synthetic_kmz())})['id']
    c.call('preview-select',{'id':bad,'revision':1,'image':image},expected=404)
    viewer=c.call('share',{'folder':folder,'role':'view'})['token'];editor=c.call('share',{'folder':folder,'role':'edit'})['token']
    v=Client(o.base);v.call('share-login',{'token':viewer})
    for action in ['previews&id='+m,'preview-image&id='+m+'&image='+image]:v.call(action,expected=403)
    v.call('preview-select',{'id':m,'revision':mission()['revision'],'image':image},expected=403)
    e=Client(o.base);e.call('share-login',{'token':editor});e.call('previews&id='+bad,expected=403)
    e.call('preview-select',{'id':bad,'revision':1,'image':image},expected=403)
    assert len(c.call('previews&id='+m)['images'])==3
    c.call('logout',{});v.call('logout',{});e.call('logout',{})
    print('Preview history, selection, source reuse, immutable mission versions, package, CAS and scope tests passed.')
if __name__=='__main__': main()
