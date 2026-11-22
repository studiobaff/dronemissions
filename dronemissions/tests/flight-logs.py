#!/usr/bin/env python3
"""OpenDroneLog import, matching, version links and access control. Synthetic only."""
import argparse,io,json,csv
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz

def fixture(name='Flown route',imperial=False):
 points=[(16,48),(16.002,48.001),(16.004,48),(16.002,47.999),(16,48)]
 return {'_exportInfo':{'format':'Open DroneLog JSON Export','units':{'distance':'imperial' if imperial else 'metric'}},'flight':{'displayName':name,'startTime':'2026-10-16T13:00:00+02:00','droneModel':'Synthetic Mavic 4','droneSerial':'synthetic-drone','batterySerial':'synthetic-battery','durationSecs':960,'totalDistance':3280.84 if imperial else 1000},'telemetry':{'time':[0,240,480,720,960],'latitude':[p[1] for p in points],'longitude':[p[0] for p in points],'battery':[100,90,80,70,60],'batteryRemainedCapacity':[5000,4500,4000,3500,3000],'isPhoto':[False,True,False,True,False]},'track':[[*p,60] for p in points]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args();assert urlparse(a.base).hostname=='127.0.0.1'
 c=Client(a.base);c.login(json.loads(a.access.read_text()));folder=c.call('folder',{'name':'Synthetic flight logs'})['id'];other=c.call('folder',{'name':'Other flight logs'})['id']
 mid=c.call('upload',{'folder':folder,'name':'Flown route'},files={'kmz':('flight.kmz',synthetic_kmz())})['id']
 mission=next(m for m in c.call('library')['missions'] if m['id']==mid);raw=json.dumps(fixture(imperial=True)).encode()
 def call(action,body=None,content=raw):return c.call(action,{'folder':folder,**(body or {})},files={'file':('flight.json',content)})
 inspected=call('flight-log-inspect');s=inspected['summary'];assert s['durationSeconds']==960 and abs(s['distanceMeters']-1000)<.001 and s['batteryUsedPercent']==40 and s['batteryUsedMah']==2000 and s['photoEvents']==2
 assert inspected['automatic']['id']==mid
 imported=call('flight-log-import',{'mission':'auto'});assert imported['assigned'];lid=imported['id']
 duplicate=call('flight-log-import');assert duplicate['duplicate'] and duplicate['id']==lid
 row=c.call('flight-logs&folder='+folder)['logs'][0];assert row['version']==mission['versionId'] and row['planned']['durationSeconds']>0
 assert len(c.call('flight-log-track&id='+lid)['track'])==5
 # Equivalent CSV: metadata is SI regardless of display-unit columns.
 buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['time_s','lat','lng','battery_percent','battery_remained_capacity_mah','is_photo','metadata']);f=fixture();meta={'format':'Open DroneLog CSV Export','display_name':'Flown route','start_time':f['flight']['startTime'],'drone_serial':'synthetic-drone','battery_serial':'synthetic-battery','duration_secs':960,'total_distance_m':1000}
 for i,t in enumerate(f['telemetry']['time']):writer.writerow([t,f['track'][i][1],f['track'][i][0],f['telemetry']['battery'][i],f['telemetry']['batteryRemainedCapacity'][i],int(f['telemetry']['isPhoto'][i]),json.dumps(meta) if i==0 else ''])
 csvraw=buf.getvalue().encode();assert call('flight-log-inspect',content=csvraw)['summary']['batteryUsedPercent']==40;assert call('flight-log-import',content=csvraw)['duplicate']
 for battery in ([None]*5,[50,40,100,90,80]):
  changed=fixture();changed['telemetry']['battery']=battery;assert call('flight-log-inspect',content=json.dumps(changed).encode())['summary']['batteryUsedPercent'] is None
 malformed=fixture();malformed['telemetry']['time']=[0,240,10,720,960];c.call('flight-log-inspect',{'folder':folder},files={'file':('bad.json',json.dumps(malformed).encode())},expected=400)
 for field,value in [('track',42),('telemetry',{'time':'bad'}),('flight',{'totalDistance':{}})]:
  malformed=fixture();malformed[field]=value;c.call('flight-log-inspect',{'folder':folder},files={'file':('bad.json',json.dumps(malformed).encode())},expected=400)
 # Identical route in another mission makes the automatic match ambiguous.
 second=c.call('upload',{'folder':folder,'name':'Another route'},files={'kmz':('second.kmz',synthetic_kmz(65))})['id'];assert call('flight-log-inspect')['automatic'] is None
 # Snapshot is retained after the mission gains another version.
 c.call('upload',{'mission':mid,'revision':mission['revision']},files={'kmz':('new.kmz',synthetic_kmz(80))})
 assert c.call('flight-logs&folder='+folder)['logs'][0]['version']==mission['versionId']
 assert c.call('flight-log-track&id='+lid)['planned']['points'][0]['height']==60
 c.call('flight-log-link',{'id':lid,'revision':row['revision'],'mission':'','version':''});c.call('flight-log-link',{'id':lid,'revision':row['revision'],'mission':'','version':''},expected=409)
 # Display labels are separate from original telemetry and fingerprint; CAS and enum validation.
 row=c.call('flight-logs&folder='+folder)['logs'][0]
 c.call('flight-log-label',{'id':lid,'revision':row['revision'],'name':'Ebenfurth Nord','captureType':'video'})
 labelled=c.call('flight-logs&geometry=1&folder='+folder)['logs'][0]
 assert labelled['displayName']=='Ebenfurth Nord' and labelled['captureType']=='video'
 assert labelled['summary']==row['summary'] and labelled['filename']==row['filename']
 assert len(labelled['previewSegments'])==5 and 'track' not in labelled
 c.call('flight-log-label',{'id':lid,'revision':row['revision'],'name':'Stale','captureType':'photo'},expected=409)
 c.call('flight-log-label',{'id':lid,'revision':labelled['revision'],'name':'Invalid','captureType':'invented'},expected=400)
 assert call('flight-log-import')['duplicate']
 # Both log and mission need authorization; viewers never see telemetry.
 viewer=Client(a.base);viewer.call('share-login',{'token':c.call('share',{'folder':folder,'role':'view'})['token']})
 outsider=Client(a.base);outsider.call('share-login',{'token':c.call('share',{'folder':other,'role':'edit'})['token']})
 for guest in (viewer,outsider):
  guest.call('flight-logs&folder='+folder,expected=403);guest.call('flight-log-track&id='+lid,expected=403)
  guest.call('flight-log-label',{'id':lid,'revision':labelled['revision'],'name':'Forbidden','captureType':'photo'},expected=403)
  guest.call('flight-log-link',{'id':lid,'revision':2,'mission':mid,'version':mission['versionId']},expected=403)
 outsider.call('flight-log-import',{'folder':other,'mission':mid,'version':mission['versionId']},files={'file':('private.json',raw)},expected=403)
 c.call('logout',{});print('PASS: OpenDroneLog CSV/JSON, SI conversion, battery gaps/reset, dedup, ambiguous match, version snapshot, CAS and scope isolation.')
if __name__=='__main__':main()
