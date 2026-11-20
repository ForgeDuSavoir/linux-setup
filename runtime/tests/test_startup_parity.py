#!/usr/bin/env python3
"""R3 differential startup/main scenarios against R0, with fake exec/bar/logger."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from startup_fixture import Backend,initial,state
from test_desktop_parity import ROOT,ORACLES

BIN=ROOT/'target/release/session-startup'
ADMIN=ROOT/'target/release/agora-desktop-admin'

def cases():
    result={}
    def add(name,signatures=('one',),marker=None):
        w=initial(('A','B'),'B');w['active']=1;w['instance']='one'
        c={'world':w,'state':{'version':3,'order':[1,3],'owners':{'1':'A','3':'B'},'preferred':{},'next_id':40},'signatures':list(signatures),'marker':marker};result[name]=c;return c
    add('01_fresh')
    add('02_same_instance',('one','one'))
    add('03_relogin',('one','two'))
    add('04_deferred',('one',),{'version':1,'instance':'one','phase':'deferred'})
    add('05_failed',('one',),{'version':1,'instance':'one','phase':'failed'})
    c=add('06_compositors');c['world']['instances']=[{'instance':'one'},{'instance':'other'}]
    c=add('07_monitors');c['world']['monitors']=[{'focused':True},{'focused':False}]
    c=add('08_scoped');c['world']['clients'].append({'workspace':{'id':-9,'name':'special:sm-A-ai'}})
    c=add('09_global');c['world']['special']='special:global';c['world']['clients'].append({'workspace':{'id':-8,'name':'special:global'}})
    c=add('10_read_retry');c['world']['flags']['read_errors']=['transport.unavailable','transport.unavailable']
    c=add('12_read_no_retry');c['world']['flags']['read_errors']=['recovery.upgrade_required']
    c=add('13_uncertain_stop',('one','one'));c['world']['flags']['lost_reply']=True
    add('14_crashed',marker={'version':1,'instance':'one','phase':'initializing'})
    c=add('15_focus_fail',('one','one'));c['world']['flags']['fail_focus']=True
    c=add('16_silent_focus');c['world']['flags']['silent_focus']=True
    c=add('17_concurrent_session');c['world']['flags']['inject_session']=True
    add('18_invalid_marker',marker={})
    add('19_invalid_signature',('',))
    c=add('21_first_failure_bar_then_blocked',('one','one'));c['world']['flags']['read_errors']=['recovery.upgrade_required']
    add('22_bar_after_ready',('one','one'))
    c=add('fresh_race');c['world']['flags']['fresh_race']=True
    add('next_login_after_deferred',('two',),{'version':1,'instance':'one','phase':'deferred'})
    c=add('failed_stop',('one','one'));c['world']['flags']['fail_stop']=True
    return result

class Environment:
    def __init__(self,directory,data):
        self.root=Path(directory);self.data=copy.deepcopy(data);self.directory=self.root/'run/hyprland';self.directory.mkdir(parents=True)
        self.metadata=self.directory/'workspace-columns.json';self.metadata.write_text(json.dumps(data['state']))
        self.marker=self.directory/'session-startup.json'
        if data['marker'] is not None:self.marker.write_text(json.dumps(data['marker']))
        self.worldfile=self.root/'world';self.worldfile.write_text(json.dumps(self.data['world']));tools=self.root/'bin';tools.mkdir()
        for name,kind in [('hyprctl','native'),('manager','core'),('quickshell','bar'),('logger','log')]:
            target=tools/name;target.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom startup_fixture import cli\ncli('+repr(kind)+')\n');target.chmod(0o700)
        self.env={**os.environ,'HOME':str(self.root),'XDG_RUNTIME_DIR':str(self.root/'run'),'SESSION_MANAGER_BIN':str(tools/'manager'),'PATH':str(tools),'DESKTOP_WORLD':str(self.worldfile),'PYTHONDONTWRITEBYTECODE':'1','SESSION_COLUMNS_SCRIPT':str(ORACLES/'configs/hypr/files/Scripts/workspace-columns.py')}
    def result(self,world,answers):
        world=copy.deepcopy(world);world.pop('codes',None)
        backups=[]
        for directory in sorted(self.directory.glob('session-startup-backup-*')):
            backups.append({p.name:json.loads(p.read_text()) for p in directory.iterdir()})
        # Backup names differ; archive contents and creation count must agree.
        backups.sort(key=lambda d:json.dumps(d,sort_keys=True))
        return {'world':world,'answers':answers,'marker':json.loads(self.marker.read_text()) if self.marker.exists() else None,'state':json.loads(self.metadata.read_text()),'backups':backups}
    def rust(self):
        answers=[]
        for instance in self.data['signatures']:
            world=json.loads(self.worldfile.read_text());world['instance']=instance
            if instance!=world.get('_previous_instance',instance):world['active']=1
            world['_previous_instance']=instance;self.worldfile.write_text(json.dumps(world))
            r=subprocess.run([str(BIN)],env={**self.env,'HYPRLAND_INSTANCE_SIGNATURE':instance},capture_output=True,text=True,timeout=5);answers.append(r.returncode)
        return self.result(json.loads(self.worldfile.read_text()),answers)
    def oracle(self):
        b=Backend(self.data['world']);answers=[]
        with patch.dict(os.environ,self.env):
            spec=importlib.util.spec_from_file_location('r3_oracle',ORACLES/'configs/session-manager/session-startup.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        m.columns.RUNTIME=self.directory;m.columns.STATE=self.metadata;m.columns.query=b.query;m.columns.active=lambda:b.w['active'];m.columns.dispatch=lambda code:b.ctl('dispatch',code);m.columns.ctl=b.ctl;m.desktop.request=b.request
        def launch(binary,args):
            self.assert_bar(binary,args)
            b.w.setdefault('bar_phases',[]).append(json.loads(self.marker.read_text()).get('phase','invalid') if self.marker.exists() else 'absent')
            raise LookupError('fake exec')
        def log(*args,**kwargs):b.w['logs']=b.w.get('logs',0)+1
        for instance in self.data['signatures']:
            if instance!=b.w.get('_previous_instance',instance):b.w['active']=1
            b.w['instance']=instance;b.w['_previous_instance']=instance
            with patch.dict(os.environ,{**self.env,'HYPRLAND_INSTANCE_SIGNATURE':instance}),patch.object(m.sys,'argv',['session-startup']),patch.object(m.os,'execvp',side_effect=launch),patch.object(m.subprocess,'run',side_effect=log),patch.object(m.sys,'stderr'):
                try:answers.append(m.main())
                except LookupError:answers.append(0)
        return self.result(b.w,answers)
    @staticmethod
    def assert_bar(binary,args):assert (binary,args)==('quickshell',['quickshell'])

class Parity(unittest.TestCase):
    def test_cases(self):
        for name,data in cases().items():
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='r3-py-') as p,tempfile.TemporaryDirectory(prefix='r3-rust-') as r:
                self.assertEqual(Environment(p,data).oracle(),Environment(r,data).rust(),name)
        print(f'R3: {len(cases())} CLI/frozen startup scenarios passed (bar/logger are private fakes).')

if __name__=='__main__':unittest.main()
