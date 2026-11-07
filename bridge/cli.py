from __future__ import annotations
import argparse,json,os,sys
from datetime import datetime
from pathlib import Path
from core import Adb,BridgeError,devices,inspect_kmz,plan,apply,atomic_json

def main():
 p=argparse.ArgumentParser(description='Drone Missions Bridge: geprüfte Dateiübertragung, getrennt von DJI-Fly-Sichtbarkeit.')
 p.add_argument('--adb',default=os.environ.get('ADB','adb'));p.add_argument('--serial')
 s=p.add_subparsers(dest='command',required=True);s.add_parser('devices');s.add_parser('list')
 a=s.add_parser('inspect');a.add_argument('kmz',type=Path)
 a=s.add_parser('backup');a.add_argument('directory',type=Path)
 a=s.add_parser('prepare');a.add_argument('kmz',type=Path);a.add_argument('--name',required=True);a.add_argument('--preview',type=Path);a.add_argument('--replace');a.add_argument('--out',type=Path,required=True)
 a=s.add_parser('apply');a.add_argument('plan',type=Path);a.add_argument('--backup',type=Path,required=True);a.add_argument('--fly-closed',action='store_true',required=True)
 args=p.parse_args()
 if args.command=='inspect':
  d=inspect_kmz(args.kmz.read_bytes());d.pop('points');print(json.dumps(d,indent=2));return
 if args.command=='devices':print(json.dumps(devices(args.adb),indent=2));return
 if not args.serial:raise BridgeError('Gerät ausdrücklich mit --serial auswählen.')
 adb=Adb(args.adb,args.serial)
 if args.command=='list':result=adb.list_missions()
 elif args.command=='backup':result=adb.snapshot(args.directory)
 elif args.command=='prepare':result=plan(adb,args.kmz,args.name,args.preview,args.replace);atomic_json(args.out,result);result={k:v for k,v in result.items() if k!='kmz'}
 elif args.command=='apply':result=apply(adb,json.loads(args.plan.read_text()),args.backup);result={k:v for k,v in result.items() if k!='kmz'}
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (BridgeError,OSError,ValueError) as e:print(str(e),file=sys.stderr);sys.exit(1)
