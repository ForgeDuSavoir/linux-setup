#!/usr/bin/env python3
"""R8 explicit helper returns for R4/R5; no runtime invocation, private HOME only."""
import os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for script,name,folder in [('install_notify.py','agora-notify','notify-upgrades'),('install_pi.py','session-pi','session-pi-upgrades')]:
    with tempfile.TemporaryDirectory(prefix='r8-single-') as d:
        root=Path(d);target=root/'.local/bin'/name;target.parent.mkdir(parents=True);target.write_bytes(b'# old helper');target.chmod(0o700)
        env={**os.environ,'HOME':str(root),'XDG_STATE_HOME':str(root/'state'),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')),'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup'))}
        def run(*args):return subprocess.run(['/usr/bin/python3',str(ROOT/script),*args],env=env,capture_output=True,text=True,timeout=90)
        r=run('--apply');assert r.returncode==0,r.stderr
        backup=next((root/'state/linux-setup'/folder).iterdir());native=target.read_bytes()
        target.write_bytes(b'personal edit');assert run('--restore',str(backup)).returncode!=0 and target.read_bytes()==b'personal edit'
        target.write_bytes(native);r=run('--restore',str(backup));assert r.returncode==0,r.stderr
        assert target.read_bytes()==b'# old helper' and target.stat().st_mode&0o777==0o700
        assert run('--restore',str(backup)).returncode==0
        target.unlink();assert run('--apply').returncode==0
        new=next(p for p in backup.parent.iterdir() if p!=backup);assert run('--restore',str(new)).returncode==0 and not target.exists()
        legacy=root/'legacy';legacy.mkdir(mode=0o700);(legacy/name).write_bytes(b'# historical legacy')
        target.write_bytes(native)
        assert run('--restore',str(legacy)).returncode!=0
        import hashlib
        pinned=hashlib.sha256(native).hexdigest()
        assert run('--restore',str(legacy),'--expected-current-sha256','0'*64).returncode!=0
        assert run('--restore',str(legacy),'--expected-current-sha256',pinned).returncode==0 and target.read_bytes()==b'# historical legacy'
        target.unlink();target.symlink_to(root/'foreign');assert run('--restore',str(backup)).returncode!=0 and not (root/'foreign').exists()
print('R8 R4/R5 manifest returns: original/absent target, idempotence, foreign edit and symlink protection passed.')
