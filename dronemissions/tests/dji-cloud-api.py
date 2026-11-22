"""Real HTTP API + real encrypted binary decoder; only upstream DJI transport is replaced.
Replacement happens in a disposable copy, never through a production test switch.
"""
import argparse,json,os,shutil,socket,subprocess,tempfile,time
from pathlib import Path
from urllib.parse import urlparse
from integration import Client,synthetic_kmz

STUB=r'''
function dm_cloud_http(string $url,?string $body=null,array $headers=[],int $limit=4194304): array {
 $dir=dm_private();$path=parse_url($url,PHP_URL_PATH);parse_str(parse_url($url,PHP_URL_QUERY)??'',$query);
 $reply=fn($data)=>['status'=>200,'headers'=>['content-type'=>'application/json'],'body'=>json_encode($data)];
 if($path==='/apis/apprest/v1/vcode'){$im=imagecreatetruecolor(8,8);ob_start();imagepng($im);$raw=ob_get_clean();return ['status'=>200,'headers'=>['content-type'=>'image/jpeg'],'body'=>$raw];}
 if($path==='/apis/apprest/v1/email_login'){parse_str($body,$form);if(($form['verificationCode']??'')!=='AB12')throw new RuntimeException('DJI rejected synthetic login',401);return $reply(['data'=>['token'=>'synthetic-session-token-123456789']]);}
 if($path==='/flight/record_info_list'){
  if(is_file($dir.'/expire-dji-test'))throw new RuntimeException('DJI expired synthetic session',401);
  if(($query['token']??'')!=='synthetic-session-token-123456789')throw new RuntimeException('DJI bad synthetic token',401);
  return $reply(['data'=>['list'=>[['file_name'=>'SyntheticDJI.txt','start_time'=>'2026-10-16T13:00:00Z','aircraft_name'=>'Synthetic drone','md5'=>str_repeat('a',32)]],'total'=>1]]);
 }
 if($path==='/flight/zipdownload'){
  $count=(int)@file_get_contents($dir.'/dji-download-count');file_put_contents($dir.'/dji-download-count',(string)($count+1));
  return ['status'=>200,'headers'=>['content-type'=>'application/octet-stream'],'body'=>gzcompress(file_get_contents($dir.'/synthetic-dji.txt'))];
 }
 if($path==='/openapi/v1/flight-records/keychains'){
  if(!in_array('Api-Key: synthetic-decoder-key-123456789',$headers,true))throw new RuntimeException('DJI bad synthetic API key',401);
  return $reply(['result'=>['code'=>0],'data'=>json_decode(file_get_contents($dir.'/synthetic-chains.json'),true)]);
 }
 throw new RuntimeException('Unexpected test upstream endpoint');
}
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args();assert urlparse(a.base).hostname=='127.0.0.1'
 root=Path(__file__).resolve().parents[1];private=a.access.parent
 subprocess.run(['node',str(root/'tests/dji-fixture.cjs'),str(private/'synthetic-dji.txt'),str(private/'synthetic-chains.json')],check=True)
 with tempfile.TemporaryDirectory(prefix='dm-dji-web-') as web:
  public=Path(web)/'dronemissions';shutil.copytree(root/'public',public)
  core=public/'dji-cloud-core.php';source=core.read_text();assert 'function dm_cloud_http(' in source
  core.write_text(source.replace('function dm_cloud_http(','function dm_cloud_real_http(')+STUB)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  base=f'http://127.0.0.1:{port}/dronemissions/'
  with (private/'dji-test-server.log').open('w') as log:
   server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',web],env={**os.environ,'DRONEMISSIONS_PRIVATE':str(private)},stdout=log,stderr=log)
   try:
    for _ in range(50):
     try:c=Client(base);break
     except Exception:time.sleep(.1)
    c.login(json.loads(a.access.read_text()));folder=c.call('folder',{'name':'Synthetic cloud destination'})['id']
    mid=c.call('upload',{'folder':folder,'name':'Mission name differs from cloud filename'},files={'kmz':('route.kmz',synthetic_kmz())})['id']
    assert c.call('dji-cloud-status')['decoderReady'];assert not c.call('dji-cloud-status')['connected']
    c.call('dji-cloud-list',{},expected=409)
    challenge=c.call('dji-cloud-captcha',{});assert challenge['image'].startswith('data:image/png;')
    c.call('dji-cloud-login',{'email':'pilot@example.test','password':'synthetic-password','answer':'AB12','challengeId':challenge['challengeId']})
    c.call('dji-cloud-login',{'email':'pilot@example.test','password':'synthetic-password','answer':'AB12','challengeId':challenge['challengeId']},expected=400)
    assert c.call('dji-cloud-status')['connected']
    stored=(private/'dji-cloud/session.json').read_text();assert 'synthetic-session-token' not in stored and 'synthetic-password' not in stored
    listing=c.call('dji-cloud-list',{'page':1});assert listing['done'] and len(listing['records'])==1;rid=listing['records'][0]['id']
    selection=private/'dji-cloud/selection.json'
    import hashlib
    selection.write_text(json.dumps({'account':hashlib.sha256(b'pilot@example.test').hexdigest(),'names':['different drone'],'serials':[]}))
    assert c.call('dji-cloud-list',{'page':1})['records'][0]['selected'] is False
    c.call('dji-cloud-sync',{'id':rid,'folder':folder},expected=409)
    selection.unlink()
    # Missing/incorrect API key must not clear the valid cloud login; downloaded source is retained.
    settings=c.call('dji-log-settings');c.call('dji-log-settings',{'revision':settings['revision'],'apiKey':'wrong-synthetic-key-12345678'})
    c.call('dji-cloud-sync',{'id':rid,'folder':folder},expected=400);assert c.call('dji-cloud-status')['connected']
    settings=c.call('dji-log-settings');c.call('dji-log-settings',{'revision':settings['revision'],'apiKey':'synthetic-decoder-key-123456789'})
    imported=c.call('dji-cloud-sync',{'id':rid,'folder':folder});assert imported['assigned'],imported
    row=c.call('flight-logs&folder='+folder)['logs'][0];assert row['mission']==mid and row['summary']['durationSeconds']==960 and row['summary']['batteryUsedPercent']==40
    duplicate=c.call('dji-cloud-sync',{'id':rid,'folder':folder});assert duplicate['duplicate'] and duplicate['id']==imported['id']
    assert (private/'dji-download-count').read_text()=='1'
    integrity=json.loads(next((private/'dji-cloud').glob('integrity-*.json')).read_text());assert integrity['serverHashKind']=='unknown'
    assert integrity['contentMd5']!=integrity['payloadMd5']
    for role in ['view','edit']:
     guest=Client(base);guest.call('share-login',{'token':c.call('share',{'folder':folder,'role':role})['token']});guest.call('dji-cloud-status',expected=403);guest.call('dji-cloud-sync',{'id':rid},expected=403)
    (private/'expire-dji-test').touch();c.call('dji-cloud-list',{},expected=409);assert not c.call('dji-cloud-status')['connected'];assert c.call('session')['authenticated']
    (private/'expire-dji-test').unlink();assert not (private/'dji-cloud/session.json').exists()
    settings=c.call('dji-log-settings');c.call('dji-log-settings',{'revision':settings['revision'],'apiKey':None})
    c.call('logout',{})
   finally:server.terminate();server.wait()
 print('PASS: mocked DJI login/CAPTCHA/list/download/keychain, real AES v13 decoder, automatic version link, battery/time, retry/dedup, encrypted session, expiry and owner boundaries.')

if __name__=='__main__':main()
