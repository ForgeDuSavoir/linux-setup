#!/usr/bin/env python3
"""Real native orchestrator/launcher, fake compositor/apps, all HOME/XDG paths private."""
import json,os,re,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROLLER=Path(os.environ.get('SHIFT_TEST_CONTROLLER',str(ROOT/'target/release/workspace-controller')))
LAUNCHER=ROOT.parent/'configs/session-manager/app-launcher/target/release/session-app-launcher'
OWNER='11111111-1111-1111-1111-111111111111'
HELPER=r'''#!/usr/bin/python3
import json,os,sys,re,fcntl
from pathlib import Path
h=Path(os.environ['HOME']);p=h/'world';w=json.loads(p.read_text());tool=Path(sys.argv[0]).name;a=sys.argv[1:]
def save():p.write_text(json.dumps(w))
def log(x):
 with (h/'trace').open('a') as f:f.write(json.dumps(x)+'\n')
def sessions():return {'sessions':[{'id':w['owner'],'source':{'kind':'project','project_name':'P'} if w['project'] else {'kind':'neutral'}}] if w['owner']!='neutral' else [],'active_session_id':None if w['owner']=='neutral' else w['owner'],'revision':0}
def check_lock():
 with (h/'runtime/hyprland/workspace-columns.lock').open('a+b') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
log([tool,a])
if tool=='session-obsidian':
 if a==['--version']:print('old' if w['mode']=='old-vault' else 'session-obsidian [expected-vault-v1]')
 elif a==['--print-uri']:
  if w['mode']=='missing-vault':sys.exit(1)
  print('obsidian://open?vault=0123456789abcdef')
 else:
  assert a==['--expected-workspace','3',w['owner'],'--expected-uri','obsidian://open?vault=0123456789abcdef']
  assert w['active']==3 and 'HL_INITIAL_WORKSPACE_TOKEN' not in os.environ
  check_lock()
  (h/'launches').write_text(json.dumps([tool,a,w['active'],None])+'\n')
elif tool=='session-desktop':
 assert a==['status'];w['status_calls']=w.get('status_calls',0)+1
 if w['mode']=='switch-planning' and w['status_calls']==3:w['active']=2;w['ws'].append(2)
 save();print(json.dumps({**sessions(),'displayed_context':w['owner'],'context_confirmed':w['mode']!='unconfirmed'}))
elif tool=='hyprctl':
 a=[x for x in a if x!='-j'];name=a[0]
 if name in ['eval','dispatch']:
  code=a[1]
  if 'new empty workspace is not active' in code:
   target=int(re.search(r'get_workspace\((\d+)\)',code)[1]);assert target==w['active']
   if w['mode']=='confirm-error':print('error: not confirmed');sys.exit(7)
   if w['mode']=='switch-after-confirm':w['active']=1
   if w['mode']=='project-directory-race':
    (h/'Project ; literal').rename(h/'moved');(h/'Project ; literal').mkdir()
   save();print('ok')
  else:
   target=int(re.search(r'workspace\s*=\s*(\d+)',code)[1]);assert 'source workspace changed before creation' in code
   if w['mode']=='source-race' or w['mode']=='collision':print('error: guarded source/target changed');sys.exit(7)
   w['active']=target;w['ws'].append(target);save()
   if w['mode']=='lost':print('error: uncertain reply');sys.exit(7)
   print('ok')
 elif name=='activeworkspace':print(json.dumps({'id':w['active']}))
 elif name=='workspaces':print(json.dumps([{'id':v} for v in w['ws']]))
 elif name=='clients':print(json.dumps([{'address':'0xaa','workspace':{'id':v}} for v in w['occupied']]))
 elif name=='monitors':print(json.dumps([{'focused':True,'activeWorkspace':{'id':w['active']},'specialWorkspace':{'name':w['special']}}]*(2 if w['mode']=='multi-monitor' else 1)))
 else:raise AssertionError(a)
elif tool=='session-manager':
 assert a[0]=='--json'
 if a[1:]==['session','list']:print(json.dumps(sessions()))
 elif a[1:]==['project','list']:print(json.dumps({'projects':[{'name':'P','path':str(h/'Project ; literal')}]}))
 elif a[1:]==['application','list']:
  if w['mode']=='switch-before-browser-launch':w['active']=1;save()
  print(json.dumps({'applications':[{'id':w['app'],'name':'Test','origin':'installed'}]}))
 else:raise AssertionError(a)
elif tool=='agora-notify':assert a==['capture'];print('neutral' if w['owner']=='neutral' else 'session:'+w['owner'])
elif tool=='xdg-mime':assert a==['query','default','inode/directory'];print('other.desktop' if w['mode']=='other-file-manager' else 'thunar.desktop')
elif tool=='rofi':
 check_lock();sys.stdin.read()
 if w['mode']=='cancel':sys.exit(1)
 if w['mode']=='switch-during-menu':w['active']=1;save()
 print('0')
elif tool in ['kitty','thunar','xdg-open','launch-terminal-command','gtk-launch','fake-browser']:
 check_lock()
 assert 'HL_INITIAL_WORKSPACE_TOKEN' not in os.environ,'stale original-workspace token reached application'
 with (h/'launches').open('a') as f:f.write(json.dumps([tool,a,w['active'],os.environ.get('AGORA_NOTIFICATION_CONTEXT')])+'\n')
 if w['mode']=='app-fail':sys.exit(7)
else:raise AssertionError(tool)
'''
def inside():
 timings=[]
 cases=[(t,m) for t in ['browser','pi','files','terminal','apps','youtube','obsidian'] for m in ['created','empty','unowned','project']]
 cases += [('apps',m) for m in ['cancel','switch-during-menu','source-race','collision','lost','confirm-error','switch-after-confirm','switch-planning','missing-launcher','old-launcher','unconfirmed','scratchpad','multi-monitor']]
 cases += [('files','other-file-manager'),('files','app-fail'),('browser','browser-action'),('browser','old-launcher'),('browser','switch-before-browser-launch'),('pi','project-directory-race'),('files','project-directory-race'),('obsidian','old-vault'),('obsidian','missing-vault'),('obsidian','switch-after-confirm'),('youtube','switch-after-confirm')]
 with tempfile.TemporaryDirectory(prefix='new-workspace-') as d:
  for target,mode in cases:
   h=Path(d)/(target+'-'+mode);h.mkdir();b=h/'bin';b.mkdir();local=h/'.local/bin';local.mkdir(parents=True);runtime=h/'runtime/hyprland';runtime.mkdir(parents=True)
   owner='neutral' if mode=='unowned' else OWNER
   w={'mode':mode,'owner':owner,'active':1,'ws':[1],'occupied':[] if mode=='empty' else [1],'special':'special:global' if mode=='scratchpad' else '', 'project':mode in ['project','project-directory-race'],'app':'firefox.desktop' if target in ['browser','youtube'] else 'test.desktop'}
   (h/'world').write_text(json.dumps(w));(runtime/'workspace-columns.json').write_text(json.dumps({'version':3,'order':[1],'owners':{'1':owner},'preferred':{},'next_id':3}))
   for tool in ['hyprctl','session-manager','session-desktop','agora-notify','xdg-mime','rofi','kitty','thunar','xdg-open','launch-terminal-command','gtk-launch','fake-browser','pi','session-obsidian']:
    p=(local if tool in ['session-manager','session-desktop','agora-notify','launch-terminal-command','fake-browser','session-obsidian'] else b)/tool;p.write_text(HELPER);p.chmod(0o700)
   if mode!='missing-launcher':
    p=local/'session-app-launcher'
    if mode=='old-launcher':p.write_text('#!/bin/sh\necho old\n');p.chmod(0o700)
    else:p.symlink_to(LAUNCHER)
   for folder in ['Agora ; literal','Project ; literal']: (h/folder).mkdir()
   cfg=h/'config/agora-workflow';cfg.mkdir(parents=True);(cfg/'config.toml').write_text('agora_root = '+json.dumps(str(h/'Agora ; literal'))+'\n')
   apps=h/'data/applications';apps.mkdir(parents=True)
   desktop='[Desktop Entry]\nType=Application\nName=Test\nExec=/usr/bin/true\n'
   if mode=='browser-action':desktop+='Actions=new-window;\n[Desktop Action new-window]\nName=New Window\nExec=fake-browser --new-window\n'
   if target=='youtube':desktop='[Desktop Entry]\nType=Application\nName=Browser\nExec='+str(local/'fake-browser')+' %u\n'
   (apps/w['app']).write_text(desktop)
   env={'HOME':str(h),'XDG_RUNTIME_DIR':str(h/'runtime'),'XDG_CONFIG_HOME':str(h/'config'),'XDG_DATA_HOME':str(h/'data'),'XDG_DATA_DIRS':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'XDG_CACHE_HOME':str(h/'cache'),'PATH':str(b)+':/usr/bin:/bin','DBUS_SESSION_BUS_ADDRESS':os.environ['DBUS_SESSION_BUS_ADDRESS'],'HL_INITIAL_WORKSPACE_TOKEN':'synthetic-original-workspace-token'}
   started=time.monotonic()
   r=subprocess.run([str(CONTROLLER),'open-new',target],env=env,capture_output=True,text=True,timeout=15)
   if target=='terminal' and mode in ['created','empty','unowned','project']:timings.append((time.monotonic()-started)*1000)
   success=mode in ['created','empty','unowned','project','cancel','other-file-manager','browser-action']
   assert (r.returncode==0)==success,(target,mode,r.stderr)
   # GIO desktop action intentionally has no synchronous spawn acknowledgement.
   if mode=='browser-action' or target=='youtube' and success:
    end=time.monotonic()+3
    while not (h/'launches').exists() and time.monotonic()<end:time.sleep(.01)
   launches=[json.loads(x) for x in (h/'launches').read_text().splitlines()] if (h/'launches').exists() else []
   expected_launch=mode in ['created','empty','unowned','project','other-file-manager','browser-action','app-fail']
   assert bool(launches)==expected_launch,(target,mode,r.stderr,launches)
   assert len(launches)<=1
   if launches:
    tool,args,ws,origin=launches[0];assert ws==3,(target,mode,launches)
    if target=='pi':
     directory=h/('Project ; literal' if mode=='project' else 'Agora ; literal')
     assert args==[str(directory),'env','AGORA_NOTIFICATION_CONTEXT='+('neutral' if owner=='neutral' else 'session:'+owner),'pi','--continue']
    if target=='files':assert tool=='xdg-open' and args==[str(h/'Project ; literal' if mode=='project' else h)]
    if mode=='browser-action':assert tool=='fake-browser' and args==['--new-window']
    state=json.loads((runtime/'workspace-columns.json').read_text());assert state['owners']['3']==owner
   trace=[json.loads(x) for x in (h/'trace').read_text().splitlines()]
   creates=[x for x in trace if x[0]=='hyprctl' and len(x[1])>1 and 'source workspace changed before creation' in x[1][1]]
   assert len(creates)==(0 if mode in ['missing-launcher','old-launcher','unconfirmed','scratchpad','multi-monitor','switch-planning','old-vault','missing-vault'] else 1),(target,mode,creates)
   assert not any(x[0] in ['thunar','xdg-mime'] for x in trace),'file manager must be system-default, not specialized'
   assert not list((h/'state').rglob('*.json')),'no Shift history writes'
   assert not list(h.rglob('app-usage.json')),'no project Shift usage counter'
   if target in ['browser','youtube']:
    assert not (h/'state').exists(),'browser must not touch history locks/store'
    assert not (h/'Project ; literal/.session-manager').exists(),'browser must not create project history/exclusions'
   if mode=='created' and target=='apps':lua=creates[0][1][1]
  # Run exact atomic source/target guard, not merely a fake compositor interpretation.
  for active,special,nmon,exists,ok in [(1,False,1,False,True),(2,False,1,False,False),(1,True,1,False,False),(1,False,2,False,False),(1,False,1,True,False)]:
   setup='hl={get_active_workspace=function() return {id='+str(active)+'} end,get_active_special_workspace=function() return '+('{id=-1}' if special else 'nil')+' end,get_monitors=function() return '+('{}' if nmon==0 else '{{}}' if nmon==1 else '{{},{}}')+' end,get_workspace=function() return '+('{}' if exists else 'nil')+' end,dispatch=function() end,dsp={focus=function() end}}\n'
   r=subprocess.run(['lua','-'],input=setup+lua,text=True,capture_output=True);assert (r.returncode==0)==ok,(active,special,nmon,exists,r.stderr)
 print('Private terminal request milliseconds:',json.dumps(timings))
 print(f'New workspace: {len(cases)} real orchestrator/launcher cases + exact Lua source guards; seven routes, empty source, owners/context, lock release, literal paths, no stats/browser history, new-window action, refusal/races/no replay; no live GUI/core/media.')
if __name__=='__main__':
 import sys
 if sys.argv[1:]==['--inside']:inside()
 else:sys.exit(subprocess.run(['dbus-run-session','--','/usr/bin/python3',str(Path(__file__).resolve()),'--inside'],env={**{'PATH':'/usr/bin:/bin'},**({'SHIFT_TEST_CONTROLLER':os.environ['SHIFT_TEST_CONTROLLER']} if 'SHIFT_TEST_CONTROLLER' in os.environ else {})},timeout=180).returncode)
