"""Build an allowlisted release; never archive the repository or private state."""
import hashlib,json,re,sys,zipfile
from pathlib import Path

def package(source, destination, commit):
    if not re.fullmatch(r'[0-9a-f]{40}',commit): raise ValueError('Expected full Git commit SHA')
    source=Path(source); files={}
    for p in sorted(source.rglob('*')):
        if p.is_symlink(): raise ValueError('Symlinks are not allowed')
        if not p.is_file(): continue
        name=p.relative_to(source).as_posix()
        if any(part.startswith('.') for part in p.relative_to(source).parts) or p.suffix.lower() not in {'.php','.js','.css','.html','.png','.jpg','.jpeg','.svg','.webp','.ico','.woff','.woff2'} and name not in {'vendor/leaflet-LICENSE','vendor/fonts/DejaVu-LICENSE'}:
            raise ValueError('Unexpected public file: '+name)
        if p.name.lower()=='config.json': raise ValueError('Private configuration in public directory')
        files[name]=p.read_bytes()
    for name in ('index.php','api.php','lib.php','view.html','app.js','style.css'):
        if name not in files: raise ValueError('Missing '+name)
    manifest={'commit':commit,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items(): z.writestr(n,b)
        z.writestr('release.json',json.dumps(manifest,sort_keys=True))
    return manifest
if __name__=='__main__': package(*sys.argv[1:])
