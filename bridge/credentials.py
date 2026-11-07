"""GPL-3.0-or-later. Store the archive access key in the operating system's credential store.

macOS: Keychain via the `security` command (generic password, service DroneMissionsBridge).
Windows: DPAPI (CryptProtectData, current user) with the ciphertext kept in QSettings-independent user data.
Other systems: nothing is stored; the key stays in memory for the session.
The key never touches a plain text file.
"""
from __future__ import annotations
import base64,os,subprocess,sys
from pathlib import Path

SERVICE='DroneMissionsBridge'

def backend():
 if sys.platform=='darwin':return 'keychain'
 if os.name=='nt':return 'dpapi'
 return None

def _account(url:str)->str:return 'archive:'+url.strip().lower()

def _dpapi_path(url:str,root:Path)->Path:
 import hashlib;return Path(root)/'credentials'/(hashlib.sha256(_account(url).encode()).hexdigest()+'.bin')

def _dpapi(data:bytes,protect:bool)->bytes:
 import ctypes,ctypes.wintypes as wt
 class BLOB(ctypes.Structure):_fields_=[('cbData',wt.DWORD),('pbData',ctypes.POINTER(ctypes.c_char))]
 buf=ctypes.create_string_buffer(data,len(data));inp=BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char)));out=BLOB()
 fn=ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
 if not fn(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out)):raise OSError('DPAPI-Aufruf fehlgeschlagen.')
 try:return ctypes.string_at(out.pbData,out.cbData)
 finally:ctypes.windll.kernel32.LocalFree(out.pbData)

def save(url:str,key:str,root:Path|None=None)->bool:
 kind=backend()
 if kind=='keychain':
  subprocess.run(['security','add-generic-password','-U','-a',_account(url),'-s',SERVICE,'-w',key],check=True,capture_output=True,timeout=20);return True
 if kind=='dpapi' and root is not None:
  path=_dpapi_path(url,root);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64encode(_dpapi(key.encode('utf-8'),True)));return True
 return False

def load(url:str,root:Path|None=None)->str|None:
 kind=backend()
 try:
  if kind=='keychain':
   r=subprocess.run(['security','find-generic-password','-a',_account(url),'-s',SERVICE,'-w'],capture_output=True,text=True,timeout=20)
   return r.stdout.rstrip('\n') if r.returncode==0 and r.stdout.strip() else None
  if kind=='dpapi' and root is not None:
   path=_dpapi_path(url,root);return _dpapi(base64.b64decode(path.read_bytes()),False).decode('utf-8') if path.is_file() else None
 except (OSError,subprocess.SubprocessError,ValueError):return None
 return None

def delete(url:str,root:Path|None=None)->None:
 kind=backend()
 try:
  if kind=='keychain':subprocess.run(['security','delete-generic-password','-a',_account(url),'-s',SERVICE],capture_output=True,timeout=20)
  elif kind=='dpapi' and root is not None:_dpapi_path(url,root).unlink(missing_ok=True)
 except (OSError,subprocess.SubprocessError):pass
