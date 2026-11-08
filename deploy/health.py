import json,sys,time,urllib.request

def verify(base, commit):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(base+'release.json?expected='+commit,timeout=15) as r: data=json.load(r)
            if data['commit']!=commit: raise RuntimeError('Release SHA differs')
            with urllib.request.urlopen(base,timeout=15) as r:
                if r.status!=200: raise RuntimeError('Homepage unavailable')
            return
        except Exception:
            if attempt==3: raise
            time.sleep(2)
if __name__=='__main__': verify(*sys.argv[1:])
