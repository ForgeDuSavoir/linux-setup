#!/usr/bin/env python3
"""Real Rust CLI, private HOME/runtime/locks and strict fake hyprctl; no desktop IO."""
import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'target/release/workspace-controller'
DATA=json.loads((ROOT.parent/'tools/runtime-migration/fixtures.json').read_text())

class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='r1-cli-');self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.runtime=self.home/'run';self.directory=self.runtime/'hyprland';self.directory.mkdir(parents=True)
        self.state=self.directory/'workspace-columns.json';self.state.write_text(json.dumps(DATA['desktop']))
        self.world=self.home/'world.json';self.world.write_text(json.dumps(DATA['native']))
        self.trace=self.home/'trace.jsonl';tools=self.home/'bin';tools.mkdir()
        helper=tools/'hyprctl';helper.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
world=json.loads(Path(os.environ['FAKE_WORLD']).read_text())
with Path(os.environ['FAKE_TRACE']).open('a') as stream:stream.write(json.dumps(sys.argv[1:])+'\\n')
mode=world.get('_mode','')
if mode=='badjson':print('{');sys.exit(0)
if mode=='exit':sys.exit(9)
if mode=='stdout_error':print('error: synthetic');sys.exit(0)
if mode=='timeout':print('error: synthetic timeout; outcome uncertain');sys.exit(0)
if mode=='stderr_error':print('error: synthetic',file=sys.stderr);sys.exit(0)
name=sys.argv[1]
if name in ('dispatch','eval'):print('ok')
elif name in world:print(json.dumps(world[name]))
else:raise SystemExit('unexpected fake query')
''');helper.chmod(0o700)
        self.env={**os.environ,'HOME':str(self.home),'XDG_RUNTIME_DIR':str(self.runtime),'PATH':str(tools),'FAKE_WORLD':str(self.world),'FAKE_TRACE':str(self.trace)}
    def run_cli(self,*args):return subprocess.run([str(BIN),*args],env=self.env,text=True,capture_output=True,timeout=4)
    def change(self,**values):
        data=json.loads(self.world.read_text());data.update(values);self.world.write_text(json.dumps(data))
    def test_version_without_runtime_or_helpers(self):
        self.state.unlink();self.env['XDG_RUNTIME_DIR']=str(self.home/'unused')
        result=self.run_cli('--version');self.assertEqual(result.returncode,0,result.stderr);self.assertFalse((self.home/'unused').exists());self.assertFalse(self.trace.exists())
    def test_snapshot_read_only(self):
        before=self.state.read_bytes();r=self.run_cli('snapshot');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),DATA['snapshot']);self.assertEqual(self.state.read_bytes(),before)
    def test_runtime_path_with_spaces_and_quotes(self):
        runtime=self.home/"runtime with ' spaces";self.env['XDG_RUNTIME_DIR']=str(runtime)
        r=self.run_cli('snapshot');self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((runtime/'hyprland/workspace-columns.lock').exists())
        self.assertFalse((runtime/'hyprland/workspace-columns.json').exists())
    def test_snapshot_missing_does_not_initialize(self):
        self.state.unlink();r=self.run_cli('snapshot');self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(self.state.exists())
    def test_legacy_snapshot_does_not_migrate(self):
        self.state.write_text(json.dumps({'version':2,'owners':{'1':'A'},'last':{},'preferred':{}}));before=self.state.read_bytes();r=self.run_cli('snapshot');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.state.read_bytes(),before)
    def test_migrate_publishes_private_json_no_dispatch(self):
        self.state.write_text(json.dumps({'version':2,'owners':{'1':'A'},'last':{},'preferred':{}}));r=self.run_cli('migrate');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(self.state.read_text())['version'],3);self.assertEqual(self.state.stat().st_mode&0o777,0o600);self.assertNotIn('dispatch',self.trace.read_text());self.assertNotIn('eval',self.trace.read_text())
    def test_invalid_cli_before_any_state_or_native_io(self):
        for args in [[],['toggle-row'],['closed','-1'],['focus-workspace','x']]:
            with self.subTest(args=args):
                self.assertNotEqual(self.run_cli(*args).returncode,0);self.assertFalse(self.trace.exists())
    def test_unknown_schema_unchanged(self):
        self.state.write_text('{"version":99}');before=self.state.read_bytes();self.assertNotEqual(self.run_cli('migrate').returncode,0);self.assertEqual(self.state.read_bytes(),before)
    def test_corrupt_json_unchanged(self):
        self.state.write_text('{broken');self.assertNotEqual(self.run_cli('snapshot').returncode,0);self.assertEqual(self.state.read_text(),'{broken')
    def test_native_failures_do_not_replace_state(self):
        before=self.state.read_bytes()
        for mode in ['badjson','exit','stdout_error','stderr_error','timeout']:
            self.change(_mode=mode);self.assertNotEqual(self.run_cli('migrate').returncode,0);self.assertEqual(self.state.read_bytes(),before)
    def test_symlink_and_fifo_state_refused_without_hang(self):
        self.state.unlink();target=self.home/'preserve';target.write_text('keep');self.state.symlink_to(target)
        self.assertNotEqual(self.run_cli('snapshot').returncode,0);self.assertEqual(target.read_text(),'keep');self.state.unlink();os.mkfifo(self.state)
        self.assertNotEqual(self.run_cli('snapshot').returncode,0)
    def test_symlink_and_fifo_lock_refused(self):
        lock=self.directory/'workspace-columns.lock';lock.symlink_to(self.state);self.assertNotEqual(self.run_cli('snapshot').returncode,0);lock.unlink();os.mkfifo(lock);self.assertNotEqual(self.run_cli('snapshot').returncode,0)
    def test_legacy_flock_interoperability_and_stable_inode(self):
        lock=self.directory/'workspace-columns.lock'
        with lock.open('w') as stream:
            inode=lock.stat().st_ino;fcntl.flock(stream,fcntl.LOCK_EX)
            process=subprocess.Popen([str(BIN),'migrate'],env=self.env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                time.sleep(0.05);self.assertIsNone(process.poll());self.assertFalse(self.trace.exists())
                fcntl.flock(stream,fcntl.LOCK_UN);out,err=process.communicate(timeout=3);self.assertEqual(process.returncode,0,err)
            finally:
                if process.poll() is None:process.kill();process.wait()
            self.assertEqual(lock.stat().st_ino,inode)
    def test_hide_first_does_not_touch_invalid_state(self):
        self.state.write_text('{broken');before=self.state.read_bytes()
        for special in ['special:global','special:session-ai','special:sm-11111111-1111-1111-1111-111111111111-notes']:
            monitors=copy.deepcopy(DATA['native']['monitors']);monitors[0]['specialWorkspace']['name']=special;self.change(monitors=monitors)
            for args in [['cycle'],['create-empty'],['focus-workspace','2']]:
                r=self.run_cli(*args);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.state.read_bytes(),before)
        self.assertIn('toggle_special',self.trace.read_text())
    def test_other_monitor_scratchpad_does_not_intercept(self):
        monitors=copy.deepcopy(DATA['native']['monitors']);monitors.append({'focused':False,'activeWorkspace':{'id':9},'specialWorkspace':{'name':'special:global'}});self.change(monitors=monitors)
        r=self.run_cli('cycle');self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('toggle_special',self.trace.read_text())
    def test_no_focused_monitor_refuses_navigation(self):
        self.change(monitors=[{'focused':False},{'focused':False}]);before=self.state.read_bytes();self.assertNotEqual(self.run_cli('cycle').returncode,0);self.assertEqual(self.state.read_bytes(),before)
    def test_unsafe_special_refuses_without_state_write(self):
        monitors=copy.deepcopy(DATA['native']['monitors']);monitors[0]['specialWorkspace']['name']='special:bad"name';self.change(monitors=monitors);before=self.state.read_bytes();self.assertNotEqual(self.run_cli('cycle').returncode,0);self.assertEqual(self.state.read_bytes(),before)
    def test_unknown_native_workspace_stays_unowned(self):
        self.change(workspaces=[{'id':1},{'id':2},{'id':9}]);r=self.run_cli('migrate');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(self.state.read_text())['owners']['9'],'neutral')
    def test_lua_guards_from_real_rust_generation(self):
        from test_workspace_parity import cases,FIXTURE
        wrapper='''local code=io.read('*a');local chunk=assert(load(code));hl={get_workspace=function()return {}end};assert(not pcall(chunk));local called=0;local function spec(v)return v end;hl={get_workspace=function()return nil end,dsp={focus=spec,window={move=spec}},dispatch=function(v)assert(v.workspace==9);called=called+1 end};assert(pcall(chunk));assert(called==1)'''
        for case in ['34_guarded_focus','35_guarded_move']:
            result=json.loads(subprocess.check_output([str(FIXTURE)],input=json.dumps(cases()[case]),text=True))
            for kind,code in result['codes']:
                self.assertEqual(kind,'eval');subprocess.run(['/usr/bin/lua','-e',wrapper],input=code,text=True,capture_output=True,check=True,timeout=2)

if __name__=='__main__':unittest.main()
