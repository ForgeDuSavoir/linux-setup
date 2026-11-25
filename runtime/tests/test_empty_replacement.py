#!/usr/bin/env python3
"""Private actual desktop CLI: replacement only after confirmed start, never switch."""
import importlib.util,tempfile,json
from pathlib import Path
p=Path(__file__).with_name('test_desktop_parity.py');s=importlib.util.spec_from_file_location('fixture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for mode in ['empty','project','occupied','other-workspace','hidden-special','late-window','late-other-workspace','focus-fail','silent-focus','selection-race','stop-fail','lost-stop','after-stop-race','no-active','mismatch','switch']:
 data=m.cases()['start_neutral'];w=data['world'];st=data['state'];flags=w['flags']
 if mode=='project':data['actions']=[['start','--project','literal ; project']]
 if mode=='occupied':w['clients'].append({'workspace':{'id':3,'name':'3'}})
 if mode=='other-workspace':
  st['order'].append(8);st['owners']['8']='B';w['clients'].append({'workspace':{'id':8,'name':'8'}})
 if mode=='late-other-workspace':
  st['order'].append(8);st['owners']['8']='B';flags['late_window']=True;flags['late_window_ws']=8
 if mode=='hidden-special':w['clients'].append({'workspace':{'id':-8,'name':'special:sm-B-notes'}})
 for name,flag in [('late-window','late_window'),('focus-fail','fail_focus'),('silent-focus','silent_focus'),('selection-race','after_focus_none'),('stop-fail','fail_stop'),('lost-stop','lost_reply'),('after-stop-race','after_stop_none')]:
  if mode==name:flags[flag]=True
 if mode=='no-active':w['selected']=None;w['active']=1
 if mode=='mismatch':w['active']=2
 if mode=='switch':data['actions']=[['switch','A']]
 with tempfile.TemporaryDirectory(prefix='empty-replacement-') as d:
  result=m.Environment(d,data).rust();world=result['world'];events=world['events'];stops=[e for e in events if e==['request',['stop','B']]]
  expected=mode in ['empty','project','stop-fail','lost-stop','after-stop-race']
  assert len(stops)==int(expected),(mode,result)
  if stops:assert next(i for i,e in enumerate(events) if e[0]=='focus')<events.index(stops[0])
  assert result['answers'][0]['ok']==(mode not in ['focus-fail','silent-focus','selection-race','stop-fail','lost-stop','after-stop-race']),(mode,result)
  if mode in ['empty','project']:assert 'B' not in world['sessions'] and world['selected']=='D'
  elif mode not in ['lost-stop','after-stop-race']:assert 'B' in world['sessions']
  assert all(e[1][1]=='B' for e in events if e[0]=='request' and e[1][0]=='stop'),'never remove unrelated inactive session'
print('16 empty-replacement cases: after-focus only, occupied normal/other/scoped/late windows, project/Neutral, no-active/mismatch/switch, failures/uncertain stop no replay; private CLI only.')
