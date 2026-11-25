#!/usr/bin/env python3
"""R1 differential cases against frozen R0; Rust fixture calls the real library.
All native operations are in-memory. No real compositor/daemon can be reached.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT.parent/'tools/runtime-migration/oracles/configs/hypr/files/Scripts/workspace-columns.py'
FIXTURE = ROOT/'target/release/examples/workspace-fixture'

def client(address,ws):return {'address':address,'workspace':{'id':ws,'name':str(ws)}}
def scenario(*ops):
    return {'state':{'version':3,'order':[1,2,8],'owners':{'1':'A','2':'A','8':'B'},'preferred':{},'next_id':9},
            'world':{'active':1,'focused':'a','clients':[client('a',1),client('b',2),client('c',8)],'ws':[1,2,8],'other_visible':[],'events':[]},
            'steps':[{'op':op} if isinstance(op,str) else op for op in ops]}

class Oracle:
    def __init__(self,data,root):
        self.data=copy.deepcopy(data);self.world=self.data['world'];self.sleeps=0;self.saves=0
        spec=importlib.util.spec_from_file_location('r1_frozen',ORACLE);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        m=self.m;m.RUNTIME=root;m.STATE=root/'state.json';self.codes=[]
        if data.get('raw') is not None:m.STATE.write_text(json.dumps(data['raw']))
        m.query=self.query;m.focus=lambda ws:self.act(ws,None,False);m.focus_empty=lambda ws:self.act(ws,None,True)
        m.move=lambda ws,address,**kw:self.act(ws,address,False);m.move_empty=lambda ws,address:self.act(ws,address,True)
        m.dispatch=self.dispatch;m.ctl=lambda *args:(_ for _ in ()).throw(AssertionError('unexpected native IO'))
        self.sleep=m.time.sleep;m.time.sleep=lambda seconds:setattr(self,'sleeps',self.sleeps+1)
        save=m.save
        def checked(state):
            self.saves+=1
            if self.saves==data.get('fail_save'):raise RuntimeError('injected write failure')
            save(state)
        m.save=checked
    def query(self,name):
        w=self.world
        if w.get('fail_query')==name:raise RuntimeError('injected query failure')
        if name=='clients':return copy.deepcopy(w['clients'])
        if name=='activeworkspace':return {'id':w['active']}
        if name=='activewindow':return next((copy.deepcopy(c) for c in w['clients'] if c['address']==w['focused']),{})
        if name=='workspaces':return [{'id':ws} for ws in sorted(w['ws'])]
        if name=='monitors':return copy.deepcopy(w.get('monitors',[{'focused':True,'activeWorkspace':{'id':w['active']},'specialWorkspace':{'name':w.get('special','')}}]+[{'focused':False,'activeWorkspace':{'id':ws},'specialWorkspace':{'name':''}} for ws in w['other_visible']]))
        raise AssertionError(name)
    def prune(self):
        w=self.world;w['ws']=sorted({w['active'],*w['other_visible'],*(c['workspace']['id'] for c in w['clients'] if c['workspace']['id']>0)})
    def dispatch(self,code):
        assert 'toggle_special' in code
        self.world['events'].append(['hide',code]);self.world['special']=''
    def act(self,ws,address,fresh):
        w=self.world;mode=w.get('failure','')
        if fresh and (ws in w['ws'] or mode=='race'):raise RuntimeError('workspace target already exists')
        if mode=='reject':raise RuntimeError('injected native rejection')
        if address:
            self.world['events'].append(['move',ws,address]);c=next(c for c in w['clients'] if c['address']==address);c['workspace']={'id':ws,'name':str(ws)}
        w['events'].append(['focus',ws]);w['active']=ws;w['focused']=next((c['address'] for c in w['clients'] if c['workspace']['id']==ws),None);self.prune()
        if mode=='lost':raise RuntimeError('lost acknowledgement')
    def run(self):
        m=self.m;state=None;output=None;ok=False
        try:
            state=m.project_state(self.data.get('state'),set(self.world['ws']))
            for step in self.data['steps']:
                op=step['op']
                if op=='project':output=state;break
                if op in ('read','load'):state=(m.read_state if op=='read' else m.load)();continue
                if op=='snapshot':output=m.snapshot();break
                if op=='run':
                    args=step['args']
                    # Full executable semantics, without actual stdout parsing.
                    with patch('sys.argv',[str(ORACLE),*args]):m.main()
                    break
                if op=='fresh':m.fresh_workspace(state,'A',after=step.get('ws',1))
                elif op=='closed':m.closed(state,step.get('ws',1))
                else:getattr(m,op.replace('-','_'))(state)
            ok=True
        except (RuntimeError,ValueError,KeyError,SystemExit):pass
        finally:m.time.sleep=self.sleep
        return {'ok':ok,'output':output,'state':state,'raw':json.loads(m.STATE.read_text()) if m.STATE.exists() else None,'world':self.world,'sleeps':self.sleeps}

def cases():
    result={}
    def add(name,*ops):
        c=scenario(*ops);result[name]=c;return c
    c=add('01_legacy_projection','project');c['state']={'version':2,'owners':{'1':'A','2':'B','3':'C'},'last':{'1':2,'3':2},'preferred':{'A':1,'B':2,'C':3},'origins':{'a':1}};c['world']['ws']=[1,2,3]
    c=add('02_missing_legacy_special','load');c['state']=None;c['world']['clients'].append(client('d',-90))
    add('03_insert_order','create-empty')
    add('04_repeated_toggle_and_fresh_id','create-empty','create-empty','create-empty')
    c=add('05_empty_preceding_order','create-empty');c['world']['active']=9;c['world']['focused']=None;c['world']['ws'].append(9);c['state']['order']=[2,1,8,9];c['state']['owners']['9']='A';c['state']['next_id']=10
    c=add('06_empty_first_no_wrap','create-empty');c['world']['clients'].pop(0)
    c=add('07_only_empty_owner','create-empty');c['world']['clients'].pop(0);c['state']['owners']['2']='B';c['state']['order']=[2,8,1]
    c=add('08_empty_predecessor_visible','create-empty');c['world']['active']=2;c['world']['clients']=[client('c',8)];c['world']['other_visible']=[1]
    add('09_cycle_discards_empty','create-empty','cycle','cycle')
    c=add('10_external_cleanup','cleanup');c['state']['order'].append(9);c['state']['owners']['9']='only-empty';c['state']['preferred']={'only-empty':9};c['world']['active']=8
    c=add('11_other_monitor_empty','cleanup');c['world']['other_visible']=[9];c['world']['ws'].append(9);c['state']['order'].append(9);c['state']['owners']['9']='B'
    c=add('12_close_previous',{'op':'closed','ws':2});c['world']['active']=2;c['world']['clients'].pop(1)
    c=add('13_close_final_keeps_visible','closed');c['world']['clients']=[client('c',8)]
    c=add('14_inactive_close',{'op':'closed','ws':2});c['world']['clients'].pop(1);c['world']['ws']=[1,8]
    add('15_other_windows_noop','closed')
    c=add('16_isolate_then_previous','isolate-or-previous','isolate-or-previous');c['world']['clients'].append(client('d',1));c['world']['focused']='d'
    add('17_first_previous_no_wrap','isolate-or-previous')
    c=add('18_previous_explicit_order','isolate-or-previous');c['state']['order']=[2,8,1]
    c=add('19_no_previous_occupied','isolate-or-previous');c['world']['clients'].pop(0);c['world']['active']=2;c['world']['focused']='b';c['world']['other_visible']=[1]
    c=add('20_previous_skip_visible_empty','isolate-or-previous');c['world']['active']=2;c['world']['focused']='b';c['world']['other_visible']=[9];c['world']['ws'].append(9);c['state']['order']=[1,9,2,8];c['state']['owners']['9']='A'
    c=add('21_next_multiple','move-next');c['world']['clients'].append(client('d',1));c['world']['focused']='d'
    c=add('22_next_wrap','move-next');c['world']['active']=2;c['world']['focused']='b'
    c=add('23_next_explicit_order','move-next');c['state']['order']=[2,8,1]
    c=add('24_next_visible_empty','move-next');c['world']['other_visible']=[9];c['world']['ws'].append(9);c['state']['order']=[1,9,2,8];c['state']['owners']['9']='A'
    c=add('25_missing_window','move-next','isolate-or-previous');c['world']['focused']=None
    c=add('26_retired_origins','project');c['state']['origins']={'stale':999}
    c=add('27_lone_owner','move-next');c['state']['owners']['2']='B'
    c=add('28_snapshot_legacy','snapshot');c['raw']={'version':2,'owners':{'1':'A','4':'B'},'last':{},'preferred':{},'origins':{}}
    c=add('29_no_adoption','load');c['raw']=copy.deepcopy(c['state']);c['world']['clients'].append(client('d',6));c['world']['ws'].append(6)
    c=add('30_id_exhaustion','fresh');c['state']['next_id']=2147483647
    c=add('31_native_race','create-empty');c['world']['failure']='race'
    c=add('32_uncertain_focus','create-empty');c['world']['failure']='lost'
    c=add('33_isolation_race','isolate-or-previous');c['world']['clients'].append(client('d',1));c['world']['focused']='d';c['world']['failure']='race'
    add('34_guarded_focus','create-empty')
    c=add('35_guarded_move','isolate-or-previous');c['world']['clients'].append(client('d',1));c['world']['focused']='d'
    for command in ['toggle-row','move-row','focus-column']:
        add('36_removed_'+command,{'op':'run','args':[command]})
    c=add('invalid_duplicate_order','project');c['state']['order']=[1,1,8]
    c=add('invalid_bool_id','project');c['state']['next_id']=True
    c=add('invalid_schema','project');c['state']['version']=7
    c=add('invalid_preferred','project');c['state']['preferred']={'B':1}
    c=add('missing_state_snapshot','snapshot');c['state']=None
    c=add('unknown_fields_retained','project');c['state']['future']={'x':'value'}
    for operation in ['move-next','isolate-or-previous']:
        c=add('special_window_'+operation,operation);c['world']['clients'].append(client('d',-9));c['world']['focused']='d'
    for name in ['global','session-ai','sm-12345678-1234-1234-1234-123456789abc-notes']:
        for command in [['cycle'],['create-empty'],['focus-workspace','2']]:
            c=add('hide_'+name+'_'+command[0],{'op':'run','args':command});c['world']['special']='special:'+name
    c=add('unsafe_special',{'op':'run','args':['cycle']});c['world']['special']='special:bad"name'
    c=add('write_failure_before_dispatch','create-empty');c['fail_save']=1
    c=add('native_query_failure','cycle');c['world']['fail_query']='clients'
    c=add('snapshot_current_empty','snapshot');c['raw']=copy.deepcopy(c['state']);c['world']['clients'].pop(0)
    c=add('uncertain_isolation','isolate-or-previous');c['world']['clients'].append(client('d',1));c['world']['focused']='d';c['world']['failure']='lost'
    c=add('write_failure_before_fresh_focus','create-empty');c['fail_save']=2
    return result

class Parity(unittest.TestCase):
    def test_all(self):
        all_cases=cases()
        for name,data in all_cases.items():
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='r1-oracle-') as directory:
                reference=Oracle(data,Path(directory)).run()
                actual=json.loads(subprocess.check_output([str(FIXTURE)],input=json.dumps(data),text=True,timeout=3))
                # Invalid projections leave the unvalidated Python raw object in a
                # local variable, whereas Rust returns no typed state. No IO happened.
                if not reference['ok'] and not actual['ok'] and reference['state'] is None:actual['state']=None
                if name=='15_other_windows_noop':
                    self.assertEqual(actual['sleeps'],0)
                    reference['sleeps']=0 # Explicit CLOSE-WAIT-001 fix; frozen oracle unchanged.
                for key in ['ok','output','raw','world','sleeps']:
                    self.assertEqual(actual[key],reference[key],(name,key,actual.get('error')))
                if reference['ok'] or reference['raw'] is not None:
                    self.assertEqual(actual['state'],reference['state'],name)
                # Actual Rust fresh guards must be single eval, not animation changes.
                for kind,code in actual['codes']:
                    self.assertNotIn('hl.animation',code)
                    if kind=='eval':
                        self.assertLess(code.index('hl.get_workspace'),code.index('hl.dispatch'))
        print(f'Rust/frozen Python: {len(all_cases)} differential scenarios passed.')

if __name__=='__main__':unittest.main()
