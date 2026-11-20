#!/usr/bin/env python3
"""Install/restore only native thumbnail helper and immutable mask; no image/GUI work."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
ASSET=HERE.parent/'scripts/photocraft-thumbnail/photocraft-thumbnail-mask.zip'
MASK_SHA='ed7ed1e859fcc030c517e12c5ac8d022392cd561d02bf42839fc61f77ef6d720'
NAMES=('photocraft-thumbnail','photocraft-thumbnail-mask.zip')
spec=importlib.util.spec_from_file_location('thumbnail_runtime_builder',HERE/'install_notify.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def atomic(source,target,mode):
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=target.name+'.tmp.',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(source.read_bytes());os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
        os.replace(name,target)
        fd=os.open(target.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:Path(name).unlink(missing_ok=True)

def targets():
    out=[Path.home()/'.local/bin'/name for name in NAMES]
    for p in out:builder.validate_target(p)
    return out

def apply():
    out=targets()
    for tool in ['ffmpeg','ffprobe','photocraft-cli']:
        if not shutil.which(tool):raise RuntimeError(f'{tool} is required; not installing dependencies automatically')
    if ASSET.is_symlink() or digest(ASSET)!=MASK_SHA:raise RuntimeError('versioned reference mask does not match reviewed asset')
    source=builder.build_runtime('photocraft-thumbnail','(Rust; reference mask)')
    sources=[source,ASSET];modes=[0o755,0o644]
    if all(t.exists() and digest(t)==digest(s) and stat.S_IMODE(t.stat().st_mode)==m for s,t,m in zip(sources,out,modes)):
        print('Rust thumbnail helper/mask already current; no image or GUI work.');return
    base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'linux-setup/thumbnail-upgrades'
    if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup path')
    base.mkdir(parents=True,exist_ok=True)
    backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base))
    records={}
    for s,t,m in zip(sources,out,modes):
        records[t.name]={'before':digest(t),'mode':stat.S_IMODE(t.stat().st_mode) if t.exists() else None,'after':digest(s)}
        if t.exists():shutil.copy2(t,backup/t.name)
    (backup/'manifest.json').write_text(json.dumps({'version':1,'files':records})+'\n')
    # Mask first; this is the unchanged reviewed asset shared by old/new helpers.
    # Each replacement is atomic, not a claim of a two-file transaction.
    for s,t,m in reversed(list(zip(sources,out,modes))):
        if not t.exists() or digest(t)!=digest(s) or stat.S_IMODE(t.stat().st_mode)!=m:atomic(s,t,m)
    print(f'Private backup: {backup}')
    print('Installed Rust photocraft-thumbnail and unchanged reference mask only; no GUI/media/terminal/reload.')

def restore(backup):
    if not backup.is_absolute() or any(p.is_symlink() for p in [backup,*backup.parents]):raise RuntimeError('unsafe backup')
    info=backup.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077:raise RuntimeError('backup must be an owned private directory')
    manifest=backup/'manifest.json';builder.validate_target(manifest)
    data=json.loads(manifest.read_text())
    if data.get('version')!=1 or set(data.get('files',{}))!=set(NAMES):raise RuntimeError('invalid backup manifest')
    out=targets()
    for target in out:
        r=data['files'][target.name]
        if digest(target) not in [r['before'],r['after']]:raise RuntimeError('target changed since installation; refusing restore')
        if r['before'] is not None:
            saved=backup/target.name;builder.validate_target(saved)
            if digest(saved)!=r['before'] or type(r['mode']) is not int or not 0<=r['mode']<=0o777:raise RuntimeError('invalid backup contents')
    for target in out:
        r=data['files'][target.name]
        if r['before'] is None:target.unlink(missing_ok=True)
        else:atomic(backup/target.name,target,r['mode'])
    print('Explicit thumbnail helper/mask restore complete; no GUI/media/reload.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--restore',type=Path)
    args=parser.parse_args()
    if not args.apply and args.restore is None:print('Plan: pinned offline Rust build, private backup and atomic thumbnail helper/mask replacement only. Use --apply; --restore ABSOLUTE_BACKUP is explicit. No image/GUI work.');return
    os.umask(0o077)
    if args.restore is not None:restore(args.restore)
    else:apply()

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:raise SystemExit(f'Thumbnail install stopped: {error}; inspect backup, no automatic rollback/reload')
