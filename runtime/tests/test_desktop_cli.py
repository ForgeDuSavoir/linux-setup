#!/usr/bin/env python3
"""R2 CLI transport, metadata read-only behavior and legacy lock interoperation."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from test_desktop_parity import Environment,BIN,cases,ROOT

class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='r2-cli-');self.addCleanup(self.tmp.cleanup)
        self.e=Environment(self.tmp.name,cases()['status_confirmed'])
    def call(self,*args,env=None):return subprocess.run([str(BIN),*args],env=env or self.e.env,text=True,capture_output=True,timeout=5)
    def world(self):return json.loads(self.e.file.read_text())
    def test_version_without_home_runtime_or_helpers(self):
        env={'PATH':'/nonexistent','XDG_RUNTIME_DIR':str(self.e.root/'unused')}
        r=self.call('--version',env=env);self.assertEqual(r.returncode,0,r.stderr);self.assertFalse((self.e.root/'unused').exists());self.assertEqual(self.world()['events'],[])
    def test_bad_arguments_before_any_io(self):
        for args in [[],['start','legacy'],['start','--project',''],['close','-1'],['close','x'],['stop','']]:
            self.assertNotEqual(self.call(*args).returncode,0)
        self.assertEqual(self.world()['events'],[]);self.assertFalse((self.e.directory/'workspace-columns.lock').exists())
    def test_status_minimal_legacy_is_not_projected_or_saved(self):
        self.e.metadata.write_text('{"version":2,"owners":{"2":"B"}}');before=self.e.metadata.read_bytes()
        r=self.call('status');self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['context_confirmed']);self.assertEqual(self.e.metadata.read_bytes(),before)
    def test_status_missing_state_does_not_initialize(self):
        self.e.metadata.unlink();r=self.call('status');self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(json.loads(r.stdout)['context_confirmed']);self.assertFalse(self.e.metadata.exists())
    def test_unknown_schema_never_repaired(self):
        self.e.metadata.write_text('{"version":99}');self.assertNotEqual(self.call('status').returncode,0);self.assertEqual(self.e.metadata.read_text(),'{"version":99}')
    def test_shared_flock_precedes_native_and_core_requests(self):
        lock=self.e.directory/'workspace-columns.lock'
        with lock.open('w') as stream:
            inode=lock.stat().st_ino;fcntl.flock(stream,fcntl.LOCK_EX)
            p=subprocess.Popen([str(BIN),'status'],env=self.e.env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                time.sleep(.05);self.assertIsNone(p.poll());self.assertEqual(self.world()['events'],[]);self.assertNotIn('_native_seen',self.world())
                fcntl.flock(stream,fcntl.LOCK_UN);out,err=p.communicate(timeout=4);self.assertEqual(p.returncode,0,err)
            finally:
                if p.poll() is None:p.kill();p.wait()
            self.assertEqual(lock.stat().st_ino,inode)
    def replace_manager(self,body):
        path=self.e.root/'bin/manager';path.write_text('#!/usr/bin/python3\n'+body+'\n');path.chmod(0o700)
    def test_malformed_or_unavailable_core_never_falls_back_or_writes(self):
        before=self.e.metadata.read_bytes()
        for body in ["print('bad JSON')","import sys;print('{\"code\":\"transport.unavailable\"}');sys.exit(1)","print('{\"sessions\":[{\"id\":\"B\"}],\"active_session_id\":\"B\"}')","print('{\"sessions\":[],\"active_session_id\":\"missing\"}')"]:
            self.replace_manager(body);r=self.call('start','--neutral');self.assertNotEqual(r.returncode,0);self.assertEqual(self.e.metadata.read_bytes(),before)
    def test_json_and_literal_argv_not_shell(self):
        name='project with spaces; $(touch SHOULD_NOT_EXIST)'
        r=self.call('start','--project',name);self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn(['request',['start','--project',name]],self.world()['events']);self.assertFalse((self.e.root/'SHOULD_NOT_EXIST').exists())
    def test_python_module_override_not_loaded(self):
        self.e.env['SESSION_COLUMNS_SCRIPT']='/does/not/exist.py'
        r=self.call('status');self.assertEqual(r.returncode,0,r.stderr)
    def test_corrupt_or_redirected_metadata_fails_closed(self):
        self.e.metadata.write_text('{broken');self.assertNotEqual(self.call('status').returncode,0)
        self.e.metadata.unlink();target=self.e.root/'preserve';target.write_text('keep');self.e.metadata.symlink_to(target)
        self.assertNotEqual(self.call('status').returncode,0);self.assertEqual(target.read_text(),'keep')
    def test_confirmed_status_shape_for_quickshell(self):
        r=self.call('status');self.assertEqual(r.returncode,0,r.stderr);data=json.loads(r.stdout)
        for key in ['revision','active_session_id','sessions','displayed_context','context_confirmed']:self.assertIn(key,data)
        self.assertEqual(data['active_session_id'],data['displayed_context']);self.assertIs(data['context_confirmed'],True)
    def test_actual_q_lua_binding_still_freezes_keypress_workspace(self):
        binding=ROOT.parent/'configs/hypr/files/keybinds.lua'
        code='''local binds,commands={},{};local ws={id=3};local function proxy() return setmetatable({},{__index=function(t,k)local p=proxy();rawset(t,k,p);return p end,__call=function()return function()end end}) end
hl=proxy();hl.bind=function(k,f)binds[k]=f end;hl.get_active_workspace=function()return ws end;hl.dsp.exec_cmd=function(c)return c end;hl.dispatch=function(c)table.insert(commands,c)end
assert(loadfile('''+json.dumps(str(binding))+'''))();binds['SUPER + Q']();ws.id=4;assert(#commands==1 and commands[1]:match("close 3'$")~=nil)'''
        subprocess.run(['/usr/bin/lua','-'],input=code,text=True,capture_output=True,check=True,timeout=2)

if __name__=='__main__':unittest.main()
