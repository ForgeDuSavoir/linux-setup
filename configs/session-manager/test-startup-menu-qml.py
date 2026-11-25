#!/usr/bin/env python3
"""Real menu/service/native claim on private runtime/bus; offscreen window backend."""
import json,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/'quickshell/files'
BIN=Path(__file__).resolve().parents[2]/'runtime/target/release/session-startup'
A='11111111-1111-1111-1111-111111111111'
HELPER=r'''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
h=Path(os.environ['HOME']);p=h/'world';w=json.loads(p.read_text());a=sys.argv[1:]
if Path(sys.argv[0]).name=='session-manager':
 assert a==['--json','source','list']
 print(json.dumps({'sources':[{'name':'Neutral','source':{'kind':'neutral'}},{'name':'P','source':{'kind':'project','project_name':'P'}}]}))
elif a==['status']:
 rows=w['sessions'];sid=rows[0]['id'] if rows else None
 print(json.dumps({'sessions':rows,'active_session_id':sid,'displayed_context':sid or 'neutral','context_confirmed':True}))
else:
 assert a==['start','--project','P']
 with (h/'actions').open('a') as f:f.write(json.dumps(a)+'\n')
 w['sessions']=[{'id':'11111111-1111-1111-1111-111111111111','name':'P-1','source':{'kind':'project','project_name':'P'},'number':1}]
 tmp=h/'world-child';tmp.write_text(json.dumps(w));tmp.replace(p);print('{}')
'''
def inside():
 with tempfile.TemporaryDirectory(prefix='startup-menu-qml-') as d:
  h=Path(d);q=h/'qml';q.mkdir();runtime=h/'run';runtime.mkdir(mode=0o700);meta=runtime/'hyprland';meta.mkdir();marker=meta/'session-startup.json'
  shutil.copyfile(SOURCE/'SessionService.qml',q/'SessionService.qml')
  # Only the platform window container is substituted: all actual menu controls,
  # startup Process/functions/Connections/IPC and service logic remain unchanged.
  text=(SOURCE/'SessionMenu.qml').read_text().replace('import QtQuick\n','import QtQuick\nimport QtQuick.Window\n')
  old='''    PanelWindow {
        visible: menu.menuVisible
        screen: Quickshell.screens[0]
        anchors { top: true }
        implicitWidth: 460
        implicitHeight: 660'''
  assert old in text
  text=text.replace(old,'''    Window {
        visible: menu.menuVisible
        width: 460
        height: 660''')
  text='\n'.join(line for line in text.splitlines() if not line.strip().startswith('WlrLayershell.'))+'\n';(q/'SessionMenu.qml').write_text(text)
  (q/'shell.qml').write_text('''import Quickshell
import Quickshell.Io
import QtQuick
Scope {
 SessionService { id: session }
 SessionMenu { id: menu; sessionService: session }
 IpcHandler {
  target: "fixture"
  function state(): string { return JSON.stringify({visible:menu.menuVisible,section:menu.selectedSection,pending:menu.startupMenuPending,used:menu.startupMenuUsed,confirmed:session.contextConfirmed,stale:session.stale,active:session.activeId,rows:session.sessions.length,projects:menu.projects.length}); }
  function refresh(): void { session.invalidateContext(); }
  function choose(): void { menu.act(["start","--project","P"]); }
 }
}
''')
  local=h/'.local/bin';local.mkdir(parents=True);(local/'session-startup').symlink_to(BIN)
  for name in ['session-manager','session-desktop']:
   f=local/name;f.write_text(HELPER);f.chmod(0o700)
  env={'HOME':str(h),'PATH':'/usr/bin:/bin','XDG_RUNTIME_DIR':str(runtime),'XDG_CONFIG_HOME':str(h/'config'),'XDG_CACHE_HOME':str(h/'cache'),'XDG_DATA_HOME':str(h/'data'),'XDG_DATA_DIRS':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'HYPRLAND_INSTANCE_SIGNATURE':'one','QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software','NO_COLOR':'1','DBUS_SESSION_BUS_ADDRESS':os.environ['DBUS_SESSION_BUS_ADDRESS']}
  world=h/'world'
  def write(rows):
   tmp=h/'world-parent';tmp.write_text(json.dumps({'sessions':rows}));tmp.replace(world)
  def ipc(target,method):return subprocess.check_output(['quickshell','ipc','-p',str(q),'call',target,method],env=env,text=True,stderr=subprocess.PIPE,timeout=5).strip()
  def state():return json.loads(ipc('fixture','state'))
  p=None;log=h/'log'
  def wait(fn):
   deadline=time.monotonic()+6
   while time.monotonic()<deadline:
    if p.poll() is not None:raise RuntimeError(log.read_text())
    try:
     s=state()
     if fn(s):return s
    except subprocess.CalledProcessError:pass
    time.sleep(.02)
   raise AssertionError((state(),log.read_text()))
  def start():
   with log.open('w') as f:return subprocess.Popen(['quickshell','-p',str(q)],env=env,stdout=f,stderr=f)
  def stop():
   if p and p.poll() is None:p.send_signal(signal.SIGTERM);p.wait(timeout=6)
  existing=[{'id':A,'name':'P-1','source':{'kind':'project','project_name':'P'},'number':1}]
  try:
   for mode in ['pending','user-session','failed','deferred','legacy-ready','other-instance']:
    raw={'version':1,'instance':'other' if mode=='other-instance' else 'one','phase':mode if mode in ['failed','deferred'] else 'ready','keep':'personal-extra'}
    if mode!='legacy-ready':raw['startup_menu']='pending'
    marker.write_text(json.dumps(raw));before=marker.read_bytes();write(existing if mode=='user-session' else [])
    p=start();s=wait(lambda s:s['confirmed'] and s['projects']==2 and (s['used'] if mode=='pending' else True))
    if mode=='pending':
     assert s['visible'] and s['section']=='projects' and s['rows']==0
     assert json.loads(marker.read_text())=={**raw,'startup_menu':'consumed'}
     assert not (h/'actions').exists(),'no default session or automatic action'
     # Choice is deliberate; the existing safe action path closes the menu.
     ipc('fixture','choose');wait(lambda s:not s['visible'] and s['rows']==1 and s['confirmed'])
     assert len((h/'actions').read_text().splitlines())==1
     write([]);ipc('fixture','refresh');wait(lambda s:s['rows']==0 and s['confirmed']);assert not state()['visible']
     # Reload/restart same instance must not reopen after consumption or reset state.
     stop();p=start();wait(lambda s:s['confirmed'] and s['projects']==2);assert not state()['visible']
     (h/'actions').unlink()
    else:
     # Wait for the native claim to exit via the stable lock, without opening UI.
     time.sleep(.15)
     assert not state()['visible']
     if mode=='user-session':
      assert json.loads(marker.read_text())['startup_menu']=='consumed'
      ipc('sessions','toggle');s=wait(lambda s:s['visible']);assert s['section']=='projects' and s['rows']==1
      ipc('fixture','refresh');s=wait(lambda s:s['confirmed']);assert s['section']=='projects'
      ipc('sessions','hide')
      write([]);ipc('fixture','refresh');wait(lambda s:s['rows']==0 and s['confirmed']);assert not state()['visible']
     else:assert marker.read_bytes()==before
    stop();p=None
   # Escape/explicit close consumes the opening, not a property binding to emptiness.
   marker.write_text(json.dumps({'version':1,'instance':'one','phase':'ready','startup_menu':'pending'}));write([])
   p=start();wait(lambda s:s['visible']);ipc('sessions','hide');ipc('fixture','refresh');wait(lambda s:s['confirmed']);assert not state()['visible']
   stop();p=start();wait(lambda s:s['confirmed'] and s['projects']==2);assert not state()['visible']
   assert not (h/'actions').exists() and not (h/'state').exists()
   print('Real offscreen menu/native claim: zero sessions -> project search, explicit project choice only, close/reload/no reopen, user-session/failed/deferred/legacy/wrong-instance guards passed; private bus/runtime, no live UI or reset.')
  except Exception:
   print(log.read_text(),file=sys.stderr);raise
  finally:stop()
if __name__=='__main__':
 if sys.argv[1:]==['--inside']:inside()
 else:sys.exit(subprocess.run(['dbus-run-session','--','/usr/bin/python3',str(Path(__file__).resolve()),'--inside'],env={'PATH':'/usr/bin:/bin'},timeout=90).returncode)
