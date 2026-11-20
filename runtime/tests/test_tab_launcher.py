#!/usr/bin/env python3
"""Real controller + real launcher, private metadata/fake Hyprland/Core/Rofi/GTK only."""
import json,os,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CONTROLLER=ROOT/'target/release/workspace-controller';LAUNCHER=ROOT.parent/'configs/session-manager/app-launcher/target/release/session-app-launcher'
OWNER='11111111-1111-1111-1111-111111111111'
HELPER=r'''#!/usr/bin/python3
import json,os,sys,re,fcntl
from pathlib import Path
h=Path(os.environ['HOME']);p=h/'world';w=json.loads(p.read_text());tool=Path(sys.argv[0]).name;a=sys.argv[1:]
def save():p.write_text(json.dumps(w))
def log(x):
 with (h/'trace').open('a') as f:f.write(json.dumps(x)+'\n')
log([tool,a])
if tool=='hyprctl':
 a=[v for v in a if v!='-j'];name=a[0]
 if name in ['eval','dispatch']:
  code=a[1]
  if 'new empty workspace is not active' in code:
   target=int(re.search(r'get_workspace\((\d+)\)',code)[1])
   if w['mode']=='confirm-error' or w['active']!=target or target not in w['ws']:print('error: no confirmed active empty workspace');sys.exit(7)
   if w['mode']=='switch-before-menu':w['active']=1
   if w['mode']=='special-before-menu':w['special']='special:global'
   save();print('ok')
  elif 'toggle_special' in code:w['special']='';save();print('ok')
  else:
   target=int(re.search(r'workspace\s*=\s*(\d+)',code)[1])
   if name=='eval' and w['mode']=='collision':print('error: target exists');sys.exit(7)
   if target not in w['ws']:w['ws'].append(target)
   w['active']=target;save()
   if w['mode']=='lost':print('error: result uncertain');sys.exit(7)
   print('ok')
 elif name=='activeworkspace':print(json.dumps({'id':w['active']}))
 elif name=='workspaces':print(json.dumps([{'id':v} for v in w['ws']]))
 elif name=='clients':print(json.dumps([{'address':'0xaa','workspace':{'id':v}} for v in w['occupied']]))
 elif name=='monitors':print(json.dumps([{'focused':True,'activeWorkspace':{'id':w['active']},'specialWorkspace':{'name':w.get('special','')}}]))
 else:raise AssertionError(a)
elif tool=='session-manager':
 assert a[0]=='--json'
 if a[1:]==['session','list']:
  print(json.dumps({'sessions':[{'id':w['owner'],'source':{'kind':'neutral'}}] if w['owner']!='neutral' else [],'active_session_id':None if w['owner']=='neutral' else w['owner'],'revision':0}))
 elif a[1:]==['application','list']:print(json.dumps({'applications':[{'id':'test.desktop','name':'Test','origin':'installed'}]}))
 else:raise AssertionError(a)
elif tool=='rofi':
 lock=h/'runtime/hyprland/workspace-columns.lock'
 with lock.open('a+b') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 (h/'menu').write_text('workspace lock released')
 sys.stdin.read()
 if w['mode']=='switch-during-menu':w['active']=1;save()
 if w['mode']=='cancel':sys.exit(1)
 print('0')
elif tool=='gtk-launch':(h/'launched').write_text(json.dumps([a,w['active']]))
else:raise AssertionError(tool)
'''
CASES=['created','unowned','cancel','empty-first','empty-return','scratchpad','collision','lost','confirm-error','switch-before-menu','special-before-menu','switch-during-menu','missing-launcher','old-launcher']
with tempfile.TemporaryDirectory(prefix='tab-launcher-') as d:
 for mode in CASES:
  h=Path(d)/mode;h.mkdir();b=h/'bin';b.mkdir();local=h/'.local/bin';local.mkdir(parents=True);runtime=h/'runtime/hyprland';runtime.mkdir(parents=True)
  owner='neutral' if mode=='unowned' else OWNER
  w={'mode':mode,'owner':owner,'active':2 if mode=='empty-return' else 1,'ws':[1,2] if mode=='empty-return' else [1],'occupied':[] if mode=='empty-first' else [1],'special':'special:global' if mode=='scratchpad' else ''}
  state={'version':3,'order':w['ws'],'owners':{str(v):owner for v in w['ws']},'preferred':{},'next_id':3}
  (runtime/'workspace-columns.json').write_text(json.dumps(state));(h/'world').write_text(json.dumps(w))
  for tool in ['hyprctl','session-manager','rofi','gtk-launch']:
   p=(local if tool=='session-manager' else b)/tool;p.write_text(HELPER);p.chmod(0o700)
  if mode!='missing-launcher':
   p=local/'session-app-launcher'
   if mode=='old-launcher':p.write_text('#!/bin/sh\necho old-launcher\n');p.chmod(0o700)
   else:p.symlink_to(LAUNCHER)
  apps=h/'data/applications';apps.mkdir(parents=True);(apps/'test.desktop').write_text('[Desktop Entry]\nType=Application\nName=Test\nExec=/usr/bin/true\n')
  env={**os.environ,'HOME':str(h),'XDG_RUNTIME_DIR':str(h/'runtime'),'XDG_DATA_HOME':str(h/'data'),'XDG_DATA_DIRS':str(h/'data'),'XDG_CONFIG_HOME':str(h/'config'),'XDG_STATE_HOME':str(h/'state'),'PATH':str(b)+':/usr/bin:/bin','DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(h/'no-bus')}
  before=(runtime/'workspace-columns.json').read_bytes()
  r=subprocess.run([str(CONTROLLER),'create-empty-and-launch'],env=env,capture_output=True,text=True,timeout=10)
  success=mode in ['created','unowned','cancel','empty-first','empty-return','scratchpad']
  assert (r.returncode==0)==success,(mode,r.stderr)
  menu=(h/'menu').exists();launched=(h/'launched').exists()
  assert menu==(mode in ['created','unowned','cancel','switch-during-menu']),(mode,r.stderr)
  assert launched==(mode in ['created','unowned']),(mode,r.stderr)
  trace=[json.loads(v) for v in (h/'trace').read_text().splitlines()] if (h/'trace').exists() else []
  confirmations=[row for row in trace if row[0]=='hyprctl' and len(row[1])>1 and 'new empty workspace is not active' in row[1][1]]
  if launched:
   assert len(confirmations)==1
   assert next(i for i,t in enumerate(trace) if t==confirmations[0])<next(i for i,t in enumerate(trace) if t[0]=='rofi')
   assert json.loads((h/'launched').read_text())==[['test.desktop'],3]
  if mode in ['empty-first','empty-return','scratchpad','missing-launcher','old-launcher']:assert not confirmations
  if mode in ['missing-launcher','old-launcher']:assert not trace and (runtime/'workspace-columns.json').read_bytes()==before
  if mode=='confirm-error':assert json.loads((h/'world').read_text())['active']==3 # No rollback/retry.
  assert not list((h/'state').rglob('*.json')), (mode,'Tab must not publish usage')
  if mode=='created':lua=confirmations[0][1][1]
 # Execute the exact generated confirmation with Lua; compositor state, not delays.
 for active,exists,count,ok in [(3,True,0,True),(1,True,0,False),(3,False,0,False),(3,True,1,False)]:
  setup='hl={get_active_workspace=function() return {id='+str(active)+'} end,get_workspace=function() return '+('{}' if exists else 'nil')+' end,get_workspace_windows=function() return '+('{}' if count==0 else '{{}}')+' end}\n'
  r=subprocess.run(['lua','-'],input=setup+lua,text=True,capture_output=True)
  assert (r.returncode==0)==ok,(active,exists,count,r.stderr)
print(f'SUPER+Tab: {len(CASES)} real controller/launcher cases + exact Lua guards, explicit acknowledgement before menu, lock released, no timers/polling/GUI; old navigation and cancellation preserved.')
