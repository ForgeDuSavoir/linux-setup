#!/usr/bin/env python3
"""Current Shift+S contract; in-memory native fixture plus exact Lua guard execution."""
import importlib.util,json,subprocess
from pathlib import Path
p=Path(__file__).with_name('test_workspace_parity.py');spec=importlib.util.spec_from_file_location('fixture',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def run(c):return json.loads(subprocess.check_output([str(m.FIXTURE)],input=json.dumps(c),text=True,timeout=5))
for mode in ['last-shared','last-single','only-shared','only-single','not-last','reordered','reject','lost']:
 c=m.scenario('move-next');w=c['world'];s=c['state']
 if mode in ['only-shared','only-single']:
  s['order']=[1];s['owners']={'1':'A'};w['ws']=[1];w['clients']=[m.client('a',1)];w['active']=1;w['focused']='a'
 elif mode=='reordered':s['order']=[2,8,1]
 elif mode!='not-last':w['active']=2;w['focused']='b'
 if mode in ['last-shared','only-shared','reject','lost','reordered']:
  w['clients'].append(m.client('d',w['active']));w['focused']='d'
 if mode in ['reject','lost']:w['failure']=mode
 a=run(c);assert a['ok']==(mode not in ['reject','lost']),(mode,a)
 moves=[e for e in a['world']['events'] if e[0]=='move']
 if mode=='only-single':assert not moves
 elif mode=='reject':assert not moves and 9 not in a['state']['order']
 else:
  target=9 if mode in ['last-shared','only-shared','reordered','lost'] else 1 if mode=='last-single' else 2
  assert len(moves)==1 and moves[0][1]==target,(mode,a)
  assert a['world']['active']==target
  if mode!='lost':assert a['state']['owners'][str(target)]=='A'
  else:assert len(a['codes'])==1,'uncertain transfer must not be replayed'
  assert all(e[1]!=8 for e in moves),'never transfer across owners'
  if mode=='last-single':assert 2 not in a['state']['order'],'empty source pruned'
  if mode=='last-shared':shared=a['codes'][0][1]
  if mode=='last-single':single=a['codes'][0][1]
# Execute actual generated guards with synthetic compositor objects; no real Lua IPC.
for code,is_shared in [(shared,True),(single,False)]:
 source=2;target=9 if is_shared else 1
 for count,active,window_ws,existing,ok in [(2 if is_shared else 1,2,2,not is_shared,True),(1 if is_shared else 2,2,2,not is_shared,False),(2 if is_shared else 1,1,2,not is_shared,False),(2 if is_shared else 1,2,8,not is_shared,False),(2 if is_shared else 1,2,2,is_shared,False)]:
  setup='''local moved=nil
hl={get_workspace=function(id) if id==2 or EXIST then return {id=id} end end,
 get_active_workspace=function() return {id=ACTIVE} end,
 get_window=function() return {workspace={id=WINDOW_WS}} end,
 get_workspace_windows=function() local r={} for i=1,COUNT do r[i]={} end return r end,
 dispatch=function() end,dsp={window={move=function(args) moved=args.workspace return {} end}}}
'''.replace('EXIST','true' if existing else 'false').replace('ACTIVE',str(active)).replace('WINDOW_WS',str(window_ws)).replace('COUNT',str(count))
  r=subprocess.run(['lua','-'],input=setup+code+'\nassert(moved=='+str(target)+')',capture_output=True,text=True)
  assert (r.returncode==0)==ok,(is_shared,count,active,window_ws,existing,r.stderr)
print('Shift+S: 8 current policy cases, exact Lua count/source/target guards, owner order, singleton no-op, empty cleanup, failure/no replay passed; no live windows.')
