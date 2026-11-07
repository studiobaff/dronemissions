"""GPL-3.0-or-later. Store the archive access key in a credential store, never in a plain text file.

Stores:
- keychain: macOS Keychain via the `security` command (generic password, service DroneMissionsBridge).
- 1password: 1Password CLI `op` (item "Drone Missions Bridge · <host>" in the default vault); needs the CLI
  installed and the desktop-app integration or a signed-in session.
- dpapi: Windows DPAPI (CryptProtectData, current user); the ciphertext lives in the app data folder.
The preferred store is chosen with `preference` ('auto', 'keychain', '1password', 'dpapi'); 'auto' picks the
system store. On other systems nothing is stored and the key stays in memory for the session.
"""
from __future__ import annotations
import base64,hashlib,os,shutil,subprocess,sys,urllib.parse
from pathlib import Path

SERVICE='DroneMissionsBridge'
TITLE='Drone Missions Bridge'
TIMEOUT=25

def available():
 out=[]
 if sys.platform=='darwin':out.append('keychain')
 if os.name=='nt':out.append('dpapi')
 if shutil.which('op'):out.append('1password')
 return out

def backend(preference='auto'):
 stores=available()
 if preference in stores:return preference
 if preference not in ('auto','',None):return None
 return stores[0] if stores else None

def _account(url:str)->str:return 'archive:'+url.strip().lower()
def _title(url:str)->str:
 host=urllib.parse.urlsplit(url.strip()).hostname or url.strip();return f'{TITLE} · {host}'
def _dpapi_path(url:str,root:Path)->Path:return Path(root)/'credentials'/(hashlib.sha256(_account(url).encode()).hexdigest()+'.bin')

def _dpapi(data:bytes,protect:bool)->bytes:
 import ctypes,ctypes.wintypes as wt
 class BLOB(ctypes.Structure):_fields_=[('cbData',wt.DWORD),('pbData',ctypes.POINTER(ctypes.c_char))]
 buf=ctypes.create_string_buffer(data,len(data));inp=BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char)));out=BLOB()
 fn=ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
 if not fn(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out)):raise OSError('DPAPI-Aufruf fehlgeschlagen.')
 try:return ctypes.string_at(out.pbData,out.cbData)
 finally:ctypes.windll.kernel32.LocalFree(out.pbData)

def _op(args,**kw):
 return subprocess.run(['op',*args],capture_output=True,text=True,timeout=TIMEOUT,**kw)

def save(url:str,key:str,root:Path|None=None,preference='auto')->bool:
 kind=backend(preference)
 if kind=='keychain':
  subprocess.run(['security','add-generic-password','-U','-a',_account(url),'-s',SERVICE,'-w',key],check=True,capture_output=True,timeout=TIMEOUT);return True
 if kind=='1password':
  title=_title(url);edit=_op(['item','edit',title,'password='+key,'url='+url.strip()])
  if edit.returncode==0:return True
  create=_op(['item','create','--category=login','--title='+title,'--url='+url.strip(),'password='+key,'notes=Zugangsschlüssel des Drone-Missions-Webarchivs, gespeichert von der Bridge.'])
  if create.returncode!=0:raise OSError('1Password: '+(create.stderr.strip() or 'Eintrag konnte nicht angelegt werden. CLI-Integration in 1Password aktivieren.'))
  return True
 if kind=='dpapi' and root is not None:
  path=_dpapi_path(url,root);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64encode(_dpapi(key.encode('utf-8'),True)));return True
 return False

def load(url:str,root:Path|None=None,preference='auto')->str|None:
 kind=backend(preference)
 try:
  if kind=='keychain':
   r=subprocess.run(['security','find-generic-password','-a',_account(url),'-s',SERVICE,'-w'],capture_output=True,text=True,timeout=TIMEOUT)
   return r.stdout.rstrip('\n') if r.returncode==0 and r.stdout.strip() else None
  if kind=='1password':
   r=_op(['item','get',_title(url),'--fields','label=password','--reveal'])
   return r.stdout.strip() or None if r.returncode==0 else None
  if kind=='dpapi' and root is not None:
   path=_dpapi_path(url,root);return _dpapi(base64.b64decode(path.read_bytes()),False).decode('utf-8') if path.is_file() else None
 except (OSError,subprocess.SubprocessError,ValueError):return None
 return None

def delete(url:str,root:Path|None=None,preference='auto')->None:
 kind=backend(preference)
 try:
  if kind=='keychain':subprocess.run(['security','delete-generic-password','-a',_account(url),'-s',SERVICE],capture_output=True,timeout=TIMEOUT)
  elif kind=='1password':_op(['item','delete',_title(url)])
  elif kind=='dpapi' and root is not None:_dpapi_path(url,root).unlink(missing_ok=True)
 except (OSError,subprocess.SubprocessError):pass
