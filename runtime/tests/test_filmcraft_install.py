#!/usr/bin/env python3
"""R7 helper setup/restore under private HOME; no actual media/helper actions."""
import os,subprocess,tempfile
from pathlib import Path
from filmcraft_fixture import ROOT,BIN
NAME='filmcraft-patch-desktop-audio'
with tempfile.TemporaryDirectory(prefix='r7-install-') as d:
    root=Path(d);bin=root/'.local/bin';bin.mkdir(parents=True);target=bin/NAME
    target.write_bytes(b'# old Python helper\n');target.chmod(0o700);old=target.read_bytes()
    env={**os.environ,'HOME':str(root),'XDG_STATE_HOME':str(root/'state'),'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    def run(*args,normal=False):
        command=['bash',str(ROOT.parent/'scripts/filmcraft-patch-desktop-audio/install_filmcraft-patch-desktop-audio.sh')] if normal else ['/usr/bin/python3',str(ROOT/'install_filmcraft_audio.py')]
        return subprocess.run([*command,*args],env=env,capture_output=True,text=True,timeout=120)
    result=run();assert result.returncode==0 and target.read_bytes()==old and not (root/'state').exists()
    result=run('--apply');assert result.returncode==0,result.stdout+result.stderr
    assert target.read_bytes()==BIN.read_bytes() and target.stat().st_mode&0o777==0o755
    backups=list((root/'state/linux-setup/filmcraft-audio-upgrades').iterdir());assert len(backups)==1
    backup=backups[0];assert backup.stat().st_mode&0o777==0o700 and (backup/NAME).read_bytes()==old
    assert run(normal=True).returncode==0 and len(list(backup.parent.iterdir()))==1
    target.write_bytes(b'foreign edit');assert run('--restore',str(backup)).returncode!=0 and target.read_bytes()==b'foreign edit'
    target.write_bytes(BIN.read_bytes());result=run('--restore',str(backup));assert result.returncode==0,result.stderr
    assert target.read_bytes()==old and target.stat().st_mode&0o777==0o700
    target.unlink();target.symlink_to(root/'foreign')
    assert run('--apply').returncode!=0 and not (root/'foreign').exists()
    target.unlink();result=run('--apply');assert result.returncode==0,result.stderr
    newest=next(p for p in backup.parent.iterdir() if p!=backup)
    assert run('--restore',str(newest)).returncode==0 and not target.exists()
    # Consumer message must not incorrectly promise an unchanged project after
    # an uncertain exchange. Install without truncating a running old descriptor.
    consumer=bin/'pre-edit';consumer.write_bytes(b'old consumer');old_fd=consumer.open('rb')
    installer=ROOT.parent/'scripts/pre-edit/install_pre-edit.sh'
    r=subprocess.run(['bash',str(installer)],env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
    assert old_fd.read()==b'old consumer';old_fd.close()
    assert consumer.read_bytes()==(ROOT.parent/'scripts/pre-edit/pre-edit.sh').read_bytes()
    assert b'publication incertaine' in consumer.read_bytes()
    consumer_backups=list((root/'state/linux-setup/pre-edit-upgrades').iterdir());assert len(consumer_backups)==1
    assert (consumer_backups[0]/'pre-edit').read_bytes()==b'old consumer'
    assert subprocess.run(['bash',str(installer)],env=env,capture_output=True).returncode==0 and len(list(consumer_backups[0].parent.iterdir()))==1
    consumer.unlink();consumer.symlink_to(root/'foreign')
    assert subprocess.run(['bash',str(installer)],env=env,capture_output=True).returncode!=0
print('R7 installer: plan, pinned ELF, private backup, normal repeat route, explicit restore (old/absent), foreign edits and symlink refusal passed.')
