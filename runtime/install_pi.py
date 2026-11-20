#!/usr/bin/env python3
"""Build/install only the Rust session Pi launcher, never launch Pi or reload."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_notify_builder',HERE/'install_notify.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def apply():
    target=Path.home()/'.local/bin/session-pi';builder.validate_target(target)
    base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'linux-setup/session-pi-upgrades'
    if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup path')
    source=builder.build_pi()
    if target.exists() and target.read_bytes()==source.read_bytes() and target.stat().st_mode&0o777==0o755:
        print('Rust Pi launcher already current; no launch or reload.');return
    base.mkdir(parents=True,exist_ok=True);backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base))
    builder.backup_support().record(backup,target,source)
    if target.exists():shutil.copy2(target,backup/'session-pi')
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='session-pi.tmp.',dir=target.parent);os.close(fd)
    try:shutil.copyfile(source,name);os.chmod(name,0o755);os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)
    print(f'Private backup: {backup}')
    print('Installed Rust session-pi only; no terminal/model/Pi/desktop/core/Quickshell launch or reload.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--restore',type=Path);parser.add_argument('--expected-current-sha256');args=parser.parse_args()
    if args.restore is not None:
        os.umask(0o077);builder.backup_support().restore('session-pi',args.restore,args.expected_current_sha256);return
    if not args.apply:print('Plan: pinned/locked offline Rust build, private backup and atomic session-pi replacement only. No launch or reload. Use --apply.');return
    os.umask(0o077);apply()

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:raise SystemExit(f'Pi launcher installation stopped: {error}; inspect backup, no automatic rollback/reload')
