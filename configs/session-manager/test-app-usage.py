#!/usr/bin/env python3
"""Usage/context/Git end-to-end checks; private HOME, fake core/desktop/launchers."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('launcher_fixture',HERE/'test-session-app-launcher.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
BINARY=base.BINARY


class Usage(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory(prefix='usage-cli-');self.addCleanup(temp.cleanup)
        f=base.Fixture(Path(temp.name))
        # Mutations occur only inside this owned fixture, after displayed data is captured.
        rofi=f.root/'bin/rofi'
        rofi.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
r=Path(os.environ['HOME']);c=json.loads((r/'fixture.json').read_text())
(r/'rows').write_bytes(sys.stdin.buffer.read());(r/'rofi-args').write_text(json.dumps(sys.argv[1:]))
if c.get('mutate_rofi'):
 c.update(c['mutate_rofi']);(r/'fixture.json').write_text(json.dumps(c))
 m=r/'runtime/hyprland/workspace-columns.json';m.write_text(json.dumps({'version':3,'owners':{'1':c.get('owner',c['active_session_id'] or 'neutral')}}))
if c.get('change_entry'): Path(c['change_entry']).write_text('[Desktop Entry]\\nType=Application\\nName=Changed\\nExec=/bin/false\\n')
if c.get('move_project'):
 old=Path(c['projects'][0]['path']);new=old.with_name('moved');old.rename(new)
 if c.get('replace_project'): old.mkdir();(old/'.session-manager/apps').mkdir(parents=True)
 else: c['projects'][0]['path']=str(new)
 (r/'fixture.json').write_text(json.dumps(c))
print(c['choice']);raise SystemExit(c['rofi_status'])
''')
        for name in ['gtk-launch','gio']:
            (f.root/'bin'/name).write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
r=Path(os.environ['HOME']);c=json.loads((r/'fixture.json').read_text())
(r/'launch').write_text(json.dumps([Path(sys.argv[0]).name,*sys.argv[1:]]))
if c.get('mutate_launch'):
 c.update(c['mutate_launch']);(r/'fixture.json').write_text(json.dumps(c))
 (r/'runtime/hyprland/workspace-columns.json').write_text(json.dumps({'version':3,'owners':{'1':c.get('owner',c['active_session_id'] or 'neutral')}}))
raise SystemExit(c['launch_status'])
''')
        return f

    def project(self,f): f.project_app();f.app['origin']='installed'
    def launch(self,f,args=(),code=0):
        result=f.run([str(BINARY)],args);self.assertEqual(result[0],code,result[2]);return result
    def data(self,f,bucket='project'):
        return f.project/'.session-manager/app-usage.json' if bucket=='project' else f.root/f'state/session-app-launcher/{bucket}.json'
    def write_history(self,path,apps):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'version':1,'apps':apps}));path.chmod(0o600)
    def count(self,path,id='firefox.desktop'): return json.loads(path.read_text())['apps'][id]['count']
    def git(self,f,*args,cwd=None):
        return subprocess.check_output(['git','-c','user.name=Fixture','-c','user.email=fixture@invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',*args],cwd=cwd or f.project,env={**f.env,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'})
    def init_git(self,f,cwd=None): self.git(f,'init','-q',cwd=cwd)

    def test_project_installed_only_apps_still_use_project_history(self):
        f=self.fixture();self.project(f);self.launch(f);self.assertEqual(self.count(self.data(f)),1)
        self.assertFalse(self.data(f,'unowned').exists());self.assertFalse(self.data(f,'neutral').exists())
    def test_same_project_sessions_share_menu_only_counter(self):
        f=self.fixture();self.project(f);self.launch(f)
        f.config['sessions'].append({'id':'second','source':{'kind':'project','project_name':'P'}});f.config['active_session_id']='second'
        before=self.data(f).read_bytes();self.launch(f,['--browser']);self.assertEqual(self.data(f).read_bytes(),before)
        self.launch(f);self.assertEqual(self.count(self.data(f)),2)
    def test_independent_projects_and_move_reopen(self):
        f=self.fixture();self.project(f);self.launch(f)
        other=f.root/'other';(other/'.session-manager/apps').mkdir(parents=True)
        f.config['projects'][0]['path']=str(other);f.project=other;self.launch(f);self.assertEqual(self.count(self.data(f)),1)
        moved=f.root/'moved';other.rename(moved);f.project=moved;f.config['projects'][0]['path']=str(moved)
        self.launch(f);self.assertEqual(self.count(self.data(f)),2)
    def test_neutral_and_no_active_are_separate_persistent_buckets(self):
        f=self.fixture();f.config['sessions']=[{'id':'N1','source':{'kind':'neutral'}}];f.config['active_session_id']='N1'
        self.launch(f);self.assertEqual(self.count(self.data(f,'neutral')),1)
        f.config['sessions']=[{'id':'N2','source':{'kind':'neutral'}}];f.config['active_session_id']='N2';self.launch(f)
        f.config['active_session_id']=None;self.launch(f);self.assertEqual(self.count(self.data(f,'neutral')),2);self.assertEqual(self.count(self.data(f,'unowned')),1)
    def test_initial_sort_and_selected_id_not_old_catalog_index(self):
        f=self.fixture();self.project(f)
        f.config['applications'].append({'id':'other.desktop','name':'Other','origin':'installed'})
        f.desktop(f.root/'data/applications/other.desktop')
        now=int(time.time());self.write_history(self.data(f),{'other.desktop':{'count':5,'weight':5,'last_used':now}})
        result=self.launch(f)
        self.assertTrue(b'other.desktop' in result[1][0].splitlines()[0]);self.assertIn('-no-sort',json.loads(result[1][1]))
        self.assertEqual(json.loads(result[1][2]),['gtk-launch','other.desktop']);self.assertEqual(self.count(self.data(f),'other.desktop'),6)
    def test_cancel_no_history_lock_or_git_mutation(self):
        f=self.fixture();self.project(f);self.init_git(f);before=(f.project/'.git/info/exclude').read_bytes();f.config['rofi_status']=1
        self.launch(f);self.assertFalse(self.data(f).exists());self.assertFalse(self.data(f).with_suffix('.lock').exists());self.assertEqual((f.project/'.git/info/exclude').read_bytes(),before)
    def test_browser_creates_no_history_lock_or_git_rules(self):
        f=self.fixture();self.project(f);self.init_git(f)
        before=(f.project/'.git/info/exclude').read_bytes()
        result=self.launch(f,['--browser'])
        self.assertIsNotNone(result[1][2]);self.assertFalse(self.data(f).exists())
        self.assertFalse((f.project/'.session-manager/app-usage.lock').exists())
        self.assertEqual((f.project/'.git/info/exclude').read_bytes(),before)

    def test_browser_neutral_and_unowned_leave_existing_statistics_unchanged(self):
        for neutral in [False,True]:
            f=self.fixture()
            if neutral:
                f.config['sessions']=[{'id':'N1','source':{'kind':'neutral'}}];f.config['active_session_id']='N1'
            bucket='neutral' if neutral else 'unowned';path=self.data(f,bucket)
            self.launch(f,['--browser']);self.assertFalse(path.exists())
            self.write_history(path,{'firefox.desktop':{'count':3,'weight':3,'last_used':int(time.time())}})
            before=path.read_bytes();stamp=path.stat().st_mtime_ns
            self.launch(f,['--browser'])
            self.assertEqual(path.read_bytes(),before);self.assertEqual(path.stat().st_mtime_ns,stamp)

    def test_rejected_launch_has_no_measure(self):
        f=self.fixture();self.project(f);f.config['launch_status']=1;self.launch(f,code=1);self.assertFalse(self.data(f).exists())
    def test_changed_uuid_even_same_project_blocks_launch(self):
        f=self.fixture();self.project(f);f.config['sessions'].append({'id':'second','source':{'kind':'project','project_name':'P'}})
        f.config['mutate_rofi']={'active_session_id':'second'};result=self.launch(f,code=1)
        self.assertIsNone(result[1][2]);self.assertFalse(self.data(f).exists())
    def test_unrelated_revision_change_is_allowed(self):
        f=self.fixture();self.project(f);f.config['mutate_rofi']={'revision':2};self.launch(f);self.assertEqual(self.count(self.data(f)),1)
    def test_changed_entry_blocks_launch(self):
        f=self.fixture();self.project(f);f.config['change_entry']=str(f.root/'data/applications/firefox.desktop')
        result=self.launch(f,code=1);self.assertIsNone(result[1][2]);self.assertFalse(self.data(f).exists())
    def test_move_during_menu_does_not_recreate_project(self):
        f=self.fixture();self.project(f);f.config['move_project']=True;result=self.launch(f,code=1)
        self.assertIsNone(result[1][2]);self.assertFalse(f.project.exists());self.assertFalse((f.root/'moved/.session-manager/app-usage.json').exists())
    def test_replaced_directory_with_same_path_is_refused(self):
        f=self.fixture();self.project(f);f.config.update(move_project=True,replace_project=True);result=self.launch(f,code=1)
        self.assertIsNone(result[1][2]);self.assertFalse(self.data(f).exists())
    def test_changed_context_after_acceptance_skips_measure_without_error(self):
        f=self.fixture();self.project(f);f.config['mutate_launch']={'active_session_id':None}
        result=self.launch(f);self.assertIsNotNone(result[1][2]);self.assertIn(b'skipped',result[2]);self.assertFalse(self.data(f).exists());self.assertFalse(self.data(f,'unowned').exists())
    def test_unconfirmed_desktop_never_becomes_unowned_fallback(self):
        f=self.fixture();self.project(f);f.config['owner']='neutral';result=self.launch(f,code=1)
        self.assertIsNone(result[1][0]);self.assertFalse(self.data(f,'unowned').exists())
    def test_invalid_history_preserved_and_launch_works(self):
        for value in [b'corrupt',b'{"version":2,"apps":{}}',b'{"version":1,"apps":{},"apps":{}}']:
            f=self.fixture();self.project(f);path=self.data(f);path.write_bytes(value);path.chmod(0o600)
            result=self.launch(f);self.assertIsNotNone(result[1][2]);self.assertEqual(path.read_bytes(),value);self.assertIn(b'skipped',result[2])
    def test_readonly_history_does_not_block_app_or_get_replaced(self):
        f=self.fixture();self.project(f);path=self.data(f);self.write_history(path,{});path.chmod(0o400);before=path.read_bytes()
        self.launch(f);self.assertEqual(path.read_bytes(),before)
    def test_symlinked_history_does_not_modify_target(self):
        f=self.fixture();self.project(f);target=f.root/'external';target.write_text('keep');self.data(f).symlink_to(target)
        self.launch(f);self.assertEqual(target.read_text(),'keep');self.assertTrue(self.data(f).is_symlink())
    def test_invalid_global_state_path_disables_only_history(self):
        f=self.fixture();f.env['XDG_STATE_HOME']='relative';self.launch(f);self.assertFalse((f.root/'relative').exists());self.assertFalse(self.data(f,'unowned').exists())
    def test_hist_lock_timeout_is_nonfatal_and_no_counter_lost(self):
        f=self.fixture();self.project(f);self.launch(f);path=self.data(f);before=path.read_bytes()
        with (f.project/'.session-manager/app-usage.lock').open('r') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);result=self.launch(f)
        self.assertIn(b'deadline',result[2]);self.assertEqual(path.read_bytes(),before)
    def test_git_exact_local_exclusions_and_index_untouched(self):
        f=self.fixture();self.project(f);self.init_git(f)
        tracked=f.project/'keep.txt';tracked.write_text('keep');self.git(f,'add','keep.txt')
        index=(f.project/'.git/index').read_bytes();exclude=f.project/'.git/info/exclude';old=exclude.read_bytes()
        self.launch(f);self.assertEqual(self.count(self.data(f)),1);self.assertEqual((f.project/'.git/index').read_bytes(),index);self.assertTrue(exclude.read_bytes().startswith(old))
        self.assertEqual(self.git(f,'check-ignore','.session-manager/app-usage.json').strip(),b'.session-manager/app-usage.json')
        size=exclude.stat().st_size;self.launch(f);self.assertEqual(exclude.stat().st_size,size)
        self.assertEqual(self.git(f,'check-ignore','.session-manager/.app-usage.tmp-fixture').strip(),b'.session-manager/.app-usage.tmp-fixture')
    def test_git_parent_and_special_characters(self):
        f=self.fixture();self.init_git(f,cwd=f.root);new=f.root/'p [a]*?! #é';f.project.rename(new);f.project=new
        self.project(f);f.config['projects'][0]['path']=str(new)
        self.launch(f);self.assertEqual(self.count(self.data(f)),1)
        relative=f.project.relative_to(f.root)/'.session-manager/app-usage.json'
        self.assertEqual(self.git(f,'check-ignore','-q',str(relative),cwd=f.root),b'')
    def test_tracked_history_is_never_untracked_or_updated(self):
        f=self.fixture();self.project(f);self.init_git(f);self.write_history(self.data(f),{})
        self.git(f,'add','.session-manager/app-usage.json');index=(f.project/'.git/index').read_bytes();before=self.data(f).read_bytes()
        result=self.launch(f);self.assertEqual(self.data(f).read_bytes(),before);self.assertEqual((f.project/'.git/index').read_bytes(),index);self.assertIn(b'tracked',result[2]);self.assertFalse((f.project/'.session-manager/app-usage.lock').exists())
    def test_worktree_uses_common_git_info_exclude(self):
        f=self.fixture();self.init_git(f,cwd=f.root);(f.root/'keep').write_text('keep');self.git(f,'add','keep',cwd=f.root);self.git(f,'commit','-qm','fixture',cwd=f.root)
        worktree=f.root/'linked';self.git(f,'worktree','add','-q','-b','fixture-branch',str(worktree),cwd=f.root)
        (worktree/'.session-manager/apps').mkdir(parents=True);f.project=worktree;self.project(f);f.config['projects'][0]['path']=str(worktree)
        self.launch(f);self.assertEqual(self.count(self.data(f)),1);self.assertTrue((worktree/'.git').is_file())
        self.assertIn(b'/.session-manager/app-usage.json',(f.root/'.git/info/exclude').read_bytes())
    def test_launch_deadline_does_not_record_or_replay(self):
        f=self.fixture();self.project(f);f.run([str(BINARY)],['--version'])
        (f.root/'bin/gtk-launch').write_text('#!/bin/sh\nprintf started >> "$HOME/launch-started"\nexec /bin/sleep 60\n')
        result=subprocess.run([str(BINARY),'--browser'],env=f.env,capture_output=True,timeout=40)
        self.assertEqual(result.returncode,1);self.assertIn(b'deadline',result.stderr)
        self.assertFalse(self.data(f).exists());self.assertEqual((f.root/'launch-started').read_text(),'started')

    def test_scope_change_after_launch_transport_failure_is_nonfatal(self):
        f=self.fixture();self.project(f);f.config['mutate_launch']={'request_error':True}
        result=self.launch(f);self.assertIsNotNone(result[1][2]);self.assertFalse(self.data(f).exists())

    def test_symlink_history_and_metadata_directory_are_not_followed(self):
        for directory in [False,True]:
            f=self.fixture();self.project(f);outside=f.root/'outside';outside.mkdir()
            keep=outside/'app-usage.json';keep.write_text('keep');keep.chmod(0o600)
            if directory:
                for entry in (f.project/'.session-manager/apps').iterdir(): entry.unlink()
                (f.project/'.session-manager/apps').rmdir();(f.project/'.session-manager').rmdir()
                (f.project/'.session-manager').symlink_to(outside,target_is_directory=True)
            else: self.data(f).symlink_to(keep)
            self.launch(f);self.assertEqual(keep.read_text(),'keep')

    def test_newline_relative_git_path_disables_recording_without_dirty_lock(self):
        f=self.fixture();self.init_git(f,cwd=f.root);new=f.root/('p'+chr(10)+'newline');f.project.rename(new);f.project=new
        self.project(f);f.config['projects'][0]['path']=str(new)
        self.launch(f);self.assertFalse(self.data(f).exists());self.assertFalse((new/'.session-manager/app-usage.lock').exists())

    def test_legacy_metadata_status_matches_existing_helper(self):
        f=self.fixture();self.project(f)
        f.config['desktop']={'version':2,'owners':{'2':'fixture'}}
        f.config['monitors']=[{'focused':True,'activeWorkspace':{'id':3},'specialWorkspace':{'id':0,'name':''}}]
        self.launch(f)
        env={**f.env,'SESSION_COLUMNS_SCRIPT':str(HERE.parent/'hypr/files/Scripts/workspace-columns.py')}
        code='import importlib.util,json; s=importlib.util.spec_from_file_location("status",'+repr(str(HERE/'session-desktop.py'))+');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(json.dumps(m.status()))'
        status=json.loads(subprocess.check_output(['/usr/bin/python3','-c',code],env=env))
        self.assertTrue(status['context_confirmed']);self.assertEqual(status['displayed_context'],'fixture')

    def test_runtime_context_mismatch_shared_and_scoped_specials(self):
        for special,allowed in [('special:global',True),('special:sm-other-ai',False),('special:session-ai',False)]:
            f=self.fixture();self.project(f)
            f.config['monitors']=[{'focused':True,'activeWorkspace':{'id':1},'specialWorkspace':{'id':-1,'name':special}}]
            self.launch(f,code=0 if allowed else 1)
            self.assertEqual(self.data(f).exists(),allowed)

    def test_parallel_cli_processes_merge_counts_and_git_exclusion(self):
        f=self.fixture();self.project(f);self.init_git(f);self.launch(f)
        processes=[subprocess.Popen([str(BINARY)],env=f.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
        for process in processes:
            _,error=process.communicate(timeout=10);self.assertEqual(process.returncode,0,error)
        self.assertEqual(self.count(self.data(f)),3)
        lines=(f.project/'.git/info/exclude').read_text().splitlines()
        self.assertEqual(lines.count('/.session-manager/app-usage.json'),1)

    def test_readonly_git_exclude_disables_stats_not_launch(self):
        f=self.fixture();self.project(f);self.init_git(f);exclude=f.project/'.git/info/exclude';before=exclude.read_bytes();exclude.chmod(0o400)
        self.launch(f);self.assertFalse(self.data(f).exists());self.assertEqual(exclude.read_bytes(),before)


if __name__=='__main__': unittest.main()
