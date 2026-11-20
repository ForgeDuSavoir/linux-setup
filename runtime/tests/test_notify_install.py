#!/usr/bin/env python3
"""Real standalone Rust helper installer in private HOME, no desktop/bus."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='r4-install-') as directory:
    root=Path(directory);(root/'.local/bin').mkdir(parents=True)
    target=root/'.local/bin/agora-notify';target.write_text('# previous helper\n');target.chmod(0o700)
    env={**os.environ,'HOME':str(root),'XDG_STATE_HOME':str(root/'state'),
         'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),
         'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    def run(*args):
        return subprocess.run(['/usr/bin/python3',str(ROOT/'install_notify.py'),*args],env=env,text=True,capture_output=True,timeout=90)
    before=target.read_bytes();r=run();assert r.returncode==0 and target.read_bytes()==before and not (root/'state').exists()
    r=run('--apply');assert r.returncode==0,r.stdout+r.stderr
    assert target.read_bytes()==(ROOT/'target/release/agora-notify').read_bytes()
    assert target.read_bytes().startswith(b'\x7fELF') and target.stat().st_mode&0o777==0o755
    backups=list((root/'state/linux-setup/notify-upgrades').iterdir());assert len(backups)==1
    assert backups[0].stat().st_mode&0o777==0o700 and (backups[0]/'agora-notify').read_bytes()==before
    r=run('--apply');assert r.returncode==0 and len(list((root/'state/linux-setup/notify-upgrades').iterdir()))==1
    target.unlink();other=root/'preserve';other.write_text('keep');target.symlink_to(other)
    r=run('--apply');assert r.returncode!=0 and other.read_text()=='keep'
    print('R4 installer: dry run, pinned ELF build, private backup, atomic copy, idempotence and symlink refusal passed; no notification or reload.')
