#!/usr/bin/env python3
"""Real CLI, private lock + fake native; never reach a live compositor."""
import json,os,subprocess,tempfile,time,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BIN=ROOT/'target/release/workspace-controller'
HELPER=r'''#!/usr/bin/python3
import json,sys,os,re,fcntl,time
from pathlib import Path
h=Path(os.environ['HOME']);w=json.loads((h/'world').read_text());a=sys.argv[1:];name=a[0]
if name=='eval':
 code=a[1];epoch=int(re.search(r'navigation_epoch ~= (\d+)',code)[1])
 if w['epoch']!=epoch:print('error: stale event');sys.exit(1)
 if 'hl.dsp.focus' in code:
  (h/'code').write_text(code)
  assert w['active']==1 and (h/'gone').exists();w['active']=2;w['epoch']+=1;(h/'world').write_text(json.dumps(w));(h/'moved').touch()
 print('ok')
elif name=='clients':
 if not (h/'gone').exists() and b'closed-event' in Path('/proc/'+str(os.getppid())+'/cmdline').read_bytes():
  # If we are settling a still-present closing window, the common lock must be free.
  if not (h/'waiting').exists():
   with (h/'run/hyprland/workspace-columns.lock').open('a+b') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  (h/'waiting').touch()
  if w['mode']=='slow-child':time.sleep(4)
 rows=[] if (h/'gone').exists() else [{'address':'0xaa','workspace':{'id':1}}]
 rows.append({'address':'0xbb','workspace':{'id':2}})
 if w['mode']=='other':rows.append({'address':'0xcc','workspace':{'id':1}})
 print(json.dumps(rows))
elif name=='workspaces':print('[{"id":1},{"id":2}]')
elif name=='activeworkspace':print(json.dumps({'id':w['active']}))
elif name=='monitors':print(json.dumps([{'focused':True,'activeWorkspace':{'id':w['active']},'specialWorkspace':{'name':''}}]))
else:raise AssertionError(a)
'''
with tempfile.TemporaryDirectory(prefix='close-event-') as d:
 for mode in ['other','late','timeout','navigate','owner-change','slow-child']:
  h=Path(d)/mode;h.mkdir();b=h/'bin';b.mkdir();r=h/'run/hyprland';r.mkdir(parents=True)
  (b/'hyprctl').write_text(HELPER);(b/'hyprctl').chmod(0o700)
  w={'epoch':1,'active':1,'mode':mode};(h/'world').write_text(json.dumps(w))
  state={'version':3,'order':[1,2],'owners':{'1':'A','2':'A'},'preferred':{},'next_id':3};meta=r/'workspace-columns.json';meta.write_text(json.dumps(state));before=meta.read_bytes()
  env={'HOME':str(h),'PATH':str(b)+':/usr/bin:/bin',**{'XDG_'+k:str(h/v) for k,v in [('RUNTIME_DIR','run'),('STATE_HOME','state'),('CONFIG_HOME','config'),('DATA_HOME','data'),('CACHE_HOME','cache')]}}
  started=time.monotonic();p=subprocess.Popen([str(BIN),'closed-event','1','0xaa','1'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   deadline=time.monotonic()+3
   while not (h/'waiting').exists():assert p.poll() is None;assert time.monotonic()<deadline;time.sleep(.005)
   with (r/'workspace-columns.lock').open('a+b') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if mode not in ['other','timeout','slow-child']:
    # Real navigation command can acquire the common lock while closing waits.
    nav=subprocess.run([str(BIN),'snapshot'],env=env,capture_output=True,text=True,timeout=1);assert nav.returncode==0,nav.stderr
    if mode=='navigate':w['epoch']=3;(h/'world').write_text(json.dumps(w)) # navigated away and back
    if mode=='owner-change':state['owners']['1']='B';meta.write_text(json.dumps(state))
    (h/'gone').touch()
   out,err=p.communicate(timeout=4);elapsed=time.monotonic()-started
   assert (h/'moved').exists()==(mode=='late'),(mode,err)
   if mode=='late':
    assert p.returncode==0
    lua=(h/'code').read_text()
    # Duplicate event invalidated by the focus epoch, no second focus.
    q=subprocess.run([str(BIN),'closed-event','1','0xaa','1'],env=env,capture_output=True);assert q.returncode!=0
   if mode=='other':assert elapsed<1 and meta.read_bytes()==before,(elapsed,err)
   if mode in ['timeout','slow-child']:assert elapsed<2.7 and meta.read_bytes()==before,(mode,elapsed,err)
   if mode=='navigate':assert meta.read_bytes()==before
   print(mode,'elapsed ms',round(elapsed*1000,1),'lock acquirable during settlement')
  finally:
   if p.poll() is None:p.kill();p.wait()
for epoch,active,source_count,target_count,target_exists,special,ok in [(1,1,0,1,True,False,True),(2,1,0,1,True,False,False),(1,2,0,1,True,False,False),(1,1,1,1,True,False,False),(1,1,0,0,True,False,False),(1,1,0,1,False,False,False),(1,1,0,1,True,True,False)]:
 setup=f'''_G.__workflow_navigation_epoch={epoch};local calls=0
hl={{get_active_workspace=function() return {{id={active}}} end,get_active_special_workspace=function() return {'{id=-1}' if special else 'nil'} end,get_monitors=function() return {{{{}}}} end,get_workspace=function(id) if id==2 and {'false' if target_exists else 'true'} then return nil end return {{id=id}} end,get_workspace_windows=function(id) local r={{}} for i=1,(id==1 and {source_count} or {target_count}) do r[i]={{}} end return r end,dsp={{focus=function() return {{}} end}},dispatch=function() calls=calls+1 end}}
'''
 r=subprocess.run(['lua','-'],input=setup+lua+'\nassert(calls==1)',text=True,capture_output=True);assert (r.returncode==0)==ok,r.stderr
print('Close-event address settlement, other-window immediate return, private lock concurrency, delayed disappearance, stale/duplicate/owner change and bounded child/timeout passed; no live GUI.')
