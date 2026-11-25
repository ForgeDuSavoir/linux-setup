#!/usr/bin/env python3
"""Real launcher, private core/native and fake browser; no personal profiles/windows."""
import importlib.util,json,tempfile,time
from pathlib import Path
p=Path(__file__).with_name('test-session-app-launcher.py');s=importlib.util.spec_from_file_location('fixture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for mode in ['neutral','project-firefox','project-youtube','ambiguous','missing','mismatch']:
 with tempfile.TemporaryDirectory(prefix='youtube-shortcut-') as d:
  h=Path(d);f=m.Fixture(h);f.env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+str(h/'no-bus');f.env['XDG_CACHE_HOME']=str(h/'cache')
  if mode.startswith('project') or mode=='ambiguous':f.project_app()
  fake=h/'bin/fake-browser';fake.write_text('#!/usr/bin/python3\nimport sys,os,json\nfrom pathlib import Path\n(Path(os.environ["HOME"])/"youtube").write_text(json.dumps(sys.argv[1:]))\n');fake.chmod(0o700)
  entry=f.project/'.session-manager/apps/firefox.desktop' if f.app['origin']=='project' else h/'data/applications/firefox.desktop'
  entry.write_text('[Desktop Entry]\nType=Application\nName=Contextual Browser\nExec="'+str(fake)+'" --profile "literal profile" %u\n')
  if mode in ['project-youtube','ambiguous']:
   for name in (['youtube-fds.desktop'] if mode=='project-youtube' else ['youtube-fds.desktop','youtube-qmk.desktop']):
    f.config['applications'].append({'id':name,'name':'YouTube','origin':'project'})
    (f.project/'.session-manager/apps'/name).write_text('[Desktop Entry]\nType=Application\nName=YouTube\nExec=/usr/bin/true\n')
  if mode=='missing':f.config['applications']=[]
  if mode=='mismatch':f.config['owner']='absent'
  code,outputs,err=f.run([str(m.BINARY)],['--youtube'])
  assert (code==0)==(mode in ['neutral','project-firefox','project-youtube']),(mode,err)
  assert outputs[0] is None,'no Rofi'
  if mode in ['neutral','project-firefox']:
   end=time.monotonic()+3
   while not (h/'youtube').exists() and time.monotonic()<end:time.sleep(.01)
   assert json.loads((h/'youtube').read_text())==['--profile','literal profile','https://www.youtube.com/']
  if mode=='project-youtube':assert 'youtube-fds.desktop' in outputs[2].decode()
  assert not (h/'state/session-app-launcher').exists() and not list(h.rglob('app-usage.json')),'no history IO'
print('YouTube: private real Gio URI/profile preservation, project override, ambiguity/missing/mismatch refusal, no menu/history passed.')
