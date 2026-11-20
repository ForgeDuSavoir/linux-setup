#!/usr/bin/env python3
"""Actual QML/IPC/notification store on PRIVATE D-Bus/runtime, synthetic desktop only."""
import json,os,re,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
A='11111111-1111-1111-1111-111111111111';B='22222222-2222-2222-2222-222222222222';C='33333333-3333-3333-3333-333333333333'
ROWS=[{'id':B,'name':'Zulu','source':{'kind':'project','project_name':'Zulu'},'number':1},{'id':A,'name':'Alpha','source':{'kind':'neutral'},'number':1},{'id':C,'name':'Beta','source':{'kind':'neutral'},'number':2}]
HELPER=r'''#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
p=Path(os.environ['HOME'])/'world'
def read():return json.loads(p.read_text())
w=read();a=sys.argv[1:]
if a==['status']:
 while w.get('hold'):time.sleep(.01);w=read()
 if w.get('bad'):print('bad JSON');sys.exit(0)
 active=w['active'];print(json.dumps({'sessions':w['rows'],'active_session_id':active,'displayed_context':active or 'neutral','context_confirmed':w.get('confirmed',True)}))
else:
 assert len(a)==2 and a[0]=='switch'
 with (p.parent/'actions').open('a') as f:f.write(a[1]+'\n')
 if w.get('fail'):print('synthetic switch failure',file=sys.stderr);sys.exit(7)
 if w.get('hide'):w['hide']=False
 else:w['active']=a[1]
 tmp=p.with_name('world-'+str(os.getpid()));tmp.write_text(json.dumps(w));tmp.replace(p)
'''
def inside():
 source=Path(__file__).resolve().parents[1]/'quickshell/files'
 with tempfile.TemporaryDirectory(prefix='session-attention-') as d:
  h=Path(d);q=h/'qml';q.mkdir();runtime=h/'runtime';runtime.mkdir(mode=0o700)
  for n in ['SessionService.qml','NotificationStore.qml','NotificationPolicy.js']:shutil.copyfile(source/n,q/n)
  forward=next(line.strip() for line in (source/'SessionMenu.qml').read_text().splitlines() if 'function nextAttention()' in line)
  (q/'shell.qml').write_text('''import Quickshell
import Quickshell.Io
import QtQuick
Scope {
 property var menu: ({sessionService:session})
 SessionService { id: session; notificationState: store }
 NotificationStore { id: store; sessionService: session }
 IpcHandler { target: "sessions"; FORWARD }
 IpcHandler {
  target: "fixture"
  function state(): string { return JSON.stringify({active:session.activeId,busy:session.busy,phase:session.navigationPhase,generation:session.generation,confirmed:session.contextConfirmed,stale:session.stale,error:session.error,unread:store.unread}); }
 }
}
'''.replace('FORWARD',forward))
  world=h/'world'
  def write(w):
   tmp=h/'world-parent';tmp.write_text(json.dumps(w));tmp.replace(world)
  def change(**kwargs):w=json.loads(world.read_text());w.update(kwargs);write(w)
  write({'active':A,'rows':ROWS})
  helper=h/'.local/bin/session-desktop';helper.parent.mkdir(parents=True);helper.write_text(HELPER);helper.chmod(0o700)
  env={'HOME':str(h),'PATH':'/usr/bin:/bin','XDG_RUNTIME_DIR':str(runtime),'XDG_CONFIG_HOME':str(h/'config'),'XDG_CACHE_HOME':str(h/'cache'),'XDG_DATA_HOME':str(h/'data'),'XDG_DATA_DIRS':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software','NO_COLOR':'1','DBUS_SESSION_BUS_ADDRESS':os.environ['DBUS_SESSION_BUS_ADDRESS']}
  log=h/'log'
  with log.open('w') as f:p=subprocess.Popen(['quickshell','-p',str(q)],env=env,stdout=f,stderr=f)
  try:
   def ipc(target,method):return subprocess.check_output(['quickshell','ipc','-p',str(q),'call',target,method],env=env,text=True,stderr=subprocess.PIPE,timeout=5).strip()
   def state():return json.loads(ipc('fixture','state'))
   def wait(fn):
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
     if p.poll() is not None:raise RuntimeError(log.read_text())
     try:
      s=state()
      if fn(s):return s
     except subprocess.CalledProcessError:pass
     time.sleep(.02)
    raise AssertionError(('fixture timeout',state(),log.read_text()))
   def actions():return (h/'actions').read_text().splitlines() if (h/'actions').exists() else []
   def notify(context):
    hint="{'x-agora-context': <'"+context+"'>}"
    subprocess.run(['gdbus','call','--session','--dest','org.freedesktop.Notifications','--object-path','/org/freedesktop/Notifications','--method','org.freedesktop.Notifications.Notify','Fixture','0','','Synthetic attention','No personal content','[]',hint,'60000'],env=env,check=True,stdout=subprocess.DEVNULL,timeout=5)
   def press(expected):
    ipc('sessions','nextAttention');return wait(lambda s:not s['busy'] and s['active']==expected)
   wait(lambda s:s['active']==A and s['confirmed'])
   notify('global');notify('session:'+C);notify('session:'+B)
   wait(lambda s:s['unread'].get('session:'+B) and s['unread'].get('session:'+C))
   change(hold=True);ipc('sessions','nextAttention');s=wait(lambda s:s['phase']=='choose');generation=s['generation']
   ipc('sessions','nextAttention');ipc('sessions','nextAttention');assert state()['generation']==generation
   change(hold=False);s=wait(lambda s:not s['busy'] and s['active']==B)
   assert actions()==[B] and not s['unread'].get('session:'+B) and s['unread'].get('session:'+C)
   s=press(C);assert not s['unread'].get('session:'+C);press(B);press(A)
   notify('session:'+B);wait(lambda s:s['unread'].get('session:'+B));change(fail=True)
   count=len(actions());s=press(A);assert len(actions())==count+1 and s['unread'].get('session:'+B) and 'synthetic' in s['error']
   change(fail=False);press(B)
   notify('session:'+C);wait(lambda s:s['unread'].get('session:'+C));change(hide=True)
   count=len(actions());s=press(B);assert len(actions())==count+1 and s['unread'].get('session:'+C) and 'not confirmed' in s['error']
   press(C)
   change(rows=[ROWS[2],ROWS[1],ROWS[0]]);press(A) # New bar order, not a cached cursor.
   change(active=None);notify('neutral');press(C) # Unowned attention is not a UUID target.
   count=len(actions());change(rows=[ROWS[2]]);press(C);assert len(actions())==count
   change(rows=[],active=None);press('');assert len(actions())==count
   change(rows=ROWS,active=A,confirmed=False);s=press(A);assert len(actions())==count and s['error']
   change(confirmed=True,bad=True);ipc('sessions','nextAttention');wait(lambda s:not s['busy'] and s['stale']);assert len(actions())==count
   assert not (h/'state').exists()
   print('Real private QML/IPC: leftmost pending then bar-order wrap, actual notification acknowledgement, repeat suppression, failure/hide-first no retry, reorder, unowned/empty/single/unconfirmed/error passed; no live desktop/bus/history.')
  except Exception:
   print(log.read_text(),file=sys.stderr);raise
  finally:
   change(hold=False)
   if p.poll() is None:p.send_signal(signal.SIGTERM);p.wait(timeout=10)
if __name__=='__main__':
 if sys.argv[1:]==['--inside']:inside()
 else:sys.exit(subprocess.run(['dbus-run-session','--','/usr/bin/python3',str(Path(__file__).resolve()),'--inside'],env={'PATH':'/usr/bin:/bin'},timeout=60).returncode)
