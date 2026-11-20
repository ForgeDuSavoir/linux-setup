#!/usr/bin/env python3
"""SUPER+Q policy: fake core/desktop, actual generated Lua with a fake hl API."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stop_fixture',HERE/'test-session-stop.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)


class ClosePolicy(unittest.TestCase):
    def fixture(self,**kwargs):
        temporary=tempfile.TemporaryDirectory(prefix='close-policy-');self.addCleanup(temporary.cleanup)
        f=fixtures.Fixture(Path(temporary.name),**kwargs)
        f.window={};f.native_ws=None;f.native_address=None;f.native_visible=True
        query=f.query
        f.module.columns.query=lambda key:f.window if key=='activewindow' else query(key)
        f.module.columns.ctl=lambda *args:self.lua(f,*args)
        return f

    def lua(self,f,command,expression):
        self.assertEqual(command,'eval')
        f.events.append(('eval',expression))
        ws=f.window['workspace'];address=f.native_address or f.window['address']
        special=f.monitor['specialWorkspace']['name']
        window = ('{address=%s,mapped=true,visible=%s,workspace={id=%s,name=%s}}'
                  % (json.dumps(address),str(f.native_visible).lower(),ws['id'],json.dumps(ws['name'])))
        script=f'''
local closes=0
local ws={{id={f.native_ws or f.ws}}}
local sp={('{name='+json.dumps(special)+'}') if special else 'nil'}
local w={window}
hl={{get_active_workspace=function() return ws end,
get_active_special_workspace=function() return sp end,
get_active_window=function() return w end,
dsp={{window={{close=function(opts)
 assert(opts.window=="address:"..w.address)
 return function() closes=closes+1 end
end}}}},dispatch=function(d) d() end}}
{expression}
assert(closes==1)
'''
        subprocess.run(['lua','-'],input=script,text=True,capture_output=True,check=True,timeout=2)
        return 'ok'

    def test_empty_session_uses_menu_fallback_before_stop(self):
        f=self.fixture();f.module.invoke('close',3)
        self.assertEqual(f.sessions,['A','C']);self.assertEqual(f.selected,'C')
        self.assertLess(f.events.index(('focus',4)),f.events.index(('request',('stop','B'))))
        self.assertFalse(any(e[0]=='eval' for e in f.events))

    def test_stale_foreign_focus_is_not_closed(self):
        f=self.fixture();f.window={'address':'0xaa','workspace':{'id':2,'name':'2'}}
        f.module.invoke('close',3)
        self.assertNotIn('B',f.sessions);self.assertFalse(any(e[0]=='eval' for e in f.events))
        self.assertEqual(f.clients,[{'address':'legacy','workspace':{'id':1,'name':'1'}}])

    def test_other_workspace_windows_block_session_close(self):
        f=self.fixture();state=f.state();state['order'].append(8);state['owners']['8']='B';f.module.columns.save(state)
        f.clients.append({'workspace':{'id':8,'name':'8'}})
        with self.assertRaisesRegex(RuntimeError,'open windows'):f.module.invoke('close',3)
        self.assertEqual(f.was_stopped(),[]);self.assertEqual(f.selected,'B')

    def test_hidden_scoped_scratchpad_blocks_session_close(self):
        f=self.fixture();f.clients.append({'workspace':{'id':-5,'name':'special:sm-B-notes'}})
        with self.assertRaisesRegex(RuntimeError,'open windows'):f.module.invoke('close',3)
        self.assertEqual(f.was_stopped(),[])

    def test_last_session_is_not_stopped(self):
        f=self.fixture(sessions=('A',),active='A')
        with self.assertRaisesRegex(RuntimeError,'last open session'):f.module.invoke('close',2)
        self.assertEqual(f.sessions,['A']);self.assertEqual(f.revision,0)

    def test_no_active_unowned_desktop_is_noop(self):
        f=self.fixture(active=None);self.assertEqual(f.module.invoke('close',1),{'noop':True})
        self.assertEqual(f.was_stopped(),[])

    def test_native_logical_mismatch_is_refused(self):
        f=self.fixture();f.ws=2
        with self.assertRaisesRegex(RuntimeError,'differ'):f.module.invoke('close',2)
        self.assertEqual(f.was_stopped(),[])

    def test_queued_second_q_cannot_stop_survivor(self):
        f=self.fixture();f.module.invoke('close',3)
        with self.assertRaisesRegex(RuntimeError,'differ'):f.module.invoke('close',3)
        self.assertEqual(f.sessions,['A','C']);self.assertEqual(len(f.was_stopped()),1)

    def test_visible_window_is_closed_by_explicit_address_without_session_stop(self):
        f=self.fixture();f.window={'address':'0xaa','workspace':{'id':3,'name':'3'}}
        self.assertEqual(f.module.invoke('close',3),{'closed_window_requested':True})
        self.assertEqual(f.was_stopped(),[]);self.assertEqual(f.selected,'B')

    def test_native_focus_workspace_or_visibility_race_refuses_window_close(self):
        for attribute,value in [('native_address','0xbb'),('native_ws',4),('native_visible',False)]:
            with self.subTest(attribute=attribute):
                f=self.fixture();f.window={'address':'0xaa','workspace':{'id':3,'name':'3'}}
                setattr(f,attribute,value)
                with self.assertRaises(subprocess.CalledProcessError):f.module.invoke('close',3)
                self.assertEqual(f.was_stopped(),[])

    def test_visible_scoped_or_global_scratchpad_window_is_closed_not_hidden(self):
        for special in ['special:sm-B-notes','special:global']:
            f=self.fixture();f.monitor['specialWorkspace']['name']=special
            f.window={'address':'0xaa','workspace':{'id':-5,'name':special}}
            f.module.invoke('close',3)
            self.assertEqual(f.was_stopped(),[]);self.assertFalse(any(e[0]=='hide' for e in f.events))

    def test_foreign_or_unconfirmed_scratchpad_never_triggers_session_stop(self):
        for special in ['special:sm-A-notes','special:global']:
            f=self.fixture();f.monitor['specialWorkspace']['name']=special
            with self.assertRaisesRegex(RuntimeError,'scratchpad'):f.module.invoke('close',3)
            self.assertEqual(f.was_stopped(),[])

    def test_context_change_before_empty_stop_is_refused(self):
        f=self.fixture();original=f.module.request;calls=0
        def request(*args):
            nonlocal calls
            result=original(*args)
            if args==('list',):
                calls+=1
                if calls==2:result['revision']+=1
            return result
        f.module.request=request
        with self.assertRaisesRegex(RuntimeError,'context changed'):f.module.invoke('close',3)
        self.assertEqual(f.was_stopped(),[])

    def test_real_lua_binding_freezes_keypress_workspace(self):
        keybinds=HERE.parent/'hypr/files/keybinds.lua'
        script=f'''
local binds,commands={{}},{{}}
local ws={{id=3}}
local function proxy()
 return setmetatable({{}},{{__index=function(t,k) local p=proxy();rawset(t,k,p);return p end,
 __call=function() return function() end end}})
end
hl=proxy()
hl.bind=function(key,callback) binds[key]=callback end
hl.get_active_workspace=function() return ws end
hl.dsp.exec_cmd=function(command) return command end
hl.dispatch=function(command) table.insert(commands,command) end
assert(loadfile({json.dumps(str(keybinds))}))()
binds['SUPER + Q']()
ws.id=4
assert(#commands==1 and commands[1]:match("close 3'$")~=nil)
'''
        subprocess.run(['lua','-'],input=script,text=True,capture_output=True,check=True,timeout=2)

    def test_failed_survivor_focus_keeps_original_session(self):
        f=self.fixture();f.fail_focus=True
        with self.assertRaisesRegex(RuntimeError,'focus failed'):f.module.invoke('close',3)
        self.assertIn('B',f.sessions);self.assertEqual(f.was_stopped(),[])


if __name__=='__main__':unittest.main()
