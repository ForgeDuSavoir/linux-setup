#!/usr/bin/env python3
"""Actual startup/gate, synthetic backend; real hyprctl only against PRIVATE registry/IPC."""
import json,os,shutil,socket,subprocess,tempfile,threading,time
from pathlib import Path
from test_startup_parity import Environment,cases,ROOT,BIN
MODES=['registry','ipc','malformed','wrong','multiple','lost']
WRAPPER="""#!/usr/bin/python3
import json,os,sys
from pathlib import Path
sys.path.insert(0,TESTS)
from startup_fixture import cli
p=Path(os.environ['DESKTOP_WORLD']);w=json.loads(p.read_text());mode=w['probe_mode'];a=sys.argv[1:]
def save():p.write_text(json.dumps(w))
if Path(sys.argv[0]).name=='manager':
 assert w.get('gate_ready'), 'core reached before compositor readiness'
 cli('core');sys.exit()
if a[0]=='instances':
 w['instance_probes']=w.get('instance_probes',0)+1
 marker=Path(os.environ['XDG_RUNTIME_DIR'])/'hyprland/session-startup.json'
 assert json.loads(marker.read_text())['phase']=='initializing'
 if w['instance_probes']==1 and mode in ['registry','lost']:save();sys.stdout.write('\\n]\\n\\n');sys.exit()
 if mode=='malformed':save();print('{unexpected');sys.exit()
 if mode=='wrong':save();print(json.dumps([{'instance':'other'}]));sys.exit()
 if mode=='multiple':save();print(json.dumps([{'instance':'one'},{'instance':'other'}]));sys.exit()
if a[0]=='monitors' and not w.get('gate_ready'):
 w['monitor_probes']=w.get('monitor_probes',0)+1
 if mode=='ipc' and w['monitor_probes']==1:
  save();print("Couldn't connect to /private/hypr/one/.socket.sock. (4)");sys.exit(4)
 w['gate_ready']=True
save();cli('native')
""".replace('TESTS',repr(str(ROOT/'tests')))
for mode in MODES:
 with tempfile.TemporaryDirectory(prefix='startup-ready-') as d:
    data=cases()['01_fresh'];e=Environment(d,data);before=e.metadata.read_bytes()
    w=json.loads(e.worldfile.read_text());w['probe_mode']=mode
    if mode=='lost':w['flags']['lost_reply']=True
    e.worldfile.write_text(json.dumps(w))
    for n in ['hyprctl','manager']:(e.root/'bin'/n).write_text(WRAPPER)
    env={**e.env,'HYPRLAND_INSTANCE_SIGNATURE':'one','XDG_CONFIG_HOME':str(e.root/'config'),'XDG_STATE_HOME':str(e.root/'state'),'XDG_DATA_HOME':str(e.root/'data'),'XDG_CACHE_HOME':str(e.root/'cache')}
    r=subprocess.run([str(BIN)],env=env,capture_output=True,text=True,timeout=6);w=json.loads(e.worldfile.read_text())
    success=mode in ['registry','ipc']
    assert json.loads(e.marker.read_text())['phase']==('ready' if success else 'failed'),(mode,r.stderr,w)
    assert w['bar_phases']==['ready' if success else 'failed']
    if success:
        assert w.get('generation',0)==0 and w['sessions']==[]
        assert [v for v in w['events'] if v[0]=='request' and v[1][0] in ['stop','start']]==[['request',['stop','A']],['request',['stop','B']]]
        assert w.get('instance_probes',0)>=2
    elif mode!='lost':
        assert e.metadata.read_bytes()==before and w['events']==[]
        assert not list(e.directory.glob('session-startup-backup-*'))
        assert 'startup hyprctl instances' in r.stderr or 'exactly this one' in r.stderr
    # Same-login ready/failed reentry never performs another probe, reset or bar.
    saved=e.worldfile.read_bytes()
    repeat=subprocess.run([str(BIN)],env=env,capture_output=True,text=True,timeout=3)
    assert e.worldfile.read_bytes()==saved and (repeat.returncode==0)==success
