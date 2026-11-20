#!/usr/bin/env python3
"""R2 real-CLI differential scenarios, including all prior stop/close behaviors."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from desktop_fixture import Backend,initial,state

ROOT=Path(__file__).resolve().parents[1]
ORACLES=ROOT.parent/'tools/runtime-migration/oracles'
BIN=ROOT/'target/release/session-desktop'

def cases():
    cases={}
    def add(name,args=('stop','B'),sessions=('A','B','C'),selected='B'):
        w=initial(sessions,selected);c={'world':w,'state':state(w),'actions':[list(args)]};cases[name]=c;return c
    add('s01_active_next')
    add('s02_wrap',('stop','C'),selected='C')
    c=add('s03_fresh_fallback');c['state']['order'].remove(4);c['state']['owners'].pop('4')
    c=add('s04_last',('stop','A'),('A',),'A');c['world']['special']='special:global'
    add('s05_last_inactive',('stop','A'),('A',),None)
    add('s06_unknown',('stop','missing'),('A',),'A')
    add('s07_inactive',('stop','A'))
    c=add('s08_normal_guard');c['world']['clients'].append({'workspace':{'id':3,'name':'3'}})
    c=add('s09_scoped_guard');c['world']['clients'].append({'workspace':{'id':-9,'name':'special:sm-B-ai'}})
    for name,flag in [('s10_switch_failure','fail_switch'),('s11_invalid_switch','invalid_switch'),('s12_focus_failure','fail_focus'),('s13_silent_focus','silent_focus'),('s14_late_window','late_window'),('s15_selection_race','after_focus_none'),('s16_stop_failure','fail_stop'),('s17_lost_reply','lost_reply'),('s18_after_stop_race','after_stop_none')]:
        c=add(name);c['world']['flags'][flag]=True
        if name=='s12_focus_failure':c['actions'].append(['stop','B'])
    add('q01_empty',('close','3'))
    c=add('q02_stale_focus',('close','3'));c['world']['window']={'address':'0xaa','workspace':{'id':2,'name':'2'}}
    c=add('q03_other_workspace',('close','3'));c['state']['order'].append(8);c['state']['owners']['8']='B';c['world']['clients'].append({'workspace':{'id':8,'name':'8'}})
    c=add('q04_hidden_scoped',('close','3'));c['world']['clients'].append({'workspace':{'id':-5,'name':'special:sm-B-notes'}})
    add('q05_last',('close','2'),('A',),'A')
    add('q06_unowned',('close','1'),selected=None)
    c=add('q07_mismatch',('close','2'));c['world']['active']=2
    c=add('q08_queued',('close','3'));c['actions'].append(['close','3'])
    c=add('q09_visible_window',('close','3'));c['world']['window']={'address':'0xaa','workspace':{'id':3,'name':'3'}}
    for flag,value in [('native_address','0xbb'),('native_ws',4),('native_invisible',True)]:
        c=add('q10_native_race_'+flag,('close','3'));c['world']['window']={'address':'0xaa','workspace':{'id':3,'name':'3'}};c['world']['flags'][flag]=value
    for special in ['special:sm-B-notes','special:global']:
        c=add('q11_visible_'+special,('close','3'));c['world']['special']=special;c['world']['window']={'address':'0xaa','workspace':{'id':-5,'name':special}}
    for special in ['special:sm-A-notes','special:global']:
        c=add('q12_unconfirmed_'+special,('close','3'));c['world']['special']=special
    c=add('q13_core_revision',('close','3'));c['world']['flags']['second_list_revision']=True
    c=add('q14_failed_focus',('close','3'));c['world']['flags']['fail_focus']=True
    # Previous close-suite case 15 executes the actual Lua binding; retained as
    # a separate regression below rather than silently counting it as a wire case.
    add('start_neutral',('start','--neutral'))
    add('start_project_literal',('start','--project','project with spaces; $(literal)'))
    add('switch',('switch','A'))
    add('deactivate',('deactivate',))
    add('status_confirmed',('status',))
    c=add('status_unconfirmed',('status',));c['world']['active']=2
    c=add('status_legacy',('status',));c['state']={'version':2,'owners':{'2':'B'}}
    c=add('status_missing',('status',));c['state']=None
    c=add('status_unknown_owner',('status',));c['state']['owners']['3']='absent'
    c=add('status_no_focus',('status',));c['world']['monitors']=[{'focused':False},{'focused':False}]
    c=add('status_other_focus',('status',));c['world']['monitors']=[{'focused':False},{'focused':True,'activeWorkspace':{'id':3}}]
    c=add('mutation_multi_monitor');c['world']['monitors']=[{'focused':True},{'focused':False}]
    uuid='12345678-1234-1234-1234-123456789abc'
    for special,owner,active in [('special:sm-'+uuid+'-ai','B','B'),('special:session-ai','B','B'),('special:global','B','B'),('','neutral',None)]:
        c=add('status_scope_'+special+'_'+owner,('status',),selected=active);c['world']['active']=3;c['world']['special']=special;c['state']['owners']['3']=owner
    return cases

class Environment:
    def __init__(self,directory,data):
        self.root=Path(directory);self.data=copy.deepcopy(data)
        self.directory=self.root/'run/hyprland';self.directory.mkdir(parents=True)
        self.metadata=self.directory/'workspace-columns.json'
        if self.data['state'] is not None:self.metadata.write_text(json.dumps(self.data['state']))
        self.file=self.root/'world';self.file.write_text(json.dumps(self.data['world']))
        tools=self.root/'bin';tools.mkdir()
        for name,kind in [('hyprctl','native'),('manager','core')]:
            script=tools/name;script.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom desktop_fixture import cli\ncli('+repr(kind)+')\n');script.chmod(0o700)
        self.env={**os.environ,'HOME':str(self.root),'XDG_RUNTIME_DIR':str(self.root/'run'),'SESSION_MANAGER_BIN':str(tools/'manager'),'PATH':str(tools),'DESKTOP_WORLD':str(self.file),'PYTHONDONTWRITEBYTECODE':'1'}
    def rust(self):
        answers=[]
        for argv in self.data['actions']:
            r=subprocess.run([str(BIN),*argv],env=self.env,capture_output=True,text=True,timeout=5)
            answers.append({'ok':r.returncode==0,'reply':json.loads(r.stdout) if r.returncode==0 else None})
        return self.result(answers,json.loads(self.file.read_text()))
    def oracle(self):
        backend=Backend(self.data['world'])
        with patch.dict(os.environ,{**self.env,'SESSION_COLUMNS_SCRIPT':str(ORACLES/'configs/hypr/files/Scripts/workspace-columns.py')}):
            spec=importlib.util.spec_from_file_location('r2_oracle',ORACLES/'configs/session-manager/session-desktop.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        m.columns.RUNTIME=self.directory;m.columns.STATE=self.metadata;m.columns.query=backend.query;m.columns.active=lambda:backend.w['active'];m.columns.focus=backend.focus;m.columns.focus_empty=backend.focus;m.columns.ctl=backend.ctl;m.columns.dispatch=lambda code:backend.ctl('dispatch',code);m.request=backend.request
        answers=[]
        for argv in self.data['actions']:
            try:
                if argv==['status']:reply=m.status()
                elif argv[:1]==['start']:reply=m.invoke('start',{'kind':'neutral'} if argv[1]=='--neutral' else {'kind':'project','project_name':argv[2]})
                else:reply=m.invoke(argv[0],int(argv[1]) if argv[0]=='close' and len(argv)>1 else argv[1] if len(argv)>1 else None)
                answers.append({'ok':True,'reply':reply})
            except (RuntimeError,ValueError,KeyError,subprocess.SubprocessError):answers.append({'ok':False,'reply':None})
        return self.result(answers,backend.w)
    def result(self,answers,world):
        world=copy.deepcopy(world);world.pop('codes',None)
        return {'answers':answers,'state':json.loads(self.metadata.read_text()) if self.metadata.exists() else None,'world':world}

class Differential(unittest.TestCase):
    def test_all_cases(self):
        for name,data in cases().items():
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='r2-python-') as p,tempfile.TemporaryDirectory(prefix='r2-rust-') as r:
                self.assertEqual(Environment(p,data).oracle(),Environment(r,data).rust(),name)
        print(f'R2: {len(cases())} real CLI / frozen Python differential scenarios passed.')

if __name__=='__main__':unittest.main()
