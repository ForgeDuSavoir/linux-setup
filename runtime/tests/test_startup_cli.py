#!/usr/bin/env python3
"""R3 CLI/admin/concurrent-init and temporary ELF cohort installation checks."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from test_startup_parity import Environment,cases,BIN,ADMIN,ROOT

class Cli(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='r3-cli-');self.addCleanup(self.temp.cleanup)
        self.e=Environment(self.temp.name,cases()['01_fresh'])
        self.env={**self.e.env,'HYPRLAND_INSTANCE_SIGNATURE':'one'}
    def call(self,*args,env=None,binary=BIN):return subprocess.run([str(binary),*args],env=env or self.env,capture_output=True,text=True,timeout=5)
    def world(self):return json.loads(self.e.worldfile.read_text())
    def admin(self,op,payload=None):
        # No HOME/runtime/native/core tools: this process must remain a pure transform.
        return subprocess.run([str(ADMIN),op],input=json.dumps(payload),env={'PATH':'/nonexistent'},capture_output=True,text=True,timeout=2)
    def test_version_and_invalid_args_without_actions(self):
        for binary in [BIN,ADMIN]:self.assertEqual(self.call('--version',binary=binary,env={'PATH':'/nonexistent'}).returncode,0)
        self.assertNotEqual(self.call('--not-a-mode').returncode,0);self.assertEqual(self.world()['events'],[]);self.assertFalse(self.e.marker.exists())
    def test_capabilities_and_pure_defer_under_existing_lock(self):
        self.assertEqual(json.loads(self.admin('capabilities').stdout)['version'],1)
        before=self.e.metadata.read_bytes()
        with (self.e.directory/'workspace-columns.lock').open('w') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            r=self.admin('defer-marker',{'instance':'one','previous':None})
            self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['changed'])
        self.assertEqual(self.e.metadata.read_bytes(),before);self.assertFalse(self.e.marker.exists());self.assertEqual(self.world()['events'],[])
    def test_capabilities_without_environment_or_state(self):
        r=self.admin('capabilities');self.assertEqual(r.returncode,0,r.stderr)
        value=json.loads(r.stdout);self.assertEqual(value['version'],1);self.assertEqual(value['core_protocol'],3);self.assertEqual(value['marker_schema'],1)
        self.assertIn('defer-marker',value['operations']);self.assertFalse(self.e.marker.exists());self.assertEqual(self.world()['events'],[])
    def test_pure_defer_preserves_failed_marker(self):
        marker={'version':1,'instance':'one','phase':'failed','extra':'keep'}
        r=self.admin('defer-marker',{'instance':'one','previous':marker});self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),{'changed':False,'marker':marker})
    def test_pure_projection_and_validation_no_implicit_cleanup(self):
        raw={'version':2,'owners':{'1':'A'},'last':{'1':2},'preferred':{'A':1}}
        r=self.admin('project-state',{'raw':raw,'existing_ids':[1,2]});self.assertEqual(r.returncode,0,r.stderr);projected=json.loads(r.stdout)
        self.assertEqual(projected['order'],[1,2]);self.assertEqual(projected['preferred'],{'A':2})
        r=self.admin('validate-state',{'state':projected});self.assertEqual(json.loads(r.stdout),projected)
        self.assertEqual(self.world()['events'],[])
    def test_admin_bad_input_and_operation_no_effects(self):
        for op,value in [('defer-marker',{'instance':'one','previous':{}}),('defer-marker',{'instance':''}),('project-state',{'existing_ids':[1,1]}),('validate-state',{'state':{}}),('unknown',{})]:
            self.assertNotEqual(self.admin(op,value).returncode,0)
        self.assertFalse(self.e.marker.exists());self.assertEqual(self.world()['events'],[])
    def test_two_initializers_share_one_flock_and_launch_one_bar(self):
        lock=self.e.directory/'workspace-columns.lock'
        with lock.open('w') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            processes=[subprocess.Popen([str(BIN)],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
            try:
                time.sleep(.05);self.assertTrue(all(p.poll() is None for p in processes));self.assertEqual(self.world()['events'],[])
                fcntl.flock(stream,fcntl.LOCK_UN)
                for p in processes:
                    out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,err)
            finally:
                for p in processes:
                    if p.poll() is None:p.kill();p.wait()
        world=self.world();self.assertEqual(world['bar_phases'],['ready']);self.assertEqual(world.get('generation',0),0)
        self.assertEqual([e for e in world['events'] if e[0]=='request' and e[1][0] in ('stop','start')],[['request',['stop','A']],['request',['stop','B']]])
    def test_backup_and_marker_private_and_old_bytes_preserved(self):
        before=self.e.metadata.read_bytes();r=self.call();self.assertEqual(r.returncode,0,r.stderr)
        backups=list(self.e.directory.glob('session-startup-backup-*'));self.assertEqual(len(backups),1);backup=backups[0]
        self.assertEqual(backup.stat().st_mode&0o777,0o700)
        self.assertEqual((backup/'workspace-state.json').read_bytes(),before)
        for file in backup.iterdir():self.assertEqual(file.stat().st_mode&0o777,0o600)
        self.assertEqual(self.e.marker.stat().st_mode&0o777,0o600)
        self.assertEqual(json.loads(self.e.marker.read_text())['phase'],'ready')
    def test_failed_marker_blocks_replay_and_second_bar(self):
        world=self.world();world['flags']['lost_reply']=True;self.e.worldfile.write_text(json.dumps(world))
        r=self.call();self.assertEqual(r.returncode,0,r.stderr);after=self.world();self.assertEqual(after['bar_phases'],['failed']);self.assertEqual(json.loads(self.e.marker.read_text())['phase'],'failed')
        r=self.call();self.assertNotEqual(r.returncode,0);self.assertEqual(self.world(),after)
    def test_menu_claim_is_once_per_ready_instance_under_lock(self):
        marker={'version':1,'instance':'one','phase':'ready','startup_menu':'pending','keep':{'x':1}}
        self.e.marker.write_text(json.dumps(marker));state=self.e.metadata.read_bytes()
        processes=[subprocess.Popen([str(BIN),'--claim-menu'],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        replies=[]
        for p in processes:
            out,err=p.communicate(timeout=4);self.assertEqual(p.returncode,0,err);replies.append(json.loads(out)['show'])
        self.assertEqual(sorted(replies),[False,True])
        self.assertEqual(json.loads(self.e.marker.read_text()),{**marker,'startup_menu':'consumed'})
        self.assertEqual(self.e.metadata.read_bytes(),state);self.assertEqual(self.world()['events'],[])
        self.assertNotIn('bar_phases',self.world())
    def test_menu_claim_ignores_old_wrong_failed_deferred_and_absent_markers(self):
        for marker in [None,{'version':1,'instance':'other','phase':'ready','startup_menu':'pending'}, {'version':1,'instance':'one','phase':'ready','session_id':'legacy'},*({'version':1,'instance':'one','phase':p,'startup_menu':'pending'} for p in ['initializing','failed','deferred'])]:
            self.e.marker.unlink(missing_ok=True)
            if marker is not None:self.e.marker.write_text(json.dumps(marker))
            before=self.e.marker.read_bytes() if self.e.marker.exists() else None
            r=self.call('--claim-menu');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),{'show':False})
            self.assertEqual(self.e.marker.read_bytes() if self.e.marker.exists() else None,before)
        self.assertEqual(self.world()['events'],[]);self.assertNotIn('bar_phases',self.world())
    def test_symlink_marker_refuses_reset_and_does_not_overwrite_target(self):
        target=self.e.root/'preserve';contents=json.dumps({'version':1,'instance':'old','phase':'deferred'});target.write_text(contents);self.e.marker.symlink_to(target)
        self.call();self.assertEqual(target.read_text(),contents);self.assertEqual(self.world()['events'],[])
    def test_temporary_elf_cohort_and_python_installer_admin_flow(self):
        installed=self.e.root/'.local/bin';installed.mkdir(parents=True)
        for name in ['workspace-controller','session-desktop','session-startup','agora-desktop-admin']:
            shutil.copy2(ROOT/'target/release'/name,installed/name)
        # Installer holds lock, computes marker only through the pure ELF helper,
        # then publishes it itself. No importlib or reset command is involved.
        before=self.e.metadata.read_bytes()
        with (self.e.directory/'workspace-columns.lock').open('w') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            r=subprocess.run([str(installed/'agora-desktop-admin'),'defer-marker'],input=json.dumps({'instance':'one','previous':None}),env={'PATH':'/nonexistent'},text=True,capture_output=True,timeout=2)
            self.assertEqual(r.returncode,0,r.stderr);self.e.marker.write_text(json.dumps(json.loads(r.stdout)['marker']))
        self.assertEqual(self.e.metadata.read_bytes(),before);self.assertEqual(self.world()['events'],[])
        r=self.call(binary=installed/'session-startup');self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('bar_phases',self.world())
        world=self.world();world['instance']='next-login';self.e.worldfile.write_text(json.dumps(world))
        r=self.call(binary=installed/'session-startup',env={**self.env,'HYPRLAND_INSTANCE_SIGNATURE':'next-login'})
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.world()['bar_phases'],['ready']);self.assertEqual(self.world().get('generation',0),0)

if __name__=='__main__':unittest.main()
