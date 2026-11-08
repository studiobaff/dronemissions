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

def test_layers(c,a,root):
    """Eigene Kartenebenen: Validierung, Schlüssel, Vektor-Upload mit Bereinigung, Auslieferung, Rechte, CSP."""
    assert c.call('layers')['layers']==[]
    c.call('layer-save',{'name':'Kaputt','url':'http://tiles.example.org/{z}/{x}/{y}.png'},expected=400)   # kein https
    c.call('layer-save',{'name':'Kaputt','url':'https://tiles.example.org/{z}/{x}.png'},expected=400)       # {y} fehlt
    c.call('layer-save',{'name':'','url':'https://tiles.example.org/{z}/{x}/{y}.png'},expected=400)         # Name fehlt
    c.call('layer-save',{'name':'Mapbox','url':'https://api.mapbox.com/{z}/{x}/{y}?access_token={key}'},expected=400)  # {key} ohne Schlüssel
    tile=c.call('layer-save',{'name':'Mapbox','url':'https://api.mapbox.com/{z}/{x}/{y}?access_token={key}','key':'pk.secret','attribution':'© Mapbox','maxZoom':22,'overlay':False})['id']
    listed=c.call('layers')['layers'];assert len(listed)==1 and 'key' not in listed[0]['config'] and listed[0]['config']['keyHint']=='pk.s…'
    c.call('layer-save',{'id':tile,'name':'Mapbox Streets','url':'https://api.mapbox.com/{z}/{x}/{y}?access_token={key}','key':'','maxZoom':22})   # leerer Schlüssel behält den gespeicherten
    public=[l for l in c.call('library')['layers'] if l['kind']=='tile'];assert public[0]['url'].endswith('access_token=pk.secret') and public[0]['name']=='Mapbox Streets'
    html=c.opener.open(a.base.rstrip('/')+'/');csp=html.headers.get('Content-Security-Policy');assert 'https://api.mapbox.com' in csp,csp
    geo=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[16.7,47.8],[16.71,47.8],[16.71,47.81],[16.7,47.8]]]},'properties':{'name':'Fläche','x':1,'nested':{'a':1}}},{'type':'Feature','geometry':{'type':'Weird','coordinates':[]},'properties':{}}]}).encode()
    vec=c.call('layer-upload',{'name':'Schutzgebiete','color':'#2f8f4e','attribution':'Testdaten'},files={'file':('ebene.geojson',geo)});assert vec['features']==1
    c.call('layer-upload',{'name':'Leer'},expected=400,files={'file':('leer.geojson',b'{"type":"FeatureCollection","features":[]}')})
    c.call('layer-upload',{'name':'Kein GeoJSON'},expected=400,files={'file':('x.geojson',b'[1,2,3]')})
    data=json.loads(c.call('layer-data&id='+vec['id']));assert data['features'][0]['properties']=={'name':'Fläche','x':1} and len(data['features'])==1
    public=c.call('library')['layers'];assert any(l['kind']=='vector' and l['features']==1 and l['color']=='#2f8f4e' for l in public)
    customer=c.call('share',{'folder':root,'role':'view'});cust=Client(a.base);cust.call('share-login',{'token':customer['token']})
    assert json.loads(cust.call('layer-data&id='+vec['id']))['features'];cust.call('layers',expected=403);cust.call('layer-delete',{'id':vec['id']},expected=403);cust.call('layer-save',{'name':'x','url':'https://t.example/{z}/{x}/{y}.png'},expected=403)
    c.call('revoke',{'id':customer['id']})
    c.call('wmts-capabilities',{'url':'http://127.0.0.1:1/wmts'},expected=400) if not a.wmts_fixture else None
    if a.wmts_fixture:
        layers=c.call('wmts-capabilities',{'url':a.wmts_fixture})['layers'];assert [l['id'] for l in layers]==['ortho','karte'],layers
        assert layers[0]['url']=='https://tiles.example.org/normal/google3857/{z}/{y}/{x}.jpeg' and 'TILEMATRIX=EPSG:3857:{z}' in layers[1]['url'] and layers[0]['maxZoom']==18
    c.call('layer-delete',{'id':vec['id']});c.call('layer-delete',{'id':tile});c.call('layer-delete',{'id':tile},expected=404);c.call('layer-data&id='+vec['id'],expected=404)
    assert c.call('layers')['layers']==[]
    print('PASS: custom map layers: validation, key handling and masking, CSP host, vector upload cleanup, viewer read-only, WMTS import'+('' if a.wmts_fixture else ' (fixture skipped)'))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--base',required=True); p.add_argument('--access',type=Path,required=True);p.add_argument('--fixture-dir',type=Path);p.add_argument('--allow-test-writes',action='store_true',required=True);p.add_argument('--wmts-fixture',help='http(s) URL of a WMTS capabilities document reachable from the server (DRONEMISSIONS_DEV allows loopback)'); a=p.parse_args()
    assert urlparse(a.base).hostname in ('127.0.0.1','localhost','::1'), 'Integration tests require a loopback-only dedicated test installation'
    c=Client(a.base); c.call('library',expected=401)
    c.call('login',{'password':'incorrect'},expected=401); c.call('login',json.loads(a.access.read_text()))
    saved=c.csrf;c.csrf='invalid';c.call('folder',{'name':'CSRF blocked'},expected=403);c.csrf=saved
    assert not c.call('library')['missions'], 'Use a dedicated empty test installation'
    author='Demo & Co <Test>';c.call('settings',{'authorName':author});assert c.call('settings')=={'authorName':author};html=c.opener.open(a.base.rstrip('/')+'/').read();assert b'Demo &amp; Co &lt;Test&gt;' in html and b'Demo & Co <Test>' not in html
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
        manifest=json.loads(z.read('manifest.json'));assert manifest['author']==author; assert z.read('mission.kmz')==raw2; assert manifest['files']['mission.kmz']==hashlib.sha256(raw2).hexdigest()
    assert b'<svg' in c.call('preview&id='+m)
    c.call('upload',{'folder':sub,'name':'Bad'},expected=400,files={'kmz':('broken.kmz',b'broken')})
    point={'folder':sub,'name':'Demo · Panorama','lat':48.001,'lng':16.002,'settings':{'height':60,'heading':0,'gimbal':-90,'heightMode':'relativeToStartPoint','capture':'sphere'}}
    pointid=c.call('point',point)['id']; c.call('point',{**point,'id':pointid,'revision':0},expected=409)
    current=next(x for x in c.call('library')['missions'] if x['id']==m)
    for bad in [-1,5,True,'2']:
        c.call('mission',{'id':m,'revision':current['revision'],'overviewWaypoint':bad},expected=400)
    c.call('mission',{'id':m,'revision':current['revision'],'overviewWaypoint':2,'litchiURL':'https://hub.flylitchi.com/?m=demo123'})
    view=c.call('share',{'folder':root,'role':'view'}); edit=c.call('share',{'folder':root,'role':'edit'})
    v=Client(a.base);v.call('share-login',{'token':view['token']}); visible=v.call('library'); assert len(visible['folders'])==2 and len(visible['missions'])==1 and len(visible['points'])==1
    assert other not in json.dumps(visible)
    v.call('upload',{'folder':sub,'name':'Blocked'},expected=403,files={'kmz':('demo.kmz',raw)});v.call('point',point,expected=403);v.call('folder',{'name':'No','parent':root},expected=403);v.call('shares',expected=403);v.call('settings',expected=403);v.call('settings',{'authorName':'Blocked'},expected=403);v.call('share',{'folder':root},expected=403);v.call('folder',{'id':other,'name':'Leak'},expected=403)
    for endpoint in ['kmz','original','package','versions']:
        v.call(endpoint+'&id='+m,expected=403)
    public=visible['missions'][0];assert len(public['details']['points'])==1 and public['details']['routes']==[] and public['overviewPoint']=={'lat':48.0,'lng':16.004}
    assert public['notes']=='' and public['filename']=='' and 'sha256' not in public
    assert b'16.004,48' in v.call('location&id='+m)
    assert b'<polyline' not in v.call('preview&id='+m)
    c.call('folder-archive',{'id':root,'archived':True});nested=c.call('share',{'folder':sub,'role':'edit'});n=Client(a.base);n.call('share-login',{'token':nested['token']});assert next(f for f in n.call('library')['folders'] if f['id']==sub)['inheritedArchived'];c.call('revoke',{'id':nested['id']});c.call('folder-archive',{'id':root,'archived':False})
    e=Client(a.base);e.call('share-login',{'token':edit['token']});e.call('settings',{'authorName':'Blocked'},expected=403);e.call('folder',{'name':'Editor-Unterordner','parent':sub});e.call('folder',{'name':'Escape','parent':other},expected=403);e.call('mission',{'id':m,'revision':2,'folder':other},expected=403);e.call('folder',{'id':root,'name':'Escape','parent':sub},expected=400)
    c.call('revoke',{'id':view['id']});v.call('library',expected=401);v.call('share-login',{'token':view['token']},expected=403)
    c.call('folder-archive',{'id':root,'archived':True});assert next(f for f in c.call('library')['folders'] if f['id']==root)['archived']==1
    c.call('folder-archive',{'id':root,'archived':False})
    mission=next(x for x in c.call('library')['missions'] if x['id']==m)
    c.call('mission',{'id':m,'revision':mission['revision'],'notes':'Synthetische Demo. Keine reale Flugplanung.'})
    c.call('mission',{'id':m,'revision':mission['revision'],'name':'Stale'},expected=409)
    c.call('revoke',{'id':edit['id']});e.call('library',expected=401)
    native_project=json.dumps({'version':1,'type':'polygon','polygon':[[48,16],[48.001,16],[48.001,16.001]],'settings':{'altitude':60}}).encode()
    project=c.call('upload',{'folder':sub,'name':'Map Creator Demo'},files={'kmz':('demo.mproj',native_project)})['id']
    assert c.call('original&id='+project)==native_project
    proj=next(x for x in c.call('library')['missions'] if x['id']==project);assert proj['details']['sourceFormat']=='mapcreator-project' and proj['details']['points']==[]
    c.call('mission',{'id':project,'revision':proj['revision'],'overviewWaypoint':0},expected=400)
    target=next(x for x in c.call('library')['missions'] if x['id']==m)
    c.call('attach-source',{'target':m,'source':project,'targetRevision':0,'sourceRevision':proj['revision']},expected=409)
    assert not next(x for x in c.call('library')['missions'] if x['id']==project)['archived']
    c.call('attach-source',{'target':m,'source':project,'targetRevision':target['revision'],'sourceRevision':proj['revision']})
    attached=next(x for x in c.call('library')['missions'] if x['id']==m)['attachments'];assert len(attached)==1 and attached[0]['format']=='mproj'
    assert c.call('attachment&id='+m+'&version='+attached[0]['id'])==native_project
    assert c.call('original&id='+m)==raw2
    with zipfile.ZipFile(io.BytesIO(c.call('package&id='+m))) as bundle:
        assert bundle.read('sources/1-demo.mproj')==native_project
        assert json.loads(bundle.read('manifest.json'))['files']['sources/1-demo.mproj']==hashlib.sha256(native_project).hexdigest()
    viewer_link=c.call('share',{'folder':root,'role':'view'});viewer=Client(a.base);viewer.call('share-login',{'token':viewer_link['token']})
    viewer.call('attachment&id='+m+'&version='+attached[0]['id'],expected=403)
    assert 'attachments' not in next(x for x in viewer.call('library')['missions'] if x['id']==m)
    c.call('revoke',{'id':viewer_link['id']})
    csv=b'latitude,longitude,altitude(m),heading(deg),speed(m/s),altitudemode\r\n48,16,50,90,5,0\r\n48.001,16.001,60,180,5,0\r\n'
    csv_id=c.call('upload',{'folder':sub,'name':'Demo · Litchi CSV'},files={'kmz':('legacy.csv',csv)})['id']
    assert c.call('original&id='+csv_id)==csv
    csv_mission=next(x for x in c.call('library')['missions'] if x['id']==csv_id);assert csv_mission['details']['sourceFormat']=='litchi-csv'
    with zipfile.ZipFile(io.BytesIO(c.call('package&id='+csv_id))) as z:
        assert z.read('mission.csv')==csv;assert json.loads(z.read('manifest.json'))['files']['mission.csv']==hashlib.sha256(csv).hexdigest()
    assert b'<svg' in c.call('preview&id='+csv_id)
    c.call('upload',{'folder':sub,'name':'Bad CSV'},expected=400,files={'kmz':('bad.csv',b'bad,header\n1,2')})
    native_zip=io.BytesIO();native_zip.write(b'lchz'+b'\0'*4)
    with zipfile.ZipFile(native_zip,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('flight.lch2',b'lch2'+b'\0'*20)
    embedded=io.BytesIO()
    with zipfile.ZipFile(embedded,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('flight.lch2',b'lch2'+b'\0'*20)
    embedded_native=b'lchz'+len(embedded.getvalue()).to_bytes(4,'big')+embedded.getvalue()
    for ext,native in [('lchm',b'lchm'+b'\0'*20),('lchz',native_zip.getvalue()),('lchz',embedded_native)]:
        native_id=c.call('upload',{'folder':sub,'name':'Native Demo '+ext},files={'kmz':('demo.'+ext,native)})['id']
        assert c.call('original&id='+native_id)==native
        item=next(x for x in c.call('library')['missions'] if x['id']==native_id);assert item['details']['previewAvailable'] is False and item['details']['points']==[]
        assert b'Litchi Original' in c.call('preview&id='+native_id)
        with zipfile.ZipFile(io.BytesIO(c.call('package&id='+native_id))) as z:assert z.read('mission.'+ext)==native
        c.call('upload',{'folder':sub,'name':'Bad'},expected=400,files={'kmz':('broken.'+ext,b'wrong-header')})
    # Bulk changes are atomic, revision checked, and constrained on both source and destination.
    bulk=[]
    for i in range(10):
        bulk.append(c.call('upload',{'folder':sub,'name':f'Auswahl Demo {i+1:02}'},files={'kmz':('demo.kmz',raw)})['id'])
    rows=[x for x in c.call('library')['missions'] if x['id'] in bulk]
    batch=[{'id':x['id'],'revision':x['revision']} for x in rows]
    c.call('missions-move',{'folder':other,'missions':batch[:-1]+[{**batch[-1],'revision':0}]},expected=409)
    assert all(x['folder']==sub for x in c.call('library')['missions'] if x['id'] in bulk)
    c.call('missions-move',{'folder':other,'missions':batch+batch[:1]},expected=400)
    readonly=c.call('share',{'folder':root,'role':'view'});reader=Client(a.base);reader.call('share-login',{'token':readonly['token']})
    reader.call('missions-move',{'folder':sub,'missions':batch},expected=403)
    editable=c.call('share',{'folder':root,'role':'edit'});editor=Client(a.base);editor.call('share-login',{'token':editable['token']})
    editor.call('missions-move',{'folder':other,'missions':batch},expected=403)
    assert c.call('missions-move',{'folder':other,'missions':batch})['moved']==10
    rows=[x for x in c.call('library')['missions'] if x['id'] in bulk]
    assert all(x['folder']==other for x in rows)
    batch=[{'id':x['id'],'revision':x['revision']} for x in rows]
    editor.call('missions-move',{'folder':sub,'missions':batch},expected=403)
    c.call('missions-move',{'folder':None,'missions':batch})
    for mid in bulk:assert c.call('original&id='+mid)==raw
    c.call('revoke',{'id':readonly['id']});c.call('revoke',{'id':editable['id']})
    print('PASS: ten-mission bulk move, stale/duplicate atomic rejection, source/destination scopes, viewer denial, exact originals')
    bridge=c.call('bridge');assert bridge['archiveURL'].endswith('/dronemissions/') and isinstance(bridge['files'],list) and bridge['folder']=='bridge/'
    cfg=c.call('bridge-config');assert cfg['format']=='dronemissions-bridge-config/1' and cfg['archiveURL']==bridge['archiveURL'] and 'password' not in json.dumps(cfg)
    for bad in ['..%2Fconfig.json','.checksums.json','nicht-da.zip']:c.call('bridge-file&name='+bad,expected=400 if bad.startswith('.') or '%2F' in bad else 404)
    customer=c.call('share',{'folder':root,'role':'view'});cust=Client(a.base);cust.call('share-login',{'token':customer['token']});cust.call('bridge',expected=403);cust.call('bridge-config',expected=403);c.call('revoke',{'id':customer['id']})
    print('PASS: bridge download listing, config without secrets, filename validation, customer denial')
    c.call('settings',{'authorName':''})
    if a.fixture_dir:
        a.fixture_dir.mkdir(parents=True,exist_ok=True);(a.fixture_dir/'demo.kmz').write_bytes(raw)
    # Empty project deletion never removes mission data and revokes only its own links.
    empty=c.call('folder',{'name':'Empty deletion demo'})['id']
    child=c.call('folder',{'name':'Child deletion demo','parent':empty})['id']
    c.call('folder-delete',{'id':empty,'name':'Empty deletion demo','parent':None},expected=409)
    c.call('folder-delete',{'id':child,'name':'Stale name','parent':empty},expected=409)
    editlink=c.call('share',{'folder':empty,'role':'edit'});editor=Client(a.base);editor.call('share-login',{'token':editlink['token']})
    editor.call('folder-delete',{'id':child,'name':'Child deletion demo','parent':empty},expected=403)
    c.call('folder-delete',{'id':child,'name':'Child deletion demo','parent':empty})
    c.call('folder-delete',{'id':empty,'name':'Empty deletion demo','parent':None});editor.call('library',expected=401)
    c.call('folder-delete',{'id':sub,'name':'Routen','parent':root},expected=409)
    assert c.call('original&id='+m)==raw2
    print('PASS: empty folder deletion, nonempty/stale rejection, owner-only action, link revocation, originals retained')
    test_layers(c,a,root)
    print('PASS: authentication, folders/cycles, parsing, versions/conflicts, exact KMZ, package hashes, previews, points/conflicts, read/edit scopes, revocation, archive and metadata conflicts')
if __name__=='__main__': main()