# Actual bounded child transport: a stuck readonly probe is killed/reaped and
# the overall budget ends; no reset API is involved in this test driver.
with tempfile.TemporaryDirectory(prefix='startup-probe-timeout-') as d:
    h=Path(d);tools=h/'bin';tools.mkdir()
    helper=tools/'hyprctl';helper.write_text('#!/usr/bin/python3\\nimport os,time\\nfrom pathlib import Path\\nPath(os.environ["HOME"]+"/pid").write_text(str(os.getpid()))\\ntime.sleep(20)\\n');helper.chmod(0o700)
    env={'HOME':str(h),'PATH':str(tools)+':/usr/bin:/bin','XDG_RUNTIME_DIR':str(h/'run'),'XDG_CONFIG_HOME':str(h/'config'),'XDG_STATE_HOME':str(h/'state')}
    started=time.monotonic()
    r=subprocess.run([str(ROOT/'target/release/examples/startup-readiness'),'one','100'],env=env,capture_output=True,text=True,timeout=3)
    assert r.returncode==1 and 'no reset performed' in r.stderr and time.monotonic()-started<2
    if (h/'pid').exists():assert not Path('/proc/'+(h/'pid').read_text()).exists()
# Real installed hyprctl: partial registration produces malformed JSON, then
# complete registration and a synthetic Unix IPC server produce readiness.
REAL=shutil.which('hyprctl')
if REAL:
 with tempfile.TemporaryDirectory(prefix='real-hypr-readiness-') as d:
    h=Path(d);h.chmod(0o700);run=h/'run';run.mkdir(mode=0o700);sig='diagnostic_1_1';instance=run/'hypr'/sig;instance.mkdir(parents=True)
    lock=instance/'hyprland.lock';lock.write_text(str(os.getpid())+'\n')
    env={'HOME':str(h),'XDG_RUNTIME_DIR':str(run),'HYPRLAND_INSTANCE_SIGNATURE':sig,'PATH':'/usr/bin:/bin','XDG_CONFIG_HOME':str(h/'config'),'XDG_STATE_HOME':str(h/'state'),'XDG_DATA_HOME':str(h/'data'),'XDG_CACHE_HOME':str(h/'cache')}
    broken=subprocess.run([REAL,'instances','-j'],env=env,capture_output=True,timeout=2)
    # This exact buggy format is specific to the installed affected hyprctl.
    if broken.returncode==0 and broken.stdout.strip()==b']':
        sock=socket.socket(socket.AF_UNIX);sock.bind(str(instance/'.socket.sock'));sock.listen();sock.settimeout(3);requests=[]
        def server():
            try:
                conn,_=sock.accept()
                with conn:
                    request=conn.recv(4096);requests.append(request)
                    conn.sendall(b'[{"focused":true,"activeWorkspace":{"id":1},"specialWorkspace":{"name":""}}]')
            finally:sock.close()
        thread=threading.Thread(target=server);thread.start()
        tools=h/'bin';tools.mkdir();wrapper=tools/'hyprctl'
        wrapper.write_text('#!/usr/bin/python3\nimport os,sys,subprocess\nfrom pathlib import Path\np=Path('+repr(str(h/'count'))+')\nn=int(p.read_text()) if p.exists() else 0\nif sys.argv[1]=="instances":\n n+=1;p.write_text(str(n))\n if n==2:Path('+repr(str(lock))+').write_text('+repr(str(os.getpid())+'\nwayland-private\n')+')\nr=subprocess.run(['+repr(REAL)+',*sys.argv[1:]])\nsys.exit(r.returncode)\n');wrapper.chmod(0o700)
        env['PATH']=str(tools)+':/usr/bin:/bin'
        driver=ROOT/'target/release/examples/startup-readiness'
        r=subprocess.run([str(driver),sig,'2000'],env=env,capture_output=True,text=True,timeout=5);thread.join(timeout=4)
        assert r.returncode==0 and r.stdout.strip()=='ready',(r.stderr,r.stdout)
        assert int((h/'count').read_text())==2 and len(requests)==1 and b'monitors' in requests[0]
        print('Real hyprctl/private Unix IPC: exact partial-lock malformed JSON recovered, one registration retry then readonly monitor confirmation.')
print('Startup readiness: registry/IPC cold-start races, no reset before readiness, wrong/ambiguous/corrupt hard failure, lost mutation no replay, same-login ready/failed preservation passed; no live startup/session/bar.')
