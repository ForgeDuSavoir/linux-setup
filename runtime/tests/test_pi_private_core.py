#!/usr/bin/env python3
"""R5 actual v3 daemon/R4/R2 in private HOME, synthetic native, stub terminal/Pi."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from desktop_fixture import initial
from test_pi_parity import ROOT,BIN
CORE=Path.home()/'.local/bin/session-manager'
with tempfile.TemporaryDirectory(prefix='r5-core-') as directory:
    root=Path(directory)
    for name in ['config/session-manager','config/agora-workflow','run/hyprland','state','data','projects/P quoted é','Agora','.local/bin','bin']:(root/name).mkdir(parents=True,exist_ok=True)
    (root/'run').chmod(0o700)
    project=root/'projects/P quoted é';agora=root/'Agora'
    (root/'config/session-manager/config-v2.toml').write_text('schema_version=2\nproject_source='+json.dumps(str(root/'projects'))+'\n')
    (root/'config/agora-workflow/config.toml').write_text('agora_root='+json.dumps(str(agora))+'\n')
    (root/'.local/bin/session-manager').symlink_to(CORE)
    for name in ['session-desktop','agora-notify']:(root/'.local/bin'/name).symlink_to(ROOT/'target/release'/name)
    native=root/'native';world=initial((),None);native.write_text(json.dumps(world))
    hypr=root/'bin/hyprctl';hypr.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom desktop_fixture import cli\ncli("native")\n');hypr.chmod(0o700)
    terminal=root/'.local/bin/launch-terminal-command'
    terminal.write_text("""#!/usr/bin/python3
import json,os,subprocess,sys
from pathlib import Path
Path(os.environ['HOME']+'/terminal').write_text(json.dumps([sys.argv[1:],os.environ['AGORA_NOTIFICATION_CONTEXT']]))
# Simulate an already-running terminal server retaining a stale environment.
env={**os.environ,'AGORA_NOTIFICATION_CONTEXT':'stale-server'}
subprocess.run(sys.argv[2:],cwd=sys.argv[1],env=env,check=True)
""");terminal.chmod(0o700)
    stub=root/'bin/pi';stub.write_text("""#!/usr/bin/python3
import json,os,sys
from pathlib import Path
Path(os.environ['HOME']+'/stub').write_text(json.dumps([os.getcwd(),os.environ['AGORA_NOTIFICATION_CONTEXT'],sys.argv[1:]]))
""");stub.chmod(0o700)
    env={'HOME':str(root),'XDG_CONFIG_HOME':str(root/'config'),'XDG_STATE_HOME':str(root/'state'),'XDG_DATA_HOME':str(root/'data'),'XDG_DATA_DIRS':str(root/'data'),'XDG_RUNTIME_DIR':str(root/'run'),'PATH':str(root/'bin')+':/usr/bin:/bin','DESKTOP_WORLD':str(native),'SESSION_MANAGER_BIN':str(CORE),'PYTHONDONTWRITEBYTECODE':'1','AGORA_NOTIFICATION_CONTEXT':'session:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'}
    def core(*args):return json.loads(subprocess.check_output([str(CORE),'--json','session',*args],env=env,text=True))
    metadata=root/'run/hyprland/workspace-columns.json'
    def ownership(sid):
        metadata.write_text(json.dumps({'version':3,'order':[1],'owners':{'1':sid or 'neutral'},'preferred':{},'next_id':2}))
    def launch(path,tag,*args):
        logical=core('list');raw=metadata.read_bytes()
        result=subprocess.run([str(BIN),*args],env=env,capture_output=True,text=True,timeout=8)
        assert result.returncode==0,result.stderr
        assert json.loads((root/'stub').read_text())==[str(path),tag,['--continue']]
        assert json.loads((root/'terminal').read_text())==[[str(path),'env','AGORA_NOTIFICATION_CONTEXT='+tag,'pi','--continue'],tag]
        assert core('list')==logical and metadata.read_bytes()==raw
        assert json.loads(native.read_text())['clients']==world['clients']
        assert not list(root.rglob('app-usage.json'))
    daemon=subprocess.Popen([str(CORE),'daemon'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+8
        while not (root/'run/session-manager/ipc-v3.sock').exists():
            assert daemon.poll() is None;assert time.monotonic()<deadline;time.sleep(.02)
        ownership(None);launch(agora,'neutral')
        a=core('start','--project',project.name)['session']['id'];ownership(a)
        launch(project,'session:'+a);launch(agora,'session:'+a,'--agora')
        b=core('start','--neutral')['session']['id'];ownership(b)
        # Neutral never needs an available project catalogue.
        (root/'projects').rename(root/'detached')
        launch(agora,'session:'+b)
        # Also exercise the still-installed desktop ABI, not just the future R2 ELF.
        desktop=root/'.local/bin/session-desktop';desktop.unlink()
        desktop.write_bytes((ROOT.parent/'configs/session-manager/session-desktop.py').read_bytes());desktop.chmod(0o700)
        env['SESSION_COLUMNS_SCRIPT']=str(ROOT.parent/'configs/hypr/files/Scripts/workspace-columns.py')
        launch(agora,'session:'+b)
        desktop.unlink();desktop.symlink_to(ROOT/'target/release/session-desktop')
        (root/'detached').rename(root/'projects')
        core('switch',a);ownership(b) # Logical/spatial mismatch: do not invent origin.
        launch(project,'global')
        core('deactivate');ownership(None);launch(agora,'neutral')
    finally:
        daemon.terminate()
        try:daemon.communicate(timeout=5)
        except subprocess.TimeoutExpired:daemon.kill();daemon.communicate()
print('R5 private real core/R4/R2: project, Neutral UUID, unowned, explicit Agora and mismatch; pi --continue in the routed directory; stale terminal server overridden by literal env argv; no real Pi/model/desktop.')
