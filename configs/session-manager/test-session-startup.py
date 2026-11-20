#!/usr/bin/env python3
"""New-login policy with fake core/native APIs and private runtime roots only."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
os.environ['SESSION_COLUMNS_SCRIPT'] = str(HERE.parent/'hypr/files/Scripts/workspace-columns.py')


class Fixture:
    def __init__(self, root):
        spec=importlib.util.spec_from_file_location('startup_test',HERE/'session-startup.py')
        self.m=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.root=root; self.instance='instance-one'; self.active=1; self.selected='B'
        self.sessions=[{'id':'A'},{'id':'B'}]; self.calls=[]; self.generation=0
        self.clients=[{'address':'fixture','workspace':{'id':1,'name':'1'}}]
        self.monitor={'focused':True,'activeWorkspace':{'id':1},'specialWorkspace':{'name':''}}
        self.instances=None; self.monitors=None; self.stop_error=None; self.lost_stop=False
        self.focus_error=False; self.silent_focus=False; self.read_errors=[]; self.inject_session=False
        self.m.columns.RUNTIME=root; self.m.columns.STATE=root/'state.json'
        self.m.columns.save({'version':3,'order':[1,3],'owners':{'1':'A','3':'B'},'preferred':{},'next_id':40})
        self.m.columns.query=self.query; self.m.columns.active=lambda:self.active
        self.m.columns.focus_empty=self.focus
        self.m.columns.focus=lambda *_:(_ for _ in ()).throw(AssertionError('must allocate a fresh target'))
        self.m.columns.dispatch=self.dispatch; self.m.columns.ctl=lambda *_:(_ for _ in ()).throw(AssertionError('no real compositor'))
        self.m.desktop.request=self.request

    def query(self,name):
        self.calls.append(('native',name))
        if name=='instances': return self.instances if self.instances is not None else [{'instance':self.instance}]
        if name=='monitors': return self.monitors if self.monitors is not None else [self.monitor]
        if name=='clients': return self.clients
        if name=='workspaces': return [{'id':ws} for ws in {1,self.active}]
        raise AssertionError(name)

    def dispatch(self,expression):
        assert expression.startswith('hl.dsp.workspace.toggle_special('),expression
        self.calls.append(('hide',)); self.monitor['specialWorkspace']['name']=''

    def focus(self,ws):
        self.calls.append(('focus',ws))
        if self.focus_error: raise RuntimeError('native focus failed')
        if not self.silent_focus: self.active=ws; self.monitor['activeWorkspace']['id']=ws

    def request(self,*args,**kwargs):
        self.calls.append(('core',*args))
        if args==('list',):
            if self.read_errors: raise self.read_errors.pop(0)
            return {'sessions':list(self.sessions),'active_session_id':self.selected}
        if args[0]=='stop':
            if self.stop_error: raise RuntimeError(self.stop_error)
            self.sessions=[s for s in self.sessions if s['id']!=args[1]]
            if self.selected==args[1]: self.selected=None
            if self.lost_stop: raise RuntimeError('transport.uncertain')
            return {'stopped_session_id':args[1]}
        if args==('start','--neutral'):
            self.generation+=1; self.selected=f'new-{self.generation}'
            row={'id':self.selected,'source':{'kind':'neutral'},'number':1,'name':'Neutral-1'}
            self.sessions.append(row)
            if self.inject_session: self.sessions.append({'id':'concurrent'}); self.selected='concurrent'
            return {'session':row}
        raise AssertionError(args)

    def initialize(self):
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':self.instance}): return self.m.initialize()
    def defer(self):
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':self.instance}): self.m.defer_current_locked()
    def marker(self): return json.loads(self.m.marker_path().read_text())
    def mutations(self): return [c for c in self.calls if c[0]=='core' and c[1]!='list']


class Startup(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory(prefix='session-startup-test-'); self.addCleanup(temp.cleanup)
        return Fixture(Path(temp.name))

    def test_new_login_resets_old_sessions_and_selects_one_neutral_empty_target(self):
        f=self.fixture(); original=list(f.clients)
        self.assertTrue(f.initialize())
        self.assertEqual(f.mutations(),[('core','stop','A'),('core','stop','B'),('core','start','--neutral')])
        self.assertEqual([s['name'] for s in f.sessions],['Neutral-1']); self.assertEqual(f.selected,'new-1')
        self.assertEqual(f.clients,original); self.assertNotEqual(f.active,1)
        state=json.loads(f.m.columns.STATE.read_text())
        self.assertEqual(state['owners'],{'1':'neutral',str(f.active):'new-1'})
        self.assertEqual(f.marker()['phase'],'ready'); self.assertTrue(list(f.root.glob('session-startup-backup-*/core-before.json')))

    def test_same_instance_reentry_does_not_reset_new_user_sessions(self):
        f=self.fixture(); f.initialize(); f.sessions.append({'id':'user-project'}); f.selected='user-project'
        f.calls.clear(); self.assertFalse(f.initialize()); self.assertEqual(f.calls,[])
        self.assertEqual(f.selected,'user-project')

    def test_logout_login_in_same_runtime_resets_again_without_inheriting_old_ids(self):
        f=self.fixture(); f.initialize(); f.instance='instance-two'; f.active=1; f.monitor['activeWorkspace']['id']=1
        self.assertTrue(f.initialize()); self.assertEqual(f.selected,'new-2'); self.assertEqual(len(f.sessions),1)
        self.assertEqual(f.marker()['instance'],'instance-two')

    def test_install_defer_never_touches_current_core_or_desktop(self):
        f=self.fixture(); before=f.m.columns.STATE.read_bytes(); f.defer()
        self.assertEqual(f.calls,[]); self.assertFalse(f.initialize()); self.assertEqual(f.calls,[])
        self.assertEqual(f.selected,'B'); self.assertEqual(f.m.columns.STATE.read_bytes(),before)
        f.instance='next-login'; self.assertTrue(f.initialize())

    def test_deferring_does_not_hide_a_failed_attempt(self):
        f=self.fixture(); f.stop_error='stop refused'
        with self.assertRaisesRegex(RuntimeError,'stop refused'): f.initialize()
        f.defer(); self.assertEqual(f.marker()['phase'],'failed')

    def test_multiple_compositors_fail_before_reset(self):
        f=self.fixture(); f.instances=[{'instance':f.instance},{'instance':'other'}]
        with self.assertRaisesRegex(RuntimeError,'exactly this one'): f.initialize()
        self.assertEqual(f.mutations(),[])

    def test_multiple_monitors_keep_existing_restriction(self):
        f=self.fixture(); f.monitors=[f.monitor,{'focused':False}]
        with self.assertRaisesRegex(RuntimeError,'one monitor'): f.initialize()
        self.assertEqual(f.mutations(),[])

    def test_existing_scoped_windows_fail_before_reset(self):
        f=self.fixture(); f.clients.append({'workspace':{'id':-9,'name':'special:sm-A-ai'}})
        with self.assertRaisesRegex(RuntimeError,'scoped scratchpad windows'): f.initialize()
        self.assertEqual(f.mutations(),[])

    def test_global_scratchpad_is_hidden_not_closed(self):
        f=self.fixture(); f.monitor['specialWorkspace']['name']='special:global'
        f.clients.append({'workspace':{'id':-8,'name':'special:global'}}); original=list(f.clients)
        f.initialize(); self.assertEqual(f.clients,original); self.assertIn(('hide',),f.calls)

    def test_initial_transport_unavailable_is_read_only_retryable(self):
        f=self.fixture(); f.read_errors=[RuntimeError('transport.unavailable'),subprocess.TimeoutExpired('fixture',2)]
        with patch.object(f.m.time,'sleep') as sleep: f.initialize()
        self.assertEqual(sleep.call_count,2); self.assertEqual(len(f.mutations()),3)

    def test_unavailable_core_times_out_without_reset(self):
        f=self.fixture(); f.read_errors=[RuntimeError('transport.unavailable')]
        with patch.object(f.m.time,'monotonic',side_effect=[0,20]):
            with self.assertRaisesRegex(RuntimeError,'unavailable at graphical startup'): f.initialize()
        self.assertEqual(f.mutations(),[]); self.assertEqual(f.marker()['phase'],'failed')

    def test_nontransport_core_failure_is_not_retried(self):
        f=self.fixture(); f.read_errors=[RuntimeError('recovery.upgrade_required')]
        with self.assertRaisesRegex(RuntimeError,'upgrade_required'): f.initialize()
        self.assertEqual(f.calls.count(('core','list')),1); self.assertEqual(f.mutations(),[])

    def test_uncertain_stop_is_not_replayed(self):
        f=self.fixture(); f.lost_stop=True
        with self.assertRaisesRegex(RuntimeError,'transport.uncertain'): f.initialize()
        before=list(f.calls)
        with self.assertRaises(f.m.AlreadyAttempted): f.initialize()
        self.assertEqual(f.calls,before); self.assertEqual(f.marker()['phase'],'failed')
        self.assertEqual(f.mutations(),[('core','stop','A')])

    def test_crashed_initializing_marker_is_not_replayed(self):
        f=self.fixture(); f.m.write_marker(f.instance,'initializing')
        with self.assertRaises(f.m.AlreadyAttempted): f.initialize()
        self.assertEqual(f.calls,[])

    def test_focus_failure_does_not_claim_ready_or_retry_creation(self):
        f=self.fixture(); f.focus_error=True
        with self.assertRaisesRegex(RuntimeError,'native focus failed'): f.initialize()
        self.assertEqual(f.marker()['phase'],'failed'); self.assertEqual(f.generation,1)
        with self.assertRaises(f.m.AlreadyAttempted): f.initialize()
        self.assertEqual(f.generation,1)

    def test_unconfirmed_focus_is_an_error(self):
        f=self.fixture(); f.silent_focus=True
        with self.assertRaisesRegex(RuntimeError,'not confirmed'): f.initialize()
        self.assertEqual(f.marker()['phase'],'failed')

    def test_concurrent_created_session_is_not_deleted_to_repair_state(self):
        f=self.fixture(); f.inject_session=True
        with self.assertRaisesRegex(RuntimeError,'not confirmed'): f.initialize()
        self.assertIn('concurrent',[s['id'] for s in f.sessions]); self.assertEqual(f.marker()['phase'],'failed')

    def test_corrupt_marker_blocks_reset(self):
        f=self.fixture(); f.m.marker_path().write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'invalid startup marker'): f.initialize()
        self.assertEqual(f.calls,[])

    def test_invalid_environment_blocks_all_calls(self):
        f=self.fixture()
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':''}):
            with self.assertRaisesRegex(RuntimeError,'signature'): f.m.initialize()
        self.assertEqual(f.calls,[])

    def test_shared_lock_serializes_concurrent_initializers(self):
        import fcntl
        f=self.fixture(); results=[]; errors=[]
        def worker():
            try: results.append(f.m.initialize())
            except Exception as error: errors.append(error)
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':f.instance}):
            with (f.root/'workspace-columns.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                threads=[threading.Thread(target=worker) for _ in range(2)]
                for thread in threads: thread.start()
                time.sleep(0.02); self.assertEqual(f.calls,[])
                fcntl.flock(lock,fcntl.LOCK_UN)
            for thread in threads: thread.join(timeout=3); self.assertFalse(thread.is_alive())
        self.assertEqual(errors,[]); self.assertEqual(sorted(results),[False,True]); self.assertEqual(f.generation,1)

    def test_first_failure_logs_and_exposes_bar_but_replay_never_launches_another(self):
        f=self.fixture(); f.read_errors=[RuntimeError('recovery.upgrade_required')]
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':f.instance}),patch.object(f.m.sys,'argv',['session-startup']),patch.object(f.m.sys,'stderr'),patch.object(f.m.subprocess,'run') as log,patch.object(f.m.os,'execvp',side_effect=LookupError('fake recovery bar')):
            with self.assertRaisesRegex(LookupError,'fake recovery bar'): f.m.main()
            log.assert_called_once(); self.assertEqual(log.call_args.args[0][0],'logger')
            self.assertEqual(f.marker()['phase'],'failed')
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':f.instance}),patch.object(f.m.sys,'argv',['session-startup']),patch.object(f.m.sys,'stderr'),patch.object(f.m.os,'execvp') as launch:
            self.assertEqual(f.m.main(),1); launch.assert_not_called()

    def test_main_only_launches_bar_after_initialization(self):
        f=self.fixture()
        def launch(binary,args):
            self.assertEqual((binary,args),('quickshell',['quickshell']))
            self.assertEqual(f.marker()['phase'],'ready')
            raise LookupError('fake bar exec')
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':f.instance}),patch.object(f.m.sys,'argv',['session-startup']),patch.object(f.m.os,'execvp',side_effect=launch):
            with self.assertRaisesRegex(LookupError,'fake bar exec'): f.m.main()
        with patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':f.instance}),patch.object(f.m.sys,'argv',['session-startup']),patch.object(f.m.os,'execvp') as launch:
            self.assertEqual(f.m.main(),0); launch.assert_not_called()


if __name__=='__main__': unittest.main()
