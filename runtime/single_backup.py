"""Installer-only single-command manifest/restore. Never part of a runtime process."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def validate(path):
    if not path.is_absolute() or any(p.is_symlink() for p in [path,*path.parents]):raise RuntimeError('unsafe restore path')
    if path.exists() and (not path.is_file() or path.stat().st_uid!=os.getuid()):raise RuntimeError('nonregular/foreign restore file')
def record(backup,target,source):
    data={'version':1,'name':target.name,'before':sha(target),'after':sha(source),'mode':stat.S_IMODE(target.stat().st_mode) if target.exists() else None}
    (backup/'manifest.json').write_text(json.dumps(data)+'\n')
def atomic(source,target,mode):
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=target.name+'.tmp.',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(source.read_bytes());os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
        os.replace(name,target)
        directory=os.open(target.parent,os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:Path(name).unlink(missing_ok=True)
def restore(name,backup,expected_current=None):
    if not backup.is_absolute() or any(p.is_symlink() for p in [backup,*backup.parents]):raise RuntimeError('unsafe backup')
    m=backup.stat()
    if not stat.S_ISDIR(m.st_mode) or m.st_uid!=os.getuid() or stat.S_IMODE(m.st_mode)&0o077:raise RuntimeError('owned private backup required')
    manifest=backup/'manifest.json';validate(manifest)
    target=Path.home()/'.local/bin'/name;validate(target)
    if not manifest.exists():
        if expected_current is None or len(expected_current)!=64 or any(c not in '0123456789abcdef' for c in expected_current) or sha(target)!=expected_current:raise RuntimeError('pre-R8 backup requires --expected-current-sha256 with the exact reviewed installed hash; never guess')
        saved=backup/name;validate(saved)
        if not saved.is_file():raise RuntimeError('legacy original missing')
        atomic(saved,target,stat.S_IMODE(saved.stat().st_mode)&0o777)
        print(f'Explicit pinned-hash legacy {name} restore complete; no runtime action.');return
    data=json.loads(manifest.read_text())
    if data.get('version')!=1 or data.get('name')!=name or sha(target) not in [data['before'],data['after']]:raise RuntimeError('foreign later target or invalid manifest; refusing restore')
    if data['before'] is None:target.unlink(missing_ok=True)
    else:
        saved=backup/name;validate(saved)
        if sha(saved)!=data['before'] or type(data['mode']) is not int or not 0<=data['mode']<=0o777:raise RuntimeError('invalid backup bytes/mode')
        atomic(saved,target,data['mode'])
    print(f'Explicit {name} restore complete; no desktop/media/Pi/notification action.')
