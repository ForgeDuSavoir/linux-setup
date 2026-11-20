#!/usr/bin/env python3
"""R6 real targeted installers/explicit restore in private HOME, never run GUI."""
import json,os,subprocess,tempfile
from pathlib import Path
from thumbnail_fixture import ROOT,ASSET
with tempfile.TemporaryDirectory(prefix='r6-install-') as d:
    root=Path(d);bin=root/'.local/bin';bin.mkdir(parents=True)
    helper=bin/'photocraft-thumbnail';helper.write_text('# previous Python helper\n');helper.chmod(0o700)
    mask=bin/'photocraft-thumbnail-mask.zip';mask.write_bytes(ASSET.read_bytes());mask.chmod(0o600)
    env={**os.environ,'HOME':str(root),'XDG_STATE_HOME':str(root/'state'),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')),'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup'))}
    def run(*args,normal=False):
        program=['bash',str(ROOT.parent/'scripts/photocraft-thumbnail/install_photocraft-thumbnail.sh')] if normal else ['/usr/bin/python3',str(ROOT/'install_thumbnail.py')]
        return subprocess.run([*program,*args],env=env,capture_output=True,text=True,timeout=120)
    old=helper.read_bytes()
    r=run();assert r.returncode==0 and helper.read_bytes()==old and not (root/'state').exists()
    r=run('--apply');assert r.returncode==0,r.stdout+r.stderr
    assert helper.read_bytes()==(ROOT/'target/release/photocraft-thumbnail').read_bytes()
    assert mask.read_bytes()==ASSET.read_bytes()
    backups=list((root/'state/linux-setup/thumbnail-upgrades').iterdir());assert len(backups)==1
    backup=backups[0];assert backup.stat().st_mode&0o777==0o700 and (backup/helper.name).read_bytes()==old
    r=run(normal=True);assert r.returncode==0,r.stderr
    assert len(list(backup.parent.iterdir()))==1
    # A foreign later edit must not be removed/restored over.
    helper.write_bytes(b'newer user edit')
    assert run('--restore',str(backup)).returncode!=0 and helper.read_bytes()==b'newer user edit'
    helper.write_bytes((ROOT/'target/release/photocraft-thumbnail').read_bytes())
    r=run('--restore',str(backup));assert r.returncode==0,r.stderr
    assert helper.read_bytes()==old and helper.stat().st_mode&0o777==0o700 and mask.stat().st_mode&0o777==0o600
    helper.unlink();helper.symlink_to(root/'foreign')
    r=run('--apply');assert r.returncode!=0 and not (root/'foreign').exists()
    helper.unlink();helper.write_bytes(old);mask.unlink();mask.symlink_to(ASSET)
    r=run('--apply');assert r.returncode!=0 and ASSET.read_bytes()==(backup/mask.name).read_bytes()
print('R6 installers: no-effect plan, ELF/asset, private backup, repeat setup, explicit restore, foreign-edit and symlink protection passed.')
