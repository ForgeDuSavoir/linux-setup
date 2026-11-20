#!/usr/bin/env python3
"""Build/install/explicitly restore the Rust audio helper only; never run FilmCraft."""
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
NAME='filmcraft-patch-desktop-audio'
spec=importlib.util.spec_from_file_location('audio_runtime_builder',HERE/'install_notify.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def atomic(source,target,mode):
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=NAME+'.tmp.',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(source.read_bytes());os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
        os.replace(name,target)
        fd=os.open(target.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:Path(name).unlink(missing_ok=True)
def target():
    p=Path.home()/'.local/bin'/NAME;builder.validate_target(p);return p
def apply():
    dest=target()
    for tool in ['ffmpeg','ffprobe','filmcraft-cli']:
        if not shutil.which(tool):raise RuntimeError(f'{tool} required; no automatic package installation')
    source=builder.build_runtime(NAME,'(Rust; exact stereo stream)')
    if dest.exists() and sha(dest)==sha(source) and stat.S_IMODE(dest.stat().st_mode)==0o755:
        print('Rust FilmCraft audio helper already current; no media/GUI work.');return
    base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'linux-setup/filmcraft-audio-upgrades'
    if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup path')
    base.mkdir(parents=True,exist_ok=True);backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base))
    data={'version':1,'before':sha(dest),'after':sha(source),'mode':stat.S_IMODE(dest.stat().st_mode) if dest.exists() else None}
    if dest.exists():shutil.copy2(dest,backup/NAME)
    (backup/'manifest.json').write_text(json.dumps(data)+'\n')
    atomic(source,dest,0o755)
    print(f'Private backup: {backup}')
    print('Installed native FilmCraft audio helper only; no project/media/GUI/terminal/notification/reload.')
def restore(backup):
    if not backup.is_absolute() or any(p.is_symlink() for p in [backup,*backup.parents]):raise RuntimeError('unsafe backup')
    m=backup.stat()
    if not stat.S_ISDIR(m.st_mode) or m.st_uid!=os.getuid() or stat.S_IMODE(m.st_mode)&0o077:raise RuntimeError('owned private backup required')
    manifest=backup/'manifest.json';builder.validate_target(manifest)
    data=json.loads(manifest.read_text());dest=target()
    if data.get('version')!=1 or sha(dest) not in [data['before'],data['after']]:raise RuntimeError('target changed since install; refusing restore')
    if data['before'] is None:dest.unlink(missing_ok=True)
    else:
        saved=backup/NAME;builder.validate_target(saved)
        if sha(saved)!=data['before'] or type(data['mode']) is not int or not 0<=data['mode']<=0o777:raise RuntimeError('invalid backup')
        atomic(saved,dest,data['mode'])
    print('Explicit helper restore complete; no project/media/GUI work.')
def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--restore',type=Path);args=p.parse_args()
    if not args.apply and args.restore is None:print('Plan: pinned/locked offline Rust build, private backup and atomic helper replacement only. Use --apply or --restore ABSOLUTE_BACKUP. No media/GUI work.');return
    os.umask(0o077)
    if args.restore is not None:restore(args.restore)
    else:apply()
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:raise SystemExit(f'FilmCraft helper installation stopped: {error}; inspect backup, no automatic rollback/reload')
