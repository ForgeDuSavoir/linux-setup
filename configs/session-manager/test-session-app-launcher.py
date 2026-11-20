#!/usr/bin/env python3
"""Executable parity: Rust vs frozen Python oracle; private HOME and fake tools only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
BINARY = HERE/'app-launcher/target/release/session-app-launcher'
LEGACY = HERE/'app-launcher/tests/fixtures/legacy-launcher.py'
assert BINARY.is_file(), 'Build the locked release Rust launcher first'


class Fixture:
    def __init__(self, root):
        self.root=root
        for name in ['bin','.local/bin','data/applications','runtime','state','project with space/.session-manager/apps']:
            (root/name).mkdir(parents=True,exist_ok=True)
        self.project=root/'project with space'
        self.app={'id':'firefox.desktop','name':'Core Firefox','origin':'installed','icon':'firefox'}
        self.config={'applications':[self.app], 'sessions':[], 'active_session_id':None,
                     'projects':[{'name':'P','path':str(self.project)}], 'revision':1, 'choice':'0','rofi_status':0,'launch_status':0}
        manager=root/'.local/bin/session-manager'
        manager.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['HOME']); c=json.loads((root/'fixture.json').read_text()); args=sys.argv[1:]
with (root/'queries').open('a') as stream: stream.write(json.dumps(args)+'\\n')
if c.get('request_error'): print('{}'); raise SystemExit(1)
if c.get('malformed'): print('invalid'); raise SystemExit(0)
if args==['--json','application','list']: value={'applications':c['applications']}
elif args==['--json','session','list']: value={'sessions':c['sessions'],'active_session_id':c['active_session_id'],'revision':c.get('revision',1)}
elif args==['--json','project','list']: value={'projects':c['projects']}
else: raise SystemExit('forbidden request')
print(json.dumps(value))
'''); manager.chmod(0o700)
        rofi=root/'bin/rofi'
        rofi.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['HOME']); c=json.loads((root/'fixture.json').read_text())
(root/'rows').write_bytes(sys.stdin.buffer.read()); (root/'rofi-args').write_text(json.dumps(sys.argv[1:]))
print(c['choice']); raise SystemExit(c['rofi_status'])
'''); rofi.chmod(0o700)
        for command in ['gtk-launch','gio']:
            path=root/'bin'/command
            path.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['HOME']); c=json.loads((root/'fixture.json').read_text())
(root/'launch').write_text(json.dumps([Path(sys.argv[0]).name,*sys.argv[1:]]))
raise SystemExit(c['launch_status'])
'''); path.chmod(0o700)
        self.env={'HOME':str(root),'PATH':str(root/'bin')+':/usr/bin:/bin',
                  'XDG_CONFIG_HOME':str(root/'config'),'XDG_DATA_HOME':str(root/'data'),
                  'XDG_DATA_DIRS':str(root/'data'),'XDG_STATE_HOME':str(root/'state'),
                  'XDG_RUNTIME_DIR':str(root/'runtime'),'LANG':'C','LC_ALL':'C'}
        self.desktop(root/'data/applications/firefox.desktop')
        (root/'runtime/hyprland').mkdir()
        hypr=root/'bin/hyprctl'
        hypr.write_text('#!/usr/bin/python3\nimport json,os\nfrom pathlib import Path\nr=Path(os.environ["HOME"]);c=json.loads((r/"fixture.json").read_text());print(json.dumps(c.get("monitors",[{"focused":True,"activeWorkspace":{"id":1},"specialWorkspace":{"id":0,"name":""}}])))\n')
        hypr.chmod(0o700)

    def desktop(self,path,extra=''):
        path.write_text('[Desktop Entry]\nType=Application\nName=Firefox <&>\nGenericName=Web Browser\nKeywords=browser;search;\nComment=Browse\nExec=/bin/false %u\n'+extra)

    def project_app(self):
        self.app['origin']='project'
        self.config['sessions']=[{'id':'fixture','source':{'kind':'project','project_name':'P'}}]
        self.config['active_session_id']='fixture'
        self.desktop(self.project/'.session-manager/apps/firefox.desktop')

    def run(self,program,args=()):
        for name in ['rows','rofi-args','launch','queries']: (self.root/name).unlink(missing_ok=True)
        (self.root/'fixture.json').write_text(json.dumps(self.config))
        meta=self.root/'runtime/hyprland/workspace-columns.json'
        meta.write_text(json.dumps(self.config.get('desktop',{'version':3,'owners':{'1':self.config.get('owner',self.config['active_session_id'] or 'neutral')}})))
        meta.chmod(0o600)
        result=subprocess.run([*program,*args],env=self.env,capture_output=True,timeout=8)
        outputs=tuple((self.root/name).read_bytes() if (self.root/name).exists() else None for name in ['rows','rofi-args','launch','queries'])
        return result.returncode,outputs,result.stderr


class Parity(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory(prefix='launcher-parity-'); self.addCleanup(temp.cleanup)
        return Fixture(Path(temp.name))
    def compare(self,f,args=(),expected=0):
        legacy=f.run(['/usr/bin/python3',str(LEGACY)],args)
        rust=f.run([str(BINARY)],args)
        self.assertEqual(rust[0],expected,rust[2]); self.assertEqual(legacy[0],expected,legacy[2])
        # History adds context queries, initial ranking and -no-sort intentionally.
        self.assertEqual(rust[1][2],legacy[1][2])
        if expected==0:
            self.assertEqual(rust[1][0],legacy[1][0])
            if rust[1][1] is not None:
                self.assertEqual([a for a in json.loads(rust[1][1]) if a!='-no-sort'],json.loads(legacy[1][1]))
        return rust

    def test_installed_menu_metadata_and_arguments(self): self.compare(self.fixture())
    def test_project_menu_and_literal_path(self):
        f=self.fixture(); f.project_app(); result=self.compare(f)
        self.assertEqual(json.loads(result[1][2]),['gio','launch',str(f.project/'.session-manager/apps/firefox.desktop')])
    def test_installed_browser_does_not_read_project_or_run_rofi(self):
        result=self.compare(self.fixture(),['--browser']); self.assertIsNone(result[1][0])
        self.assertEqual(json.loads(result[1][2]),['gtk-launch','firefox.desktop'])
    def test_project_browser(self):
        f=self.fixture(); f.project_app(); self.compare(f,['--browser'])
    def test_neutral_with_installed_apps(self):
        f=self.fixture(); f.config['sessions']=[{'id':'N','source':{'kind':'neutral'}}]; f.config['active_session_id']='N'; self.compare(f)
    def test_empty_catalog(self):
        f=self.fixture(); f.config['applications']=[]; self.compare(f)
    def test_missing_browser(self):
        f=self.fixture(); f.config['applications']=[]; self.compare(f,['--browser'],1)
    def test_escape(self):
        f=self.fixture(); f.config['rofi_status']=1; self.compare(f)
    def test_invalid_selection(self):
        for choice in ['','-1','99','not-an-index']:
            f=self.fixture(); f.config['choice']=choice; self.compare(f,expected=1)
    def test_failed_launch(self):
        f=self.fixture(); f.config['launch_status']=1; self.compare(f,expected=1)
    def test_failed_core_request(self):
        f=self.fixture(); f.config['request_error']=True; self.compare(f,expected=1)
    def test_bad_json(self):
        f=self.fixture(); f.config['malformed']=True; self.compare(f,expected=1)
    def test_invalid_cli(self): self.compare(self.fixture(),['--unknown'],1)
    def test_project_removed_does_not_launch_installed_profile(self):
        f=self.fixture(); f.project_app(); f.config['projects']=[]; self.compare(f,['--browser'],1)
    def test_symlinked_project_entry_is_not_launched(self):
        f=self.fixture(); f.project_app(); entry=f.project/'.session-manager/apps/firefox.desktop'; entry.unlink(); entry.symlink_to(f.root/'data/applications/firefox.desktop'); self.compare(f,expected=1)
    def test_metadata_missing_uses_core_label(self):
        f=self.fixture(); (f.root/'data/applications/firefox.desktop').unlink()
        rust=f.run([str(BINARY)]); legacy=f.run(['/usr/bin/python3',str(LEGACY)])
        self.assertEqual(rust[0],0,rust[2]); self.assertTrue(rust[1][0].startswith(b'Core Firefox\x00'))
        # PyGI raises on a NULL constructor; Rust implements the intended fallback.
        self.assertEqual(legacy[0],1)
    def test_localized_names(self):
        f=self.fixture(); self.env_locale(f); self.compare(f)
    def env_locale(self,f):
        f.desktop(f.root/'data/applications/firefox.desktop','Name[fr]=Navigateur français\nGenericName[fr]=Navigateur Web\n')
        f.env.pop('LC_ALL'); f.env['LANG']='fr_FR.UTF-8'; f.env['LANGUAGE']='fr'
    def test_installed_symlink_export(self):
        f=self.fixture(); entry=f.root/'data/applications/firefox.desktop'; target=f.root/'export.desktop'; entry.rename(target); entry.symlink_to(target); self.compare(f)
    def test_multiple_rows_selection_keeps_core_order(self):
        f=self.fixture(); f.desktop(f.root/'data/applications/other.desktop')
        f.config['applications'].append({'id':'other.desktop','name':'Other','origin':'installed','icon':None}); f.config['choice']='1'; self.compare(f)
    def test_stricter_invalid_catalog_rejected_before_menu(self):
        for ident in ['../escape.desktop','bad\n.desktop','.desktop']:
            f=self.fixture(); f.app['id']=ident; result=f.run([str(BINARY)])
            self.assertEqual(result[0],1); self.assertIsNone(result[1][0]); self.assertIsNone(result[1][2])
    def test_component_does_not_require_python_in_path(self):
        f=self.fixture()
        (f.root/'.local/bin/session-manager').write_text('#!/bin/sh\nif [ "$2" = session ]; then printf \'%s\\n\' \'{"sessions":[],"active_session_id":null,"revision":1}\'; else printf \'%s\\n\' \'{"applications":[{"id":"firefox.desktop","name":"Firefox","origin":"installed"}]}\'; fi\n')
        (f.root/'bin/hyprctl').write_text('#!/bin/sh\nprintf \'%s\\n\' \'[{"focused":true,"activeWorkspace":{"id":1},"specialWorkspace":{"id":0,"name":""}}]\'\n')
        (f.root/'bin/rofi').write_text('#!/bin/sh\n/bin/cat > "$HOME/rows"\nprintf \'0\\n\'\n')
        (f.root/'bin/gtk-launch').write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$HOME/launch"\n')
        f.env['PATH']=str(f.root/'bin')
        result=f.run([str(BINARY)])
        self.assertEqual(result[0],0,result[2]); self.assertEqual(result[1][2],b'firefox.desktop\n')
        self.assertEqual(BINARY.read_bytes()[:4],b'\x7fELF')

    def test_duplicate_ids_fail_closed(self):
        f=self.fixture(); f.config['applications'].append(dict(f.app)); result=f.run([str(BINARY)])
        self.assertEqual(result[0],1); self.assertIsNone(result[1][2])


if __name__=='__main__': unittest.main()
