#!/usr/bin/env python3
"""Standalone Rust Pi installer under private HOME; never invoke the launcher."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='r5-install-') as directory:
    root=Path(directory);(root/'.local/bin').mkdir(parents=True)
    target=root/'.local/bin/session-pi';target.write_text('# previous launcher\n');target.chmod(0o700)
    settings=root/'.pi/settings.json';settings.parent.mkdir();settings.write_text('{"personal":true}\n')
    desktop=root/'project/.session-manager/apps/session-pi.desktop';desktop.parent.mkdir(parents=True);desktop.write_text('personal entry\n')
    env={**os.environ,'HOME':str(root),'XDG_STATE_HOME':str(root/'state'),'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    def run(*args):return subprocess.run(['/usr/bin/python3',str(ROOT/'install_pi.py'),*args],env=env,capture_output=True,text=True,timeout=90)
    before=target.read_bytes()
    r=run();assert r.returncode==0 and target.read_bytes()==before and not (root/'state').exists()
    r=run('--apply');assert r.returncode==0,r.stdout+r.stderr
    assert target.read_bytes()==(ROOT/'target/release/session-pi').read_bytes()
    assert target.read_bytes()[:4]==b'\x7fELF' and target.stat().st_mode&0o777==0o755
    backups=list((root/'state/linux-setup/session-pi-upgrades').iterdir());assert len(backups)==1
    assert backups[0].stat().st_mode&0o777==0o700 and (backups[0]/'session-pi').read_bytes()==before
    r=run('--apply');assert r.returncode==0 and len(list((root/'state/linux-setup/session-pi-upgrades').iterdir()))==1
    target.unlink();other=root/'preserve';other.write_text('keep');target.symlink_to(other)
    assert run('--apply').returncode!=0 and other.read_text()=='keep'
    assert settings.read_text()=='{"personal":true}\n' and desktop.read_text()=='personal entry\n'
print('R5 standalone installer: dry run, pinned ELF, private backup, atomic copy, idempotence, symlink refusal and unchanged personal settings/entries passed.')
