#!/usr/bin/env python3
"""Destructive only to a dedicated empty test installation. Stdlib, synthetic data."""
import argparse, hashlib, http.cookiejar, io, json, urllib.request, urllib.error, uuid, zipfile
from pathlib import Path
from urllib.parse import urlparse

class Client:
    def __init__(self, base):
        self.base = base.rstrip('/') + '/api.php?action='
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = self.call('session')['csrf']
    def call(self, action, body=None, expected=200, files=None):
        headers = {}; payload = None
        if body is not None:
            headers['X-CSRF-Token'] = self.csrf
            if files:
                boundary = uuid.uuid4().hex
                chunks = []
                for k, v in body.items():
                    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
                for k, (name, raw) in files.items():
                    chunks += [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), raw, b'\r\n']
                payload = b''.join(chunks) + f'--{boundary}--\r\n'.encode()
                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
            else:
                payload = json.dumps(body).encode(); headers['Content-Type'] = 'application/json'
        try:
            response = self.opener.open(urllib.request.Request(self.base + action, data=payload, headers=headers))
        except urllib.error.HTTPError as e: response = e
        raw = response.read()
        assert response.status == expected, (action, response.status, raw[:300])
        if 'application/json' in response.headers.get('Content-Type',''):
            data = json.loads(raw)
            if 'csrf' in data: self.csrf = data['csrf']
            return data
        return raw

