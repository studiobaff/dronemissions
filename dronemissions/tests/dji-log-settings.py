"""Private decoder-key setup; synthetic key, no external requests."""
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
from integration import Client

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--access',type=Path,required=True);a=p.parse_args();assert urlparse(a.base).hostname=='127.0.0.1'
 owner=Client(a.base);owner.login(json.loads(a.access.read_text()));action='dji-log-settings'
 anon=Client(a.base);anon.call(action,expected=401)
 initial=owner.call(action);assert not initial['configured'] and initial['cloudSyncReady']
 fake='synthetic-not-a-real-key-12345678';body={'revision':initial['revision'],'apiKey':fake}
 saved=owner.call(action,body);assert saved['configured'] and fake not in json.dumps(saved)
 assert fake not in json.dumps(owner.call(action));assert fake not in json.dumps(owner.call('library'))
 owner.call(action,body,expected=409)
 owner.call(action,{'revision':saved['revision'],'apiKey':'bad key'},expected=400)
 folder=owner.call('folder',{'name':'DJI setup access test'})['id']
 for role in ['view','edit']:
  guest=Client(a.base);guest.call('share-login',{'token':owner.call('share',{'folder':folder,'role':role})['token']});guest.call(action,expected=403);guest.call(action,{'revision':saved['revision'],'apiKey':None},expected=403)
 token=owner.csrf;owner.csrf='invalid';owner.call(action,{'revision':saved['revision'],'apiKey':None},expected=403);owner.csrf=token
 cleared=owner.call(action,{'revision':saved['revision'],'apiKey':None});assert not cleared['configured']
 assert not owner.call(action)['configured'];owner.call('logout',{})
 print('PASS: DJI decoder key storage/status, no disclosure, CAS, CSRF, owner-only access and removal. No cloud request.')

if __name__=='__main__':main()
