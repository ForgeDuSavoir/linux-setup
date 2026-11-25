#!/usr/bin/env python3
"""No real Pi process/config: targeted merge in private HOME and all XDG roots."""
import json,subprocess,tempfile
from pathlib import Path
installer=Path(__file__).with_name('install_keybindings.py')
with tempfile.TemporaryDirectory(prefix='pi-binding-install-') as d:
 h=Path(d);p=h/'.pi/agent/keybindings.json';p.parent.mkdir(parents=True)
 old={'app.tools.expand':'alt+o','personal.action':'f5','tui.editor.deleteWordBackward':'alt+w'};p.write_text(json.dumps(old))
 env={'HOME':d,'PATH':'/usr/bin:/bin',**{'XDG_'+key:str(h/key.lower()) for key in ['STATE_HOME','CONFIG_HOME','DATA_HOME','CACHE_HOME','RUNTIME_DIR']}}
 for _ in range(2):subprocess.run(['python3',str(installer),'--apply'],env=env,check=True)
 a=json.loads(p.read_text());assert a['app.tools.expand']=='alt+o' and a['personal.action']=='f5'
 assert a['tui.editor.deleteWordBackward']==['alt+w','ctrl+w','alt+backspace','ctrl+backspace']
 backups=list((h/'state_home/linux-setup/pi-keybinding-upgrades').iterdir());assert len(backups)==1
 assert json.loads((backups[0]/'keybindings.json').read_text())==old
 p.unlink();target=h/'protected';target.write_text('{}');p.symlink_to(target)
 assert subprocess.run(['python3',str(installer),'--apply'],env=env,capture_output=True).returncode!=0
 assert target.read_text()=='{}'
print('Private Pi binding merge/personal aliases/backup/idempotence/symlink guards passed.')