def synthetic_kmz(height=60):
    points = [(16.0,48.0),(16.002,48.001),(16.004,48.0),(16.002,47.999),(16.0,48.0)]
    marks = ''.join(f'<Placemark><Point><coordinates>{lng},{lat}</coordinates></Point><wpml:index>{i}</wpml:index><wpml:executeHeight>{height+i*3}</wpml:executeHeight><wpml:waypointSpeed>5</wpml:waypointSpeed></Placemark>' for i,(lng,lat) in enumerate(points))
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('wpmz/template.kml','<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><name>Demo · Rundflug</name><wpml:droneEnumValue>99</wpml:droneEnumValue></Document></kml>')
        z.writestr('wpmz/waylines.wpml',f'<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><Folder><wpml:waylineId>0</wpml:waylineId><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>{marks}</Folder></Document></kml>')
    return buf.getvalue()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--base',required=True); p.add_argument('--access',type=Path,required=True);p.add_argument('--fixture-dir',type=Path);p.add_argument('--allow-test-writes',action='store_true',required=True); a=p.parse_args()
    assert urlparse(a.base).hostname in ('127.0.0.1','localhost','::1'), 'Integration tests require a loopback-only dedicated test installation'
    c=Client(a.base); c.call('library',expected=401)
    c.call('login',{'password':'incorrect'},expected=401); c.call('login',json.loads(a.access.read_text()))
    saved=c.csrf;c.csrf='invalid';c.call('folder',{'name':'CSRF blocked'},expected=403);c.csrf=saved
    assert not c.call('library')['missions'], 'Use a dedicated empty test installation'
    root=c.call('folder',{'name':'Demo · Küstenprojekt'})['id']; sub=c.call('folder',{'name':'Routen','parent':root})['id']; other=c.call('folder',{'name':'Privates Gegenprojekt'})['id']
    c.call('folder',{'id':root,'name':'Zyklus','parent':sub},expected=400)
    raw=synthetic_kmz(); raw2=synthetic_kmz(75)
    m=c.call('upload',{'folder':sub,'name':'Demo · Rundflug'},files={'kmz':('demo.kmz',raw)})['id']
    lib=c.call('library'); mission=next(x for x in lib['missions'] if x['id']==m)
    assert mission['details']['count']==5 and mission['details']['distance']>500
    assert c.call('kmz&id='+m)==raw
    c.call('upload',{'mission':m,'revision':mission['revision'],'name':'Demo'},files={'kmz':('demo-v2.kmz',raw2)})
    c.call('upload',{'mission':m,'revision':mission['revision'],'name':'Stale'},expected=409,files={'kmz':('stale.kmz',raw)})
    versions=c.call('versions&id='+m)['versions']; assert len(versions)==2
    assert c.call('kmz&id='+m+'&version='+versions[-1]['id'])==raw
    with zipfile.ZipFile(io.BytesIO(c.call('package&id='+m))) as z:
        manifest=json.loads(z.read('manifest.json')); assert z.read('mission.kmz')==raw2; assert manifest['files']['mission.kmz']==hashlib.sha256(raw2).hexdigest()
    assert b'<svg' in c.call('preview&id='+m)
    c.call('upload',{'folder':sub,'name':'Bad'},expected=400,files={'kmz':('broken.kmz',b'broken')})
    point={'folder':sub,'name':'Demo · Panorama','lat':48.001,'lng':16.002,'settings':{'height':60,'heading':0,'gimbal':-90,'heightMode':'relativeToStartPoint','capture':'sphere'}}
    pointid=c.call('point',point)['id']; c.call('point',{**point,'id':pointid,'revision':0},expected=409)
    view=c.call('share',{'folder':root,'role':'view'}); edit=c.call('share',{'folder':root,'role':'edit'})
    v=Client(a.base);v.call('share-login',{'token':view['token']}); visible=v.call('library'); assert len(visible['folders'])==2 and len(visible['missions'])==1 and len(visible['points'])==1
    assert other not in json.dumps(visible)
    v.call('upload',{'folder':sub,'name':'Blocked'},expected=403,files={'kmz':('demo.kmz',raw)});v.call('point',point,expected=403);v.call('folder',{'name':'No','parent':root},expected=403);v.call('shares',expected=403);v.call('share',{'folder':root},expected=403);v.call('folder',{'id':other,'name':'Leak'},expected=403)
    assert v.call('kmz&id='+m)==raw2
    c.call('folder-archive',{'id':root,'archived':True});nested=c.call('share',{'folder':sub,'role':'view'});n=Client(a.base);n.call('share-login',{'token':nested['token']});assert next(f for f in n.call('library')['folders'] if f['id']==sub)['inheritedArchived'];c.call('revoke',{'id':nested['id']});c.call('folder-archive',{'id':root,'archived':False})
    e=Client(a.base);e.call('share-login',{'token':edit['token']});e.call('folder',{'name':'Editor-Unterordner','parent':sub});e.call('folder',{'name':'Escape','parent':other},expected=403);e.call('mission',{'id':m,'revision':2,'folder':other},expected=403);e.call('folder',{'id':root,'name':'Escape','parent':sub},expected=400)
    c.call('revoke',{'id':view['id']});v.call('library',expected=401);v.call('share-login',{'token':view['token']},expected=403)
    c.call('folder-archive',{'id':root,'archived':True});assert next(f for f in c.call('library')['folders'] if f['id']==root)['archived']==1
    c.call('folder-archive',{'id':root,'archived':False})
    mission=next(x for x in c.call('library')['missions'] if x['id']==m)
    c.call('mission',{'id':m,'revision':mission['revision'],'notes':'Synthetische Demo. Keine reale Flugplanung.'})
    c.call('mission',{'id':m,'revision':mission['revision'],'name':'Stale'},expected=409)
    c.call('revoke',{'id':edit['id']});e.call('library',expected=401)
    csv=b'latitude,longitude,altitude(m),heading(deg),speed(m/s),altitudemode\r\n48,16,50,90,5,0\r\n48.001,16.001,60,180,5,0\r\n'
    csv_id=c.call('upload',{'folder':sub,'name':'Demo · Litchi CSV'},files={'kmz':('legacy.csv',csv)})['id']
    assert c.call('original&id='+csv_id)==csv
    csv_mission=next(x for x in c.call('library')['missions'] if x['id']==csv_id);assert csv_mission['details']['sourceFormat']=='litchi-csv'
    with zipfile.ZipFile(io.BytesIO(c.call('package&id='+csv_id))) as z:
        assert z.read('mission.csv')==csv;assert json.loads(z.read('manifest.json'))['files']['mission.csv']==hashlib.sha256(csv).hexdigest()
    assert b'<svg' in c.call('preview&id='+csv_id)
    c.call('upload',{'folder':sub,'name':'Bad CSV'},expected=400,files={'kmz':('bad.csv',b'bad,header\n1,2')})
    if a.fixture_dir:
        a.fixture_dir.mkdir(parents=True,exist_ok=True);(a.fixture_dir/'demo.kmz').write_bytes(raw)
    print('PASS: authentication, folders/cycles, parsing, versions/conflicts, exact KMZ, package hashes, previews, points/conflicts, read/edit scopes, revocation, archive and metadata conflicts')
if __name__=='__main__': main()
