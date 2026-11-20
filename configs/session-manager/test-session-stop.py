#!/usr/bin/env python3
"""Graphical stop policy using fake core/desktop and private workspace state only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name('session-desktop.py')
os.environ['SESSION_COLUMNS_SCRIPT'] = str(SOURCE.parents[1]/'hypr/files/Scripts/workspace-columns.py')


class Fixture:
    def __init__(self, root, sessions=('A','B','C'), active='B'):
        spec=importlib.util.spec_from_file_location('stop_client',SOURCE)
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.sessions=list(sessions); self.selected=active; self.revision=0
        self.ws=ord(active)-ord('A')+2 if active else 1
        self.clients=[{'address':'legacy','workspace':{'id':1,'name':'1'}}]
        self.monitor={'focused':True,'activeWorkspace':{'id':self.ws},'specialWorkspace':{'name':''}}
        self.events=[]; self.fail_switch=False; self.fail_focus=False; self.silent_focus=False
        self.invalid_switch=False; self.fail_stop=False; self.lost_reply=False
        self.on_focus=None; self.on_stop=None; self.after_focus=None
        state={'version':3,'order':[1,*range(2,2+len(self.sessions))],
               'owners':{'1':'neutral',**{str(i):sid for i,sid in enumerate(self.sessions,2)}},
               'preferred':{},'next_id':len(self.sessions)+2}
        m=self.module; m.columns.RUNTIME=root; m.columns.STATE=root/'state.json'; m.columns.save(state)
        m.columns.query=self.query; m.columns.active=lambda:self.ws
        m.columns.focus=self.focus; m.columns.focus_empty=self.focus
        m.columns.dispatch=self.dispatch; m.columns.ctl=lambda *args:(_ for _ in ()).throw(AssertionError('no real compositor'))
        m.request=self.request

    def query(self, key):
        if key=='monitors': return [self.monitor]
        if key=='clients': return self.clients
        if key=='workspaces': return [{'id':ws} for ws in {self.ws,1,*(c['workspace']['id'] for c in self.clients if c['workspace']['id']>0)}]
        raise AssertionError(key)

    def focus(self, ws):
        self.events.append(('focus',ws))
        if self.fail_focus: raise RuntimeError('focus failed')
        if not self.silent_focus:
            self.ws=ws; self.monitor['activeWorkspace']['id']=ws
        if self.on_focus: self.on_focus(self)

    def dispatch(self, expression):
        assert expression.startswith('hl.dsp.workspace.toggle_special('),expression
        self.events.append(('hide',expression)); self.monitor['specialWorkspace']['name']=''

    def request(self,*args):
        self.events.append(('request',args))
        if args==('list',):
            if self.after_focus and any(event[0]=='focus' for event in self.events): self.after_focus(self)
            return {'sessions':[{'id':sid} for sid in self.sessions], 'active_session_id':self.selected, 'revision':self.revision}
        if args[0]=='switch':
            if self.fail_switch: raise RuntimeError('not_found.session')
            self.selected=args[1]; self.revision+=1
            return {'session':{'id':'wrong' if self.invalid_switch else self.selected}}
        if args[0]=='stop':
            if self.fail_stop: raise RuntimeError('stop rejected')
            self.sessions.remove(args[1]); self.revision+=1
            if self.selected==args[1]: self.selected=None
            if self.on_stop: self.on_stop(self)
            if self.lost_reply: raise RuntimeError('transport.uncertain')
            return {'stopped_session_id':args[1]}
        raise AssertionError(args)

    def stop(self,sid): return self.module.invoke('stop',sid)
    def was_stopped(self): return [event for event in self.events if event[0]=='request' and event[1][0]=='stop']
    def state(self): return json.loads(self.module.columns.STATE.read_text())


class StopPolicy(unittest.TestCase):
    def fixture(self,**kwargs):
        temp=tempfile.TemporaryDirectory(prefix='stop-policy-'); self.addCleanup(temp.cleanup)
        return Fixture(Path(temp.name),**kwargs)

    def test_active_stop_selects_next_then_focuses_before_deletion(self):
        f=self.fixture(); f.clients.append({'workspace':{'id':4,'name':'4'}})
        f.stop('B')
        self.assertEqual(f.sessions,['A','C']); self.assertEqual(f.selected,'C'); self.assertEqual(f.ws,4)
        switch=f.events.index(('request',('switch','C'))); focus=f.events.index(('focus',4)); stop=f.events.index(('request',('stop','B')))
        self.assertLess(switch,focus); self.assertLess(focus,stop)
        self.assertEqual(f.clients[0]['workspace']['id'],1)
        self.assertTrue(f.module.status()['context_confirmed'])

    def test_last_in_opening_order_wraps_to_first(self):
        f=self.fixture(active='C'); f.stop('C')
        self.assertEqual(f.selected,'A'); self.assertEqual(f.ws,2); self.assertEqual(f.sessions,['A','B'])

    def test_fallback_without_desktop_mapping_gets_a_fresh_owned_workspace(self):
        f=self.fixture(); state=f.state(); state['order'].remove(4); state['owners'].pop('4'); f.module.columns.save(state)
        f.stop('B'); self.assertEqual(f.selected,'C')
        self.assertEqual(f.state()['owners'][str(f.ws)],'C'); self.assertGreater(f.ws,4)

    def test_last_session_rejected_before_hiding_or_metadata_change(self):
        f=self.fixture(sessions=('A',),active='A'); f.monitor['specialWorkspace']['name']='special:global'
        before=f.module.columns.STATE.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'last open session'): f.stop('A')
        self.assertEqual(f.selected,'A'); self.assertEqual(f.sessions,['A']); self.assertEqual(f.revision,0)
        self.assertEqual(f.events,[('request',('list',))])
        self.assertEqual(f.module.columns.STATE.read_bytes(),before)

    def test_last_unselected_session_also_cannot_be_stopped(self):
        f=self.fixture(sessions=('A',),active=None)
        with self.assertRaisesRegex(RuntimeError,'last open session'): f.stop('A')
        self.assertEqual(f.selected,None); self.assertEqual(f.revision,0)

    def test_unknown_target_is_not_last_session_error(self):
        f=self.fixture(sessions=('A',),active='A')
        with self.assertRaisesRegex(RuntimeError,'not_found.session'): f.stop('missing')
        self.assertEqual(f.revision,0)

    def test_inactive_stop_does_not_switch_the_active_session(self):
        f=self.fixture(); f.stop('A')
        self.assertEqual(f.selected,'B'); self.assertEqual(f.ws,3)
        self.assertFalse(any(event[0]=='focus' or event[0]=='request' and event[1][0]=='switch' for event in f.events))

    def test_normal_windows_still_block_before_switching(self):
        f=self.fixture(); f.clients.append({'workspace':{'id':3,'name':'3'}})
        with self.assertRaisesRegex(RuntimeError,'open windows'): f.stop('B')
        self.assertEqual(f.selected,'B'); self.assertEqual(f.was_stopped(),[])

    def test_scratchpad_windows_still_block_before_switching(self):
        f=self.fixture(); f.clients.append({'workspace':{'id':-9,'name':'special:sm-B-ai'}})
        with self.assertRaisesRegex(RuntimeError,'open windows'): f.stop('B')
        self.assertEqual(f.selected,'B'); self.assertEqual(f.was_stopped(),[])

    def test_failed_fallback_switch_never_stops_original(self):
        f=self.fixture(); f.fail_switch=True
        with self.assertRaisesRegex(RuntimeError,'not_found.session'): f.stop('B')
        self.assertEqual(f.selected,'B'); self.assertIn('B',f.sessions); self.assertEqual(f.was_stopped(),[])

    def test_invalid_switch_reply_never_stops_original(self):
        f=self.fixture(); f.invalid_switch=True
        with self.assertRaisesRegex(RuntimeError,'invalid switch acknowledgement'): f.stop('B')
        self.assertIn('B',f.sessions); self.assertEqual(f.was_stopped(),[])

    def test_failed_focus_preserves_original_and_rejects_unsafe_retry(self):
        f=self.fixture(); f.fail_focus=True
        with self.assertRaisesRegex(RuntimeError,'focus failed'): f.stop('B')
        self.assertEqual(f.selected,'C'); self.assertEqual(f.ws,3); self.assertIn('B',f.sessions)
        self.assertEqual(f.was_stopped(),[])
        with self.assertRaisesRegex(RuntimeError,'displayed and logical sessions differ'): f.stop('B')
        self.assertEqual(f.was_stopped(),[])

    def test_silent_focus_failure_is_not_accepted(self):
        f=self.fixture(); f.silent_focus=True
        with self.assertRaisesRegex(RuntimeError,'fallback desktop not confirmed'): f.stop('B')
        self.assertIn('B',f.sessions); self.assertEqual(f.was_stopped(),[])

    def test_window_arriving_during_fallback_keeps_source_ownership(self):
        f=self.fixture(); f.on_focus=lambda fixture:fixture.clients.append({'workspace':{'id':3,'name':'3'}})
        with self.assertRaisesRegex(RuntimeError,'open windows'): f.stop('B')
        self.assertEqual(f.selected,'C'); self.assertIn('B',f.sessions); self.assertEqual(f.state()['owners']['3'],'B')
        self.assertEqual(f.was_stopped(),[])

    def test_core_selection_race_before_stop_is_reported_without_deletion(self):
        f=self.fixture(); f.after_focus=lambda fixture:setattr(fixture,'selected',None)
        with self.assertRaisesRegex(RuntimeError,'sessions changed during fallback'): f.stop('B')
        self.assertIn('B',f.sessions); self.assertEqual(f.was_stopped(),[])

    def test_stop_failure_keeps_original_and_valid_fallback(self):
        f=self.fixture(); f.fail_stop=True
        with self.assertRaisesRegex(RuntimeError,'stop rejected'): f.stop('B')
        self.assertIn('B',f.sessions); self.assertEqual(f.selected,'C'); self.assertEqual(f.state()['owners']['3'],'B')

    def test_lost_stop_reply_is_not_replayed_or_claimed_rolled_back(self):
        f=self.fixture(); f.lost_reply=True
        with self.assertRaisesRegex(RuntimeError,'transport.uncertain'): f.stop('B')
        self.assertNotIn('B',f.sessions); self.assertEqual(f.selected,'C')
        self.assertEqual(len(f.was_stopped()),1); self.assertEqual(f.state()['owners']['3'],'B')

    def test_external_selection_change_after_stop_is_reported(self):
        f=self.fixture(); f.on_stop=lambda fixture:setattr(fixture,'selected',None)
        with self.assertRaisesRegex(RuntimeError,'stop outcome/selection changed'): f.stop('B')
        self.assertNotIn('B',f.sessions); self.assertEqual(len(f.was_stopped()),1)


if __name__=='__main__': unittest.main()
