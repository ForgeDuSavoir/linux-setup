"""Private HOME/native/core cohort harness; never points to the live session."""
import ctypes,importlib.util,json,os,subprocess,time
from pathlib import Path
from desktop_fixture import initial
ROOT=Path(__file__).resolve().parents[1]
CORE=Path.home()/'.local/bin/session-manager'
spec=importlib.util.spec_from_file_location('cohort',ROOT/'install_desktop.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class Fixture:
    def __init__(self,root):
        self.root=root;self.daemon=None
        for p in ['bin','.local/bin','.config/hypr/Scripts','.config/quickshell','config/session-manager','runtime/hyprland','state','data','projects/P']:(root/p).mkdir(parents=True,exist_ok=True)
        (root/'runtime').chmod(0o700)
        (root/'config/session-manager/config-v2.toml').write_text('schema_version=2\nproject_source='+json.dumps(str(root/'projects'))+'\n')
        (root/'.local/bin/session-manager').symlink_to(CORE)
        for name in ['session-desktop','session-startup']:(root/'.local/bin'/name).write_text('# old '+name+'\n')
        self.state=root/'runtime/hyprland/workspace-columns.json';self.state.write_text(json.dumps({'version':3,'order':[1],'owners':{'1':'neutral'},'preferred':{},'next_id':2}))
        self.marker=root/'runtime/hyprland/session-startup.json'
        self.marker.write_text(json.dumps({'version':1,'instance':'login-one','phase':'ready','personal_extra':'keep'}))
        (root/'.config/quickshell/shell.qml').write_text('legacy python3 workspace-columns.py\n')
        (root/'.config/hypr/keybinds.lua').write_text('-- old bindings\n')
        (root/'.config/hypr/Scripts/workspace-columns.py').write_text('raise RuntimeError("legacy controller must never execute")\n')
        world=initial((),None);world['instance']='login-one';(root/'world').write_text(json.dumps(world))
        (root/'bin/systemctl').write_text('#!/bin/sh\necho 0\n');(root/'bin/systemctl').chmod(0o700)
        fake=root/'bin/hyprctl'
        fake.write_text("""#!/usr/bin/python3
import json,os,sys
from pathlib import Path
sys.path.insert(0,"""+repr(str(ROOT/'tests'))+""")
from desktop_fixture import cli
a=sys.argv[1:]
if 'instances' in a:print(json.dumps([{'instance':os.environ['HYPRLAND_INSTANCE_SIGNATURE']}]) if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') else '[]')
elif a==['reload']:
    with open(Path(os.environ['HOME'])/'reloads','a') as f:f.write('reload\\n')
    print('ok')
else:
    sys.argv=[sys.argv[0],*[x for x in a if x!='-j']]
    cli('native')
""");fake.chmod(0o700)
        subprocess.run(['cc',str(ROOT/'tests/cohort-quickshell.c'),'-o',str(root/'bin/quickshell')],check=True)
        # Reap synthetic daemonized shells instead of leaving zombies under PID1.
        ctypes.CDLL(None).prctl(36,1,0,0,0)
        self.env={**os.environ,'HOME':str(root),'PATH':str(root/'bin')+':/usr/bin:/bin','XDG_CONFIG_HOME':str(root/'config'),'XDG_RUNTIME_DIR':str(root/'runtime'),'XDG_STATE_HOME':str(root/'state'),'XDG_DATA_HOME':str(root/'data'),'XDG_DATA_DIRS':str(root/'data'),'HYPRLAND_INSTANCE_SIGNATURE':'login-one','DESKTOP_WORLD':str(root/'world'),'SESSION_MANAGER_BIN':str(root/'.local/bin/session-manager'),'PYTHONDONTWRITEBYTECODE':'1','RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    def start(self):
        self.daemon=subprocess.Popen([str(CORE),'daemon'],env=self.env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        deadline=time.monotonic()+8
        while not (self.root/'runtime/session-manager/ipc-v3.sock').exists():
            assert self.daemon.poll() is None and time.monotonic()<deadline;time.sleep(.02)
        self.shell_start()
    def shell_start(self):subprocess.run(['quickshell','--daemonize','-p',str(self.root/'.config/quickshell')],env=self.env,check=True)
    def core(self,*args):return json.loads(subprocess.check_output([str(CORE),'--json','session',*args],env=self.env,text=True))
    def run(self,*args,ok=True):
        r=subprocess.run(['/usr/bin/python3',str(ROOT/'install_desktop.py'),*args],env=self.env,capture_output=True,text=True,timeout=90)
        assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
        return r
    def backups(self):return sorted((self.root/'state/linux-setup/desktop-cohort').glob('*'))
    def reap(self):
        while True:
            try:
                pid,_=os.waitpid(-1,os.WNOHANG)
                if not pid:break
            except ChildProcessError:break
    def close(self):
        p=self.root/'qs.pid'
        if p.exists():subprocess.run(['quickshell','kill','--pid',p.read_text()],env=self.env,check=True);time.sleep(.02)
        if self.daemon:
            self.daemon.terminate()
            try:self.daemon.communicate(timeout=5)
            except subprocess.TimeoutExpired:self.daemon.kill();self.daemon.communicate()
        self.reap()
