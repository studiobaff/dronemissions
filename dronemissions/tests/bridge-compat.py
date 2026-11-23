#!/usr/bin/env python3
"""Synthetic end-to-end check of the Bridge round trip against the current web code: unchanged Bridge 0.6.2 HTTP client
(tests/fixtures/bridge062), revocable device key, mission BRIDGE-KOMPATIBILITAETSTEST. Only a disposable test
installation; no real keys, no private flight data. Key values are never printed. Kept separate from device-access.py so
the archive contract the Bridge relies on (login, library, upload, missions-move, original, preview) stays visible when the
web app changes, e.g. for the planned QR/short-code download."""
import sys, json, io, zipfile, tempfile, sqlite3, hashlib, subprocess
from pathlib import Path
from integration import Client
sys.path.insert(0,str(Path(__file__).parent/'fixtures/bridge062'))
from archive import ArchiveClient
from core import BridgeError

NAME='BRIDGE-KOMPATIBILITAETSTEST'

def test_kmz():
    """Four waypoints, photo action per waypoint, synthetic coordinates in the Danube basin (no real mission)."""
    points=[(16.3700,48.2080),(16.3705,48.2082),(16.3710,48.2080),(16.3705,48.2078)]
    marks=''.join(f'<Placemark><Point><coordinates>{lng},{lat}</coordinates></Point><wpml:index>{i}</wpml:index><wpml:executeHeight>{50+i*2}</wpml:executeHeight><wpml:waypointSpeed>4</wpml:waypointSpeed><wpml:waypointHeadingParam><wpml:waypointHeadingMode>followWayline</wpml:waypointHeadingMode></wpml:waypointHeadingParam><wpml:actionGroup><wpml:actionGroupId>{i}</wpml:actionGroupId><wpml:actionGroupStartIndex>{i}</wpml:actionGroupStartIndex><wpml:actionGroupEndIndex>{i}</wpml:actionGroupEndIndex><wpml:action><wpml:actionId>0</wpml:actionId><wpml:actionActuatorFunc>takePhoto</wpml:actionActuatorFunc></wpml:action></wpml:actionGroup></Placemark>' for i,(lng,lat) in enumerate(points))
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('wpmz/template.kml',f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><wpml:author>synthetic</wpml:author><wpml:missionConfig><wpml:droneInfo><wpml:droneEnumValue>99</wpml:droneEnumValue><wpml:droneSubEnumValue>0</wpml:droneSubEnumValue></wpml:droneInfo></wpml:missionConfig><Folder><name>{NAME}</name></Folder></Document></kml>')
        z.writestr('wpmz/waylines.wpml',f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><Folder><wpml:templateId>0</wpml:templateId><wpml:waylineId>0</wpml:waylineId><wpml:autoFlightSpeed>4</wpml:autoFlightSpeed><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>{marks}</Folder></Document></kml>')
    return buf.getvalue()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def expect_error(fn, fragment):
    try: fn()
    except BridgeError as e:
        assert fragment in str(e), (fragment, str(e)); return
    raise AssertionError('expected BridgeError containing '+fragment)

def main():
    base, access_path, private = sys.argv[1:]
    owner=Client(base); owner.login(json.loads(Path(access_path).read_text()))
    project=owner.call('folder',{'name':'Bridge-Testprojekt'})['id']
    other=owner.call('folder',{'name':'Bridge-Testprojekt B'})['id']
    key=owner.call('device-key-create',{'name':'Kompatibilitaetstest'})
    # 1 Geräteanmeldung: Browser-Login (E-Mail-Code) und Geräteschlüssel bleiben getrennt.
    bridge=ArchiveClient(base)
    expect_error(lambda: bridge.login('legacy-shared-password'), 'Geräteschlüssel')
    login=bridge.login(key['token']); assert login.get('role')=='device', login
    bridge.library(); assert bridge.role=='editor' and any(f['id']==project for f in bridge.folders)
    # 2 Sichern wie desktop.save_to_archive: upload(label, label+'.kmz', raw, folder, preview)
    raw=test_kmz()
    preview=subprocess.check_output(['php','-r','$i=imagecreatetruecolor(64,32);imagejpeg($i);'])
    saved=bridge.upload(NAME,NAME+'.kmz',raw,project,preview); assert saved.get('version')==1, saved
    # 3 im richtigen Projekt wiederfinden, Name/Dateiname/Metadaten
    m=next(x for x in bridge.missions if x['id']==saved['id'])
    assert m['folderId']==project and m['folder']=='Bridge-Testprojekt', m['folder']
    assert m['name']==NAME and m['filename']==NAME+'.kmz' and m['sha256']==sha(raw) and m['bytes']==len(raw)
    assert m['waypoints']==4 and abs(float(m['distance'])-129.6)<0.5 and m['format']=='KMZ' and m['transferable']
    assert bridge.find_by_sha(sha(raw))['id']==saved['id']
    image,ctype=bridge.preview(m); assert image.startswith(b'\xff\xd8') and 'image/jpeg' in ctype
    # 4 herunterladen: bytegleich, ZIP intakt, WPML lesbar
    with tempfile.TemporaryDirectory() as tmp:
        back=bridge.download(m,Path(tmp)/(NAME+'.kmz')).read_bytes()
    assert back==raw
    with zipfile.ZipFile(io.BytesIO(back)) as z:
        assert z.testzip() is None and {'wpmz/template.kml','wpmz/waylines.wpml'}<=set(z.namelist())
        assert NAME.encode() in z.read('wpmz/template.kml') and b'<wpml:index>3</wpml:index>' in z.read('wpmz/waylines.wpml')
    # 5 erneutes Sichern derselben Datei in ein anderes Projekt: verschieben statt duplizieren
    matches=bridge.matches_by_sha(sha(raw)); assert len(matches)==1
    moved=bridge.move_existing(matches[0],other); assert moved['folderId']==other and len(bridge.matches_by_sha(sha(raw)))==1
    back_home=bridge.move_existing(moved,project); assert back_home['folderId']==project
    # 6 Fehlerbehandlung bleibt lesbar; keine stillen Erfolge
    expect_error(lambda: bridge.upload(NAME,NAME+'.kmz',raw,'does-not-exist'), 'Projektordner')
    expect_error(lambda: bridge.upload(NAME,'plan.csv',b'latitude,longitude\n',project), 'KMZ')
    expect_error(lambda: bridge.move_existing({**back_home,'revision':1},other), 'geändert')
    for action in ['settings','shares','device-keys','bridge','bridge-config','versions&id='+m['id']]:
        expect_error(lambda a=action: bridge._request(a), 'Gerätezugang')
    # 7 Ablage: Hash statt Schlüssel, Blob unter Prüfsumme
    with sqlite3.connect(Path(private)/'missions.sqlite') as db:
        row=db.execute('SELECT token_hash FROM device_keys WHERE id=?',(key['id'],)).fetchone(); assert row and row[0]==sha(key['token'].encode())
        assert db.execute('SELECT filename,sha256,bytes FROM versions WHERE mission=?',(saved['id'],)).fetchone()==(NAME+'.kmz',sha(raw),len(raw))
    assert (Path(private)/'blobs'/(sha(raw)+'.kmz')).read_bytes()==raw
    # 8 Widerruf beendet die laufende Bridge-Sitzung
    owner.call('device-key-revoke',{'id':key['id']})
    expect_error(bridge.library, 'widerrufen')
    print('PASS: BRIDGE-KOMPATIBILITAETSTEST – device key login, save into project, metadata, byte-identical download, move instead of duplicate, readable errors, hash-only key storage, revocation.')

if __name__=='__main__': main()
