#!/usr/bin/env python3
"""Real XDG/Fish settings in private roots; no editor or GUI invocation."""
import os,subprocess,tempfile
from pathlib import Path
script=Path(__file__).with_name('configure_default_applications.sh').resolve()
with tempfile.TemporaryDirectory(prefix='mousepad-default-') as d:
 h=Path(d);config=h/'config';config.mkdir();b=h/'bin';b.mkdir()
 (b/'mousepad').write_text('#!/bin/sh\nexit 99\n');(b/'mousepad').chmod(0o700)
 env={'HOME':d,'PATH':str(b)+':/usr/bin:/bin','XDG_CONFIG_HOME':str(config),'XDG_DATA_HOME':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'XDG_CACHE_HOME':str(h/'cache'),'XDG_RUNTIME_DIR':str(h/'run'),'XDG_DATA_DIRS':'/usr/share','XDG_CURRENT_DESKTOP':'','DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(h/'no-bus')}
 (config/'mimeapps.list').write_text('[Default Applications]\ntext/plain=agora-neovim.desktop\ntext/markdown=agora-neovim.desktop\ninode/directory=thunar.desktop\nimage/png=org.gnome.Loupe.desktop\n')
 def cmd(*a):return subprocess.check_output(a,env=env,text=True).strip()
 before=(config/'mimeapps.list').read_bytes()
 for _ in range(2):
  subprocess.run(['bash',str(script),'--editor-only'],env=env,check=True,stdout=subprocess.PIPE,text=True)
  for mime in ['text/plain','text/markdown']:assert cmd('xdg-mime','query','default',mime)=='org.xfce.mousepad.desktop'
  assert cmd('fish','-c','printf "%s %s" $EDITOR $VISUAL')=='mousepad mousepad'
  assert cmd('xdg-mime','query','default','inode/directory')=='thunar.desktop'
  assert cmd('xdg-mime','query','default','image/png')=='org.gnome.Loupe.desktop'
 backups=sorted((h/'state/linux-setup/default-editor-upgrades').iterdir())
 assert len(backups)==2 and any((p/'mimeapps.list').read_bytes()==before for p in backups)
 (config/'mimeapps.list').unlink();target=h/'untouched';target.write_text('keep');(config/'mimeapps.list').symlink_to(target)
 assert subprocess.run(['bash',str(script),'--editor-only'],env=env,capture_output=True).returncode!=0
 assert target.read_text()=='keep'
print('Private real XDG/Fish: Mousepad plain/Markdown/EDITOR/VISUAL, repeat install, backup, other defaults and symlink refusal passed; no GUI launched.')
