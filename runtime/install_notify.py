#!/usr/bin/env python3
"""Build/install only the Rust notification helper, never emit or reload a shell."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent

def validate_target(target):
    if not target.is_absolute() or any(p.is_symlink() for p in [target,*target.parents]):
        raise RuntimeError(f'unsafe/symlinked target: {target}')
    if target.exists() and not target.is_file():raise RuntimeError(f'nonregular target: {target}')

def build_runtime(name, capability):
    if not shutil.which('cargo'):raise RuntimeError('Rust 1.96.1 / cargo required; no automatic toolchain installation')
    env={**os.environ,'CARGO_TARGET_DIR':str(HERE/'target')}
    subprocess.run(['cargo','+1.96.1','build','--manifest-path',str(HERE/'Cargo.toml'),'--offline','--locked','--release','--bin',name],env=env,check=True,timeout=180)
    binary=HERE/'target/release'/name
    if binary.is_symlink() or not binary.is_file() or binary.read_bytes()[:4]!=b'\x7fELF':raise RuntimeError('expected compiled Rust ELF')
    version=subprocess.check_output([str(binary),'--version'],text=True,timeout=5).strip()
    if capability not in version:raise RuntimeError('unexpected helper capability')
    return binary

def build_notify():
    return build_runtime('agora-notify','(Rust; x-agora-context)')

def build_pi():
    return build_runtime('session-pi','(Rust; captured launch origin)')

def backup_support():
    spec=importlib.util.spec_from_file_location('single_runtime_backup',HERE/'single_backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def apply():
    target=Path.home()/'.local/bin/agora-notify';validate_target(target)
    base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'linux-setup/notify-upgrades'
    if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup path')
    source=build_notify()
    if target.exists() and target.read_bytes()==source.read_bytes() and target.stat().st_mode&0o777==0o755:
        print('Rust notification helper already current; no reload or notification.');return
    base.mkdir(parents=True,exist_ok=True)
    backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base))
    backup_support().record(backup,target,source)
    if target.exists():shutil.copy2(target,backup/'agora-notify')
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='agora-notify.tmp.',dir=target.parent);os.close(fd)
    try:
        shutil.copyfile(source,name);os.chmod(name,0o755);os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)
    print(f'Private backup: {backup}')
    print('Installed Rust agora-notify only; no desktop/core/Quickshell/Pi reload or notification.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--restore',type=Path);parser.add_argument('--expected-current-sha256');args=parser.parse_args()
    if args.restore is not None:
        os.umask(0o077);backup_support().restore('agora-notify',args.restore,args.expected_current_sha256);return
    if not args.apply:print('Plan: build pinned/locked offline Rust agora-notify; private backup/atomic helper replacement only. No reload or notification. Use --apply.');return
    os.umask(0o077);apply()

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:raise SystemExit(f'Notification helper install stopped: {error}; inspect backup, no automatic rollback/reload')
