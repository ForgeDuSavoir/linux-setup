#!/usr/bin/env python3
"""Single-list controller acceptance; all windows, workspaces and dispatchers are fake."""
import importlib.util
import json
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'files/Scripts/workspace-columns.py'
spec = importlib.util.spec_from_file_location('workspace_list', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FOCUS_EMPTY = module.focus_empty
MOVE_EMPTY = module.move_empty


def client(address, ws):
    return {'address': address, 'workspace': {'id': ws, 'name': str(ws)}}


class Desktop:
    def __init__(self, clients, active):
        self.clients = clients
        self.active = active
        self.focused = clients[-1]['address'] if clients else None
        self.other_visible = set()
        self.ws = {active, *(c['workspace']['id'] for c in clients if c['workspace']['id'] > 0)}
        self.events = []

    def prune(self):
        self.ws = {self.active, *self.other_visible,
                   *(c['workspace']['id'] for c in self.clients if c['workspace']['id'] > 0)}

    def query(self, name):
        if name == 'clients': return self.clients
        if name == 'activeworkspace': return {'id': self.active}
        if name == 'activewindow': return next((c for c in self.clients if c['address'] == self.focused), {})
        if name == 'workspaces':
            return [{'id': ws, 'windows': sum(c['workspace']['id'] == ws for c in self.clients)} for ws in sorted(self.ws)]
        if name == 'monitors':
            return [{'focused': True, 'activeWorkspace': {'id': self.active}, 'specialWorkspace': {'name': ''}}] + [
                {'focused': False, 'activeWorkspace': {'id': ws}, 'specialWorkspace': {'name': ''}} for ws in self.other_visible]
        raise AssertionError(name)

    def focus(self, ws):
        self.events.append(('focus', ws))
        self.active = ws
        self.focused = next((c['address'] for c in self.clients if c['workspace']['id'] == ws), None)
        self.prune()

    def move(self, ws, address=None, follow=True):
        self.events.append(('move', ws, address))
        window = next(c for c in self.clients if c['address'] == (address or self.focused))
        window['workspace'] = {'id': ws, 'name': str(ws)}
        if follow: self.focus(ws)
        else: self.prune()


class Workspaces(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workspace-list-')
        self.addCleanup(self.temp.cleanup)
        module.RUNTIME = Path(self.temp.name)
        module.STATE = module.RUNTIME / 'state.json'
        self.desktop = Desktop([client('a', 1), client('b', 2), client('c', 8)], 1)
        self.patches = [patch.object(module, 'focus_empty', side_effect=lambda ws: self.desktop.focus(ws)),
                        patch.object(module, 'move_empty', side_effect=lambda ws, address: self.desktop.move(ws, address)),
                        patch.object(module, 'ctl', side_effect=AssertionError('no real native tool')),
                        patch.object(module, 'query', side_effect=lambda name: self.desktop.query(name)),
                        patch.object(module, 'focus', side_effect=lambda ws: self.desktop.focus(ws)),
                        patch.object(module, 'move', side_effect=lambda *a, **kw: self.desktop.move(*a, **kw)),
                        patch.object(module, 'dispatch', side_effect=AssertionError('no real compositor'))]
        for item in self.patches: item.start(); self.addCleanup(item.stop)
        self.state = module.project_state(None, self.desktop.ws)
        self.state['owners'] = {'1':'A', '2':'A', '8':'B'}

    def test_metadata_upgrade_preserves_actual_ids_rows_windows_and_scope(self):
        old = {'version':2, 'owners':{'1':'A','2':'B','3':'C'}, 'last':{'1':2,'3':2},
               'preferred':{'A':1,'B':2,'C':3}, 'origins':{'a':1}}
        clients = json.loads(json.dumps(self.desktop.clients))
        state = module.project_state(old, {1,2,3})
        self.assertEqual(state['order'], [1,2,3,6])
        self.assertEqual(state['owners'], {'1':'A','2':'A','3':'B','6':'C'})
        self.assertEqual(state['preferred'], {'A':2,'B':3,'C':6})
        self.assertNotIn('origins', state)
        self.assertEqual(self.desktop.clients, clients)
        self.assertEqual(self.desktop.events, [])

    def test_missing_metadata_never_moves_legacy_special_windows(self):
        self.desktop.clients.append(client('d', -90))
        self.desktop.clients[-1]['workspace']['name'] = 'special:workspace-2'
        state = module.load()
        self.assertEqual(state['order'], [1,2,8])
        self.assertEqual(set(state['owners'].values()), {'neutral'})
        self.assertEqual(self.desktop.events, [])

    def test_insert_is_immediately_after_current_without_renumbering_any_window(self):
        before = json.loads(json.dumps(self.desktop.clients))
        module.create_empty(self.state)
        self.assertEqual(self.state['order'], [1,9,2,8])
        self.assertEqual(self.desktop.active, 9)
        self.assertEqual(self.state['owners']['9'], 'A')
        self.assertEqual(self.desktop.clients, before)
        self.assertEqual(module.snapshot()['workspaces'], [{'id':1,'name':'1'},{'id':9,'name':'2'},{'id':2,'name':'3'}])

    def test_repeated_insert_toggles_back_then_allocates_a_fresh_id(self):
        module.create_empty(self.state)
        module.create_empty(self.state)
        self.assertEqual(self.desktop.active, 1)
        self.assertEqual(self.state["order"], [1,2,8])
        self.assertEqual(self.state["next_id"], 10)
        module.create_empty(self.state)
        self.assertEqual(self.state['order'], [1,10,2,8])
        self.assertNotIn('9', self.state['owners'])
        self.assertEqual(self.desktop.active, 10)
        self.assertEqual(self.state['next_id'], 11)

    def test_tab_empty_uses_preceding_same_owner_without_moving_windows(self):
        module.create_empty(self.state)
        self.state['order'] = [2,1,8,9]
        before = json.loads(json.dumps(self.desktop.clients))
        module.create_empty(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[2,1,8])
        self.assertEqual(self.state['next_id'],10)
        self.assertEqual(self.desktop.clients,before)

    def test_tab_empty_without_predecessor_does_not_wrap_or_allocate(self):
        self.desktop.clients = [c for c in self.desktop.clients if c['address'] != 'a']
        module.create_empty(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,2,8])
        self.assertEqual(self.state['next_id'],9)
        self.assertEqual(self.desktop.events,[])

    def test_tab_only_empty_workspace_never_enters_another_session(self):
        self.desktop.clients = [c for c in self.desktop.clients if c['address'] != 'a']
        self.state['order']=[2,8,1]
        self.state['owners']['2']='B'
        module.create_empty(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.desktop.events,[])
        self.assertEqual(self.state['next_id'],9)

    def test_tab_empty_can_return_to_existing_visible_empty_predecessor(self):
        module.create_empty(self.state)
        self.desktop.other_visible={1}
        self.desktop.clients=[c for c in self.desktop.clients if c['address']!='a']
        module.create_empty(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertNotIn(9,self.state['order'])
        self.assertEqual(self.state['next_id'],10)

    def test_cycle_uses_list_order_only_within_owner_and_discards_empty(self):
        module.create_empty(self.state)
        module.cycle(self.state)
        self.assertEqual(self.desktop.active, 2)
        self.assertEqual(self.state['order'], [1,2,8])
        module.cycle(self.state)
        self.assertEqual(self.desktop.active, 1)
        self.assertNotIn(('focus',8), self.desktop.events)

    def test_external_focus_cleanup_discards_last_empty_anchor_without_stopping_session(self):
        module.create_empty(self.state)
        self.state['owners']['9'] = 'only-empty-session'
        self.state['preferred'] = {'only-empty-session':9}
        self.desktop.focus(8)
        module.cleanup(self.state)
        self.assertNotIn(9,self.state['order'])
        self.assertNotIn('only-empty-session',self.state['preferred'])
        self.assertEqual(self.desktop.active,8)

    def test_cleanup_preserves_other_monitors_visible_empty_workspace(self):
        self.desktop.other_visible = {9}
        self.desktop.ws.add(9)
        self.state['order'].append(9); self.state['owners']['9'] = 'B'
        module.cleanup(self.state)
        self.assertIn(9,self.state['order'])
        self.assertEqual(self.desktop.events,[])

    def test_close_last_window_selects_previous_occupied_same_owner(self):
        self.desktop.focus(2)
        self.desktop.clients = [c for c in self.desktop.clients if c['address']!='b']
        module.closed(self.state,2)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,8])
        self.assertEqual(self.desktop.clients[-1]['workspace']['id'],8)

    def test_close_last_context_window_keeps_one_visible_empty_instead_of_crossing_owner(self):
        self.desktop.clients = [c for c in self.desktop.clients if c['workspace']['id']==8]
        module.closed(self.state,1)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,8])
        self.assertEqual(self.desktop.events,[])

    def test_inactive_empty_close_does_not_focus_or_renumber(self):
        self.desktop.clients = [c for c in self.desktop.clients if c['address']!='b']
        self.desktop.prune()
        module.closed(self.state,2)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,8])
        self.assertEqual(self.desktop.events,[])

    def test_close_with_other_windows_is_noop(self):
        with patch.object(module.time,'sleep'):
            module.closed(self.state,1)
        self.assertEqual(self.desktop.events,[])

    def test_isolate_then_previous_undoes_without_history(self):
        self.desktop.clients.append(client('d',1)); self.desktop.focused='d'
        module.isolate_or_previous(self.state)
        self.assertEqual(self.state['order'],[1,9,2,8])
        self.assertEqual(self.desktop.active,9)
        self.assertNotIn('origins',self.state)
        module.isolate_or_previous(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,2,8])
        self.assertEqual(self.desktop.clients[-1]['workspace']['id'],1)
        self.assertEqual(self.desktop.clients[2]['workspace']['id'],8)

    def test_previous_at_first_workspace_does_not_wrap_or_create(self):
        self.desktop.focused='a'
        module.isolate_or_previous(self.state)
        self.assertEqual(self.desktop.events,[])
        self.assertEqual(self.state['order'],[1,2,8])
        self.assertEqual(self.state['next_id'],9)

    def test_previous_uses_order_not_numeric_id_or_foreign_owner(self):
        self.state['order']=[2,8,1]
        self.desktop.focused='a'
        module.isolate_or_previous(self.state)
        self.assertEqual(self.desktop.active,2)
        self.assertEqual(self.state['order'],[2,8])
        self.assertEqual(self.desktop.clients[2]['workspace']['id'],8)

    def test_previous_with_no_occupied_target_does_nothing(self):
        self.desktop.clients=[client('b',2),client('c',8)]
        self.desktop.active=2; self.desktop.focused='b'
        self.desktop.other_visible={1}
        module.isolate_or_previous(self.state)
        self.assertEqual(self.desktop.events,[])

    def test_previous_skips_visible_empty_workspace_to_join_other_windows(self):
        self.desktop.other_visible={9}; self.desktop.ws.add(9)
        self.state['order']=[1,9,2,8]; self.state['owners']['9']='A'
        self.desktop.focus(2); self.desktop.events=[]
        module.isolate_or_previous(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertIn(9,self.state['order'])
        self.assertNotIn(2,self.state['order'])

    def test_next_moves_into_existing_workspace_even_with_multiple_source_windows(self):
        self.desktop.clients.append(client('d',1)); self.desktop.focused='d'
        module.move_next(self.state)
        self.assertEqual(self.desktop.active,2)
        self.assertEqual(self.desktop.clients[-1]['workspace']['id'],2)
        self.assertEqual(self.state['order'],[1,2,8])
        self.assertEqual(self.state['next_id'],9)
        self.assertEqual(self.desktop.clients[0]['workspace']['id'],1)

    def test_next_wraps_and_removes_empty_source(self):
        self.desktop.focus(2); self.desktop.events=[]
        module.move_next(self.state)
        self.assertEqual(self.desktop.active,1)
        self.assertEqual(self.state['order'],[1,8])
        self.assertEqual(self.desktop.clients[1]['workspace']['id'],1)
        self.assertEqual(self.desktop.clients[2]['workspace']['id'],8)

    def test_next_uses_explicit_order_and_never_isolates(self):
        self.state['order']=[2,8,1]
        self.desktop.focused='a'
        module.move_next(self.state)
        self.assertEqual(self.desktop.active,2)
        self.assertEqual(self.state['order'],[2,8])
        self.assertEqual(self.state['next_id'],9)

    def test_next_can_use_existing_visible_empty_workspace(self):
        self.desktop.other_visible={9}; self.desktop.ws.add(9)
        self.state['order']=[1,9,2,8]; self.state['owners']['9']='A'
        self.desktop.focused='a'
        module.move_next(self.state)
        self.assertEqual(self.desktop.active,9)
        self.assertNotIn(1,self.state['order'])
        self.assertEqual(self.state['next_id'],9)

    def test_move_operations_ignore_special_or_missing_active_windows(self):
        for operation in [module.move_next,module.isolate_or_previous]:
            self.desktop.focused=None
            operation(self.state)
            self.desktop.clients.append(client('d',-9)); self.desktop.focused='d'
            operation(self.state)
            self.desktop.clients.pop()
        self.assertEqual(self.desktop.events,[])

    def test_old_origins_are_retired_without_changing_schema_or_live_state(self):
        raw={**self.state,'origins':{'stale-address':999999}}
        projected=module.project_state(raw,self.desktop.ws)
        self.assertNotIn('origins',projected)
        self.assertIn('origins',raw)
        self.assertEqual(projected['order'],self.state['order'])
        self.assertEqual(projected['version'],3)
        self.assertEqual(self.desktop.events,[])

    def test_lone_window_with_no_same_owner_target_is_not_moved(self):
        self.state['owners']['2']='B'
        self.desktop.focused='a'
        module.move_next(self.state)
        self.assertEqual(self.desktop.events,[])

    def test_snapshot_does_not_write_or_migrate_and_keeps_current_empty(self):
        old={'version':2,'owners':{'1':'A','4':'B'},'last':{},'preferred':{},'origins':{}}
        module.STATE.write_text(json.dumps(old)); original=module.STATE.read_bytes()
        result=module.snapshot()
        self.assertEqual([r['id'] for r in result['workspaces']],[1,2])
        self.assertEqual(module.STATE.read_bytes(),original)
        self.assertEqual(self.desktop.events,[])

    def test_external_workspaces_are_never_adopted_by_active_session(self):
        module.save(self.state)
        self.desktop.clients.append(client('d',6)); self.desktop.ws.add(6)
        state=module.load()
        self.assertEqual(state['owners']['6'],'neutral')

    def test_invalid_metadata_and_id_exhaustion_fail_without_dispatch(self):
        for bad in [{'version':7},{**self.state,'order':[1,1,8]}, {**self.state,'next_id':True}]:
            with self.assertRaises(RuntimeError): module.project_state(bad,self.desktop.ws)
        self.state['next_id']=module.MAX_ID+1
        with self.assertRaises(RuntimeError): module.fresh_workspace(self.state,'A',after=1)
        self.assertEqual(self.desktop.events,[])

    def test_native_guard_rejects_target_race_without_adopting_or_reusing_it(self):
        before = json.loads(json.dumps(self.desktop.clients))
        with patch.object(module, 'focus_empty', side_effect=RuntimeError('workspace target already exists')):
            with self.assertRaises(RuntimeError): module.create_empty(self.state)
        self.assertEqual(self.state['order'], [1,2,8])
        self.assertNotIn('9', self.state['owners'])
        self.assertEqual(self.state['next_id'], 10)
        self.assertEqual(self.desktop.clients, before)
        self.assertEqual(self.desktop.events, [])

    def test_uncertain_focus_does_not_claim_an_unconfirmed_workspace(self):
        def uncertain(ws):
            self.desktop.focus(ws)
            raise RuntimeError('lost acknowledgement')
        with patch.object(module, 'focus_empty', side_effect=uncertain):
            with self.assertRaises(RuntimeError): module.create_empty(self.state)
        self.assertEqual(self.desktop.active, 9)
        self.assertNotIn('9', self.state['owners'])
        self.assertEqual(module.read_state()['owners']['9'], 'neutral')

    def test_isolation_target_race_keeps_original_windows_and_owner(self):
        self.desktop.clients.append(client('d',1)); self.desktop.focused='d'
        with patch.object(module, 'move_empty', side_effect=RuntimeError('workspace target already exists')):
            with self.assertRaises(RuntimeError): module.isolate_or_previous(self.state)
        self.assertEqual(self.state['order'], [1,2,8])
        self.assertNotIn('origins', self.state)
        self.assertEqual(self.desktop.clients[-1]['workspace']['id'], 1)

    def test_native_empty_guard_and_dispatch_are_one_eval_without_animation_changes(self):
        calls = []
        with patch.object(module, 'ctl', side_effect=lambda *args: calls.append(args)):
            FOCUS_EMPTY(9)
            MOVE_EMPTY(9, '0xab')
        for command, code in calls:
            self.assertEqual(command, 'eval')
            self.assertLess(code.index('hl.get_workspace(9)'), code.index('hl.dispatch('))
            self.assertNotIn('hl.animation', code)

    def test_lua_guards_are_atomic_and_syntax_valid_without_a_real_compositor(self):
        if not shutil.which('lua'):
            self.skipTest('Lua interpreter unavailable')
        calls = []
        with patch.object(module, 'ctl', side_effect=lambda *args: calls.append(args) or 'ok'):
            FOCUS_EMPTY(9)
            MOVE_EMPTY(9, 'a')
        for kind, code in calls:
            self.assertEqual(kind, 'eval')
            self.assertLess(code.index('hl.get_workspace'), code.index('hl.dispatch'))
            wrapper = """
local code = io.read("*a")
local chunk = assert(load(code))
hl = {get_workspace = function() return {} end}
local ok, err = pcall(chunk)
assert(not ok and tostring(err):find("workspace target already exists", 1, true))
local called = 0
local function spec(value) return value end
hl = {
 get_workspace = function() return nil end,
 dsp = {focus = spec, window = {move = spec}},
 dispatch = function(value) assert(value.workspace == 9); called = called + 1 end
}
assert(pcall(chunk))
assert(called == 1)
"""
            subprocess.run(['lua', '-e', wrapper], input=code, text=True, check=True)

    def test_removed_commands_are_rejected_without_loading_state(self):
        for command in ['toggle-row','move-row','focus-column']:
            with patch.object(sys,'argv',[str(SOURCE),command]), patch.object(module,'load',side_effect=AssertionError('no load')):
                with self.assertRaises(SystemExit): module.main()
        source=SOURCE.read_text()
        self.assertNotIn('hl.animation',source)
        self.assertNotIn('slidevert',source)


if __name__=='__main__': unittest.main()
