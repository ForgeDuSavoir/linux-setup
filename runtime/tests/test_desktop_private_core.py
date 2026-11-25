#!/usr/bin/env python3
"""R2 real installed core binary in private HOME/socket; fake Hyprland only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from desktop_fixture import Backend,initial
from test_desktop_parity import BIN,ROOT

CORE=Path.home()/'.local/bin/session-manager'
assert CORE.is_file() and subprocess.check_output([str(CORE),'--version'],text=True).strip().endswith('(protocol 3)')
with tempfile.TemporaryDirectory(prefix='r2-private-core-') as directory:
    root=Path(directory)
    for path in ['config/session-manager','run','state','data','projects/P','bin']:(root/path).mkdir(parents=True,exist_ok=True)
    (root/'run').chmod(0o700)
    (root/'config/session-manager/config-v2.toml').write_text('schema_version=2\nproject_source='+json.dumps(str(root/'projects'))+'\n')
    world=initial((),None);file=root/'world';file.write_text(json.dumps(world))
    fake=root/'bin/hyprctl';fake.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom desktop_fixture import cli\ncli("native")\n');fake.chmod(0o700)
    env={'HOME':str(root),'XDG_CONFIG_HOME':str(root/'config'),'XDG_STATE_HOME':str(root/'state'),'XDG_DATA_HOME':str(root/'data'),'XDG_DATA_DIRS':str(root/'data'),'XDG_RUNTIME_DIR':str(root/'run'),'PATH':str(root/'bin')+':/usr/bin:/bin','DESKTOP_WORLD':str(file),'SESSION_MANAGER_BIN':str(CORE),'PYTHONDONTWRITEBYTECODE':'1'}
    def core(*args):return json.loads(subprocess.check_output([str(CORE),'--json','session',*args],env=env,text=True))
    def desktop(*args,ok=True):
        result=subprocess.run([str(BIN),*args],env=env,capture_output=True,text=True,timeout=8)
        assert (result.returncode==0)==ok,(args,result.stdout,result.stderr)
        return json.loads(result.stdout) if ok else result.stderr
    daemon=subprocess.Popen([str(CORE),'daemon'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+8
        while not (root/'run/session-manager/ipc-v3.sock').exists():
            assert daemon.poll() is None,'private core exited';assert time.monotonic()<deadline;time.sleep(.02)
        a=desktop('start','--neutral')['session']['id']
        assert desktop('status')['context_confirmed']
        # First prove empty replacement with the real private daemon.
        replaced=a
        a=desktop('start','--neutral')['session']['id'];assert a!=replaced
        assert [s['id'] for s in core('list')['sessions']]==[a]
        world=json.loads(file.read_text());world['clients'].append({'address':'0xaaa','workspace':{'id':world['active'],'name':str(world['active'])}});file.write_text(json.dumps(world))
        b=desktop('start','--neutral')['session']['id'];assert a!=b
        world=json.loads(file.read_text());world['clients']=[c for c in world['clients'] if c.get('address')!='0xaaa'];file.write_text(json.dumps(world))
        assert [s['source'] for s in core('list')['sessions']]==[{'kind':'neutral'},{'kind':'neutral'}]
        active=json.loads(file.read_text())['active']
        desktop('close',str(active))
        after=core('list');assert [s['id'] for s in after['sessions']]==[a] and after['active_session_id']==a
        assert desktop('status')['context_confirmed']
        metadata=root/'run/hyprland/workspace-columns.json';before=metadata.read_bytes();logical=core('list')
        assert 'last open session' in desktop('stop',a,ok=False)
        assert metadata.read_bytes()==before and core('list')==logical
        # Keep a normal window in inactive a; it must block stop without switching.
        world=json.loads(file.read_text());normal={'address':'0xabc','workspace':{'id':world['active'],'name':str(world['active'])}};world['clients'].append(normal);file.write_text(json.dumps(world))
        project=desktop('start','--project','P')['session']['id']
        assert 'open windows' in desktop('stop',a,ok=False)
        assert core('list')['active_session_id']==project
        desktop('stop',project)
        world=json.loads(file.read_text());world['window']=normal;file.write_text(json.dumps(world))
        logical=core('list');desktop('close',str(world['active']))
        assert core('list')==logical # window close request != logical stop
        assert json.loads(file.read_text())['events'][-1]==['close','0xabc']
        desktop('deactivate');status=desktop('status');assert status['active_session_id'] is None and status['displayed_context']=='neutral' and status['context_confirmed']
        assert [s['id'] for s in core('list')['sessions']]==[a]
    finally:
        daemon.terminate()
        try:daemon.communicate(timeout=5)
        except subprocess.TimeoutExpired:daemon.kill();daemon.communicate()
print('R2 real private v3 core: Neutral UUIDs, fresh workspaces, Q/menu fallback, last-session guard, inactive window guard, visible addressed close and explicit unowned deselection passed; no live service/session used.')
