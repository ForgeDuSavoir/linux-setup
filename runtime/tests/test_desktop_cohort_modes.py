#!/usr/bin/env python3
"""R8 offline provisioning, new-login acceptance, reduced updates and fail-closed state."""
import json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from cohort_fixture import Fixture,ROOT,installer
with tempfile.TemporaryDirectory(prefix='r8-modes-') as d:
    f=Fixture(Path(d));f.env.pop('HYPRLAND_INSTANCE_SIGNATURE');f.state.unlink();f.marker.unlink()
    try:
        # Explicit offline only: no initialized marker/metadata/daemon lifecycle.
        f.run('--apply','--offline')
        assert not f.state.exists() and not f.marker.exists()
        assert (f.root/'.config/hypr/inputs.lua').is_file()
        offline_backup=f.backups()[0]
        f.env['HYPRLAND_INSTANCE_SIGNATURE']='login-one';f.start()
        # Stop the synthetic bar. Test only, never touches a user process.
        subprocess.run(['quickshell','kill','--pid',(f.root/'qs.pid').read_text()],env=f.env,check=True)
        before_clients=json.loads((f.root/'world').read_text())['clients']
        startup=f.root/'.local/bin/session-startup'
        r=subprocess.run([str(startup)],env=f.env,capture_output=True,text=True,timeout=8);assert r.returncode==0,r.stderr
        first=f.core('list');sid=first['active_session_id'];assert len(first['sessions'])==1 and first['sessions'][0]['source']=={'kind':'neutral'}
        calls=(f.root/'qs.calls').read_text()
        assert subprocess.run([str(startup)],env=f.env,capture_output=True,timeout=5).returncode==0
        assert f.core('list')==first and (f.root/'qs.calls').read_text()==calls
        f.core('start','--project','P')
        f.env['HYPRLAND_INSTANCE_SIGNATURE']='login-two'
        assert subprocess.run([str(startup)],env=f.env,capture_output=True,timeout=8).returncode==0
        second=f.core('list');assert len(second['sessions'])==1 and second['active_session_id']!=sid
        assert json.loads((f.root/'world').read_text())['clients']==before_clients
        # Existing native startup-only update switches four ELFs as one generation.
        f.shell_start();f.reap()
        shell=f.root/'.config/quickshell/shell.qml';qml=shell.read_bytes();pid=(f.root/'qs.pid').read_text();calls=(f.root/'qs.calls').read_text()
        metadata=f.state.read_bytes();logical=f.core('list');marker=f.marker.read_bytes()
        original_files=installer.files
        def changed_files():
            assets=original_files();name='.config/hypr/startup.lua'
            data,mode=assets[name];assets[name]=(data+b'\n-- synthetic new generation\n',mode);return assets
        with patch.dict(os.environ,f.env,clear=True),patch.object(installer,'files',side_effect=changed_files):
            installer.apply(reduced='startup')
        updated=next(p for p in f.backups() if p!=offline_backup)
        assert shell.read_bytes()==qml and (f.root/'qs.pid').read_text()==pid and (f.root/'qs.calls').read_text()==calls
        assert f.state.read_bytes()==metadata and f.marker.read_bytes()==marker and f.core('list')==logical
        f.run('--restore',str(updated))
        assert shell.read_bytes()==qml and (f.root/'qs.pid').read_text()==pid
        f.run('--restore',str(updated)) # Idempotent, including no shell stop.
        assert (f.root/'qs.calls').read_text()==calls
        # Malformed metadata/marker: refuse before stopping the known bar.
        for target,bad in [(f.marker,b''),(f.marker,b'{"version":1,"phase":"unknown"}'),(f.state,b'{"version":2}')]:
            saved=target.read_bytes();target.write_bytes(bad)
            f.run('--apply','--allow-notification-history-reset',ok=False)
            assert target.read_bytes()==bad and (f.root/'qs.calls').read_text()==calls
            target.write_bytes(saved)
        # Failed same-login marker must survive a configuration update/no-op exactly.
        failed={'version':1,'instance':'login-two','phase':'failed','error':'synthetic','keep':True}
        f.marker.write_text(json.dumps(failed));raw=f.marker.read_bytes()
        f.run('--apply','--allow-notification-history-reset')
        assert f.marker.read_bytes()==raw
        # Config symlinks and foreign public links are not followed or overwritten.
        original=shell.read_bytes();shell.unlink();foreign=f.root/'personal';foreign.write_bytes(original);shell.symlink_to(foreign)
        f.run('--apply','--allow-notification-history-reset',ok=False);assert shell.is_symlink() and foreign.read_bytes()==original
        shell.unlink();shell.write_bytes(original)
        public=f.root/'.local/bin/session-desktop';expected=os.readlink(public);public.unlink();public.symlink_to('/usr/bin/true')
        f.run('--apply','--movement-only',ok=False);assert os.readlink(public)=='/usr/bin/true'
        public.unlink();public.symlink_to(expected)
        f.run('--apply','--movement-only')
        assert shell.read_bytes()==original and (f.root/'qs.pid').read_text()==pid
    finally:f.close()
print('R8 offline/native modes: fresh/same/new login with real private core, no adoption/app restore, atomic generation startup update, idempotent reduced restore, invalid state/marker and personal symlink guards passed.')
