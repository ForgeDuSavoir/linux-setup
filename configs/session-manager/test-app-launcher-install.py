#!/usr/bin/env python3
"""Targeted binary install/restore in an owned HOME; no real desktop/service calls."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
INSTALLER=HERE/'install_app_launcher.sh'
with tempfile.TemporaryDirectory(prefix='launcher-install-') as directory:
    home=Path(directory)
    (home/'.local/bin').mkdir(parents=True); (home/'bin').mkdir()
    manager=home/'.local/bin/session-manager'
    manager.write_text('#!/bin/sh\necho "session-manager fixture (protocol 3)"\n'); manager.chmod(0o700)
    for name in ['systemctl','hyprctl','quickshell','rofi','gtk-launch','gio']:
        path=home/'bin'/name
        path.write_text('#!/bin/sh\necho 0\n' if name=='systemctl' else '#!/bin/sh\necho "forbidden desktop invocation" >&2\nexit 19\n')
        path.chmod(0o700)
    target=home/'.local/bin/session-app-launcher'; legacy=b'#!/bin/sh\n# previous owned launcher\nexit 0\n'
    target.write_bytes(legacy); target.chmod(0o700)
    env={'HOME':str(home),'PATH':str(home/'bin')+':/usr/bin:/bin','XDG_RUNTIME_DIR':str(home/'runtime'),
         'XDG_STATE_HOME':str(home/'state'),'CARGO_NET_OFFLINE':'true',
         'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),
         'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    (home/'runtime').mkdir(mode=0o700)
    def install(*args):
        return subprocess.run(['bash',str(INSTALLER),*args],env=env,capture_output=True,text=True,timeout=60)
    result=install('--apply'); assert result.returncode==0,result.stdout+result.stderr
    assert target.read_bytes()[:4]==b'\x7fELF'
    version=subprocess.check_output([str(target),'--version'],env={'PATH':'/nonexistent'},text=True)
    assert 'Rust; project-local usage history v1' in version
    base=home/'state/linux-setup/app-launcher-upgrades'
    backups=list(base.iterdir()); assert len(backups)==1
    assert backups[0].stat().st_mode & 0o777==0o700
    saved=backups[0]/'session-app-launcher'; assert saved.read_bytes()==legacy
    result=install('--restore',str(saved)); assert result.returncode==0,result.stdout+result.stderr
    assert target.read_bytes()==legacy
    assert len(list(base.iterdir()))==2
    untouched=home/'unrelated'; untouched.write_text('keep')
    target.unlink(); target.symlink_to(untouched)
    result=install('--apply'); assert result.returncode!=0
    assert untouched.read_text()=='keep' and target.is_symlink()
print('Rust launcher installer: locked offline build, ELF replacement, private backup, explicit restore and symlink refusal passed; no desktop/application invocation.')
