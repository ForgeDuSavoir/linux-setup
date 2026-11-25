#!/usr/bin/env python3
"""Private bridge/installer test: fake blocking editor, no GUI or Pi conversation."""
import json,os,subprocess,tempfile,time
from pathlib import Path
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='pi-mousepad-') as d:
 h=Path(d);b=h/'bin';b.mkdir();run=h/'run';run.mkdir(mode=0o700)
 env={'HOME':d,'PATH':str(b)+':/usr/bin:/bin','XDG_CONFIG_HOME':str(h/'config'),'XDG_DATA_HOME':str(h/'data'),'XDG_DATA_DIRS':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'XDG_CACHE_HOME':str(h/'cache'),'XDG_RUNTIME_DIR':str(run),'DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(h/'no-bus'),'EDITOR':'nvim','VISUAL':'nvim'}
 settings=h/'.pi/agent/settings.json';settings.parent.mkdir(parents=True);original={'externalEditor':'old','defaultModel':'keep','terminal':{'clearOnShrink':True}};settings.write_text(json.dumps(original))
 helper=h/'.local/bin/pi-external-editor';helper.parent.mkdir(parents=True);helper.write_text('old helper');helper.chmod(0o755)
 subprocess.run(['python3',str(here/'install_external_editor.py'),'--apply'],env=env,check=True)
 assert json.loads(settings.read_text())=={**original,'externalEditor':'pi-external-editor'}
 assert helper.read_bytes()==(here/'launch_external_editor.sh').read_bytes()
 before=settings.read_bytes();subprocess.run(['python3',str(here/'install_external_editor.py'),'--apply'],env=env,check=True);assert settings.read_bytes()==before
 fake=b/'mousepad';fake.write_text('''#!/usr/bin/python3
import os,sys,time,json
from pathlib import Path
h=Path(os.environ['HOME']);assert sys.argv[1:4]==['--disable-server','--opening-mode=window','--']
(h/'args').write_text(json.dumps(sys.argv[4:]));p=Path(sys.argv[4]);p.write_text('edited prompt')
(h/'ready').touch()
while not (h/'close').exists():time.sleep(.01)
sys.exit(int(os.environ.get('FAKE_EXIT','0')))
''');fake.chmod(0o755)
 prompt=h/'literal ; $(no-shell).md';prompt.write_text('original')
 p=subprocess.Popen([str(helper),str(prompt)],env=env)
 try:
  deadline=time.monotonic()+5
  while not (h/'ready').exists():
   assert p.poll() is None;assert time.monotonic()<deadline;time.sleep(.01)
  assert p.poll() is None,'bridge must wait while editor is open'
  assert json.loads((h/'args').read_text())==[str(prompt)]
  (h/'close').touch();assert p.wait(timeout=5)==0;assert prompt.read_text()=='edited prompt'
 finally:
  if p.poll() is None:p.kill();p.wait()
 assert subprocess.run([str(helper),str(prompt)],env={**env,'FAKE_EXIT':'9'}).returncode==9
 assert subprocess.run([str(helper)],env=env,capture_output=True).returncode==2
 backups=list((h/'state/linux-setup/pi-editor-upgrades').iterdir());assert len(backups)==1
 assert json.loads((backups[0]/'settings.json').read_text())==original
 helper.unlink();other=h/'protected';other.write_text('keep');helper.symlink_to(other)
 assert subprocess.run(['python3',str(here/'install_external_editor.py'),'--apply'],env=env,capture_output=True).returncode!=0
 assert other.read_text()=='keep'
print('Pi Mousepad bridge: private settings merge/backup/idempotence, stale nvim env ignored, literal argv, wait until close, edited text, error propagation and symlink guards passed; no real editor/Pi launched.')
