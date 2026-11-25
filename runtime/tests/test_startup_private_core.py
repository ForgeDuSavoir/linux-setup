#!/usr/bin/env python3
"""R3 first/repeated/new login with real v3 core in private HOME; fake bar/native."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from desktop_fixture import initial
from test_startup_parity import BIN,ROOT
from test_desktop_parity import BIN as DESKTOP

CORE=Path.home()/'.local/bin/session-manager'
assert subprocess.check_output([str(CORE),'--version'],text=True).strip().endswith('(protocol 3)')
with tempfile.TemporaryDirectory(prefix='r3-private-core-') as directory:
    root=Path(directory)
    for path in ['config/session-manager','run/hyprland','state','data','projects/P','bin']:(root/path).mkdir(parents=True,exist_ok=True)
    (root/'run').chmod(0o700)
    (root/'config/session-manager/config-v2.toml').write_text('schema_version=2\nproject_source='+json.dumps(str(root/'projects'))+'\n')
    world=initial((),None);world['instance']='one';world['active']=1
    file=root/'world';file.write_text(json.dumps(world))
    for name,kind in [('hyprctl','native'),('logger','log'),('quickshell','bar')]:
        target=root/'bin'/name;target.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom startup_fixture import cli\ncli('+repr(kind)+')\n');target.chmod(0o700)
    env={'HOME':str(root),'XDG_CONFIG_HOME':str(root/'config'),'XDG_STATE_HOME':str(root/'state'),'XDG_DATA_HOME':str(root/'data'),'XDG_DATA_DIRS':str(root/'data'),'XDG_RUNTIME_DIR':str(root/'run'),'PATH':str(root/'bin')+':/usr/bin:/bin','DESKTOP_WORLD':str(file),'SESSION_MANAGER_BIN':str(CORE),'HYPRLAND_INSTANCE_SIGNATURE':'one','PYTHONDONTWRITEBYTECODE':'1'}
    def core(*args):return json.loads(subprocess.check_output([str(CORE),'--json','session',*args],env=env,text=True))
    def startup(ok=True):
        result=subprocess.run([str(BIN)],env=env,capture_output=True,text=True,timeout=8)
        assert (result.returncode==0)==ok,(result.stdout,result.stderr)
    daemon=subprocess.Popen([str(CORE),'daemon'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+8
        while not (root/'run/session-manager/ipc-v3.sock').exists():
            assert daemon.poll() is None;assert time.monotonic()<deadline;time.sleep(.02)
        a=core('start','--project','P')['session']['id'];b=core('start','--neutral')['session']['id']
        metadata=root/'run/hyprland/workspace-columns.json'
        metadata.write_text(json.dumps({'version':3,'order':[1,3],'owners':{'1':a,'3':b},'preferred':{},'next_id':40}))
        before_clients=json.loads(file.read_text())['clients']
        startup();first=core('list');assert first['sessions']==[] and first['active_session_id'] is None
        assert set(json.loads(metadata.read_text())['owners'].values())=={'neutral'}
        assert json.loads(file.read_text())['active']==1
        assert not [event for event in json.loads(file.read_text())['events'] if event[0]=='focus']
        assert json.loads(file.read_text())['clients']==before_clients
        core('start','--project','P');logical=core('list');state_bytes=metadata.read_bytes();startup()
        assert core('list')==logical and metadata.read_bytes()==state_bytes and json.loads(file.read_text())['bar_phases']==['ready']
        # New compositor: IDs may repeat, but old UUID ownership must not.
        env['HYPRLAND_INSTANCE_SIGNATURE']='two';world=json.loads(file.read_text());world['instance']='two';world['active']=1;file.write_text(json.dumps(world))
        startup();second=core('list');assert second['sessions']==[] and second['active_session_id'] is None
        assert json.loads(file.read_text())['bar_phases']==['ready','ready'];assert json.loads(file.read_text())['clients']==before_clients
        assert len(list((root/'run/hyprland').glob('session-startup-backup-*')))==2
        marker=json.loads((root/'run/hyprland/session-startup.json').read_text());assert marker['version']==1 and marker['phase']=='ready' and marker['instance']=='two' and marker['startup_menu']=='pending'
    finally:
        daemon.terminate()
        try:daemon.communicate(timeout=5)
        except subprocess.TimeoutExpired:daemon.kill();daemon.communicate()
print('R3 real private core: first login resets prior logical sessions, same-login retries preserve user state, new login has zero sessions and a one-shot menu request, no default Neutral/workspace, normal windows remain unowned/unchanged; no real bar/native/service touched.')
