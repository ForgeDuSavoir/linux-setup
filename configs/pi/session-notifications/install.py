#!/usr/bin/env python3
"""Targeted Pi notification extension/helper update; never reload Pi or Quickshell."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
CONFIGS = HERE.parents[1]


def validate_path(path):
    if not path.is_absolute() or any(item.is_symlink() for item in [path, *path.parents]):
        raise RuntimeError(f'unsafe/symlinked installation path: {path}')
    if path.exists() and not path.is_file():
        raise RuntimeError(f'nonregular target: {path}')


def pi_package():
    command = shutil.which('pi')
    if not command:
        raise RuntimeError('install Pi before its notification extension')
    for directory in Path(command).resolve().parents:
        types = directory / 'dist/core/extensions/types.d.ts'
        if types.is_file():
            if 'type: "agent_settled"' not in types.read_text():
                raise RuntimeError('this Pi does not expose agent_settled; update Pi explicitly first')
            return directory
    raise RuntimeError('cannot confirm agent_settled support in this Pi distribution')


def apply():
    pi_package()  # Read-only capability check; no package install/update or credential access.
    home = Path.home()
    agent = Path(os.environ.get('PI_CODING_AGENT_DIR') or home / '.pi/agent')
    mappings = [
        (HERE / 'index.ts', agent / 'extensions/agora-notifications/index.ts', 0o644),
    ]
    launcher = home / '.local/bin/session-pi'
    if launcher.exists() or launcher.is_symlink():
        validate_path(launcher)
        subprocess.run(['bash', '-c', 'source "$1"; session_manager_require_v3', 'bash',
                        str(CONFIGS / 'session-manager/require_protocol_v3.sh')], check=True, timeout=10)
    for source, target, _ in mappings:
        validate_path(target)
        if not source.is_file():
            raise RuntimeError(f'missing source: {source}')
    base = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'linux-setup/pi-notifications'
    if not base.is_absolute() or any(item.is_symlink() for item in [base, *base.parents]):
        raise RuntimeError('unsafe private backup path')
    notify_target=home / '.local/bin/agora-notify'
    validate_path(notify_target)
    builder=CONFIGS.parent / 'runtime/install_notify.py'
    spec=importlib.util.spec_from_file_location('rust_notify_installer',builder)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    mappings.insert(1,(module.build_notify(),notify_target,0o755))
    if launcher.exists():
        mappings.append((module.build_pi(),launcher,0o755))
    base.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'), dir=base))
    for source, target, mode in mappings:
        if (target.is_file() and source.read_bytes() == target.read_bytes()
                and stat.S_IMODE(target.stat().st_mode) == mode):
            continue
        if target.exists():
            saved = backup / target.relative_to(home) if target.is_relative_to(home) else backup / 'custom-agent' / target.name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=target.name + '.tmp.', dir=target.parent)
        os.close(fd)
        try:
            shutil.copyfile(source, temporary)
            os.chmod(temporary, mode)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    print(f'Private backup: {backup}')
    print('Pi completion extension/helper installed; no current task, model, session or shell restarted.')
    print('New Pi instances load it automatically. In an existing idle Pi, run /reload explicitly.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Plan: verify Pi agent_settled support; back up/install only the Agora notification extension/helper and existing session-pi launcher. No reload or notification. Use --apply.')
        return
    os.umask(0o077)
    apply()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Pi notification installation stopped: {error}; no automatic rollback/reload')
