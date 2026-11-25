#!/usr/bin/env python3
"""Merge packaged Pi bindings without replacing unrelated user customizations."""
import argparse,json,os,tempfile,time
from pathlib import Path
from install_external_editor import content,atomic
SOURCE=Path(__file__).with_name('keybindings.json')
WORDS={'tui.editor.deleteWordBackward','tui.editor.deleteWordForward'}
def apply():
 home=Path.home();target=home/'.pi/agent/keybindings.json';old=content(target)
 current=json.loads(old) if old is not None else {}
 if not isinstance(current,dict):raise RuntimeError('keybindings must be an object')
 result=dict(current)
 for action,default in json.loads(SOURCE.read_text()).items():
  if action in WORDS:
   existing=current.get(action,[])
   if isinstance(existing,str):existing=[existing]
   if not isinstance(existing,list) or not all(isinstance(k,str) for k in existing):raise RuntimeError('invalid word binding')
   result[action]=list(dict.fromkeys([*existing,*default]))
  else:result.setdefault(action,default)
 if result==current:print('Pi keybindings already configured.');return
 base=Path(os.environ.get('XDG_STATE_HOME') or home/'.local/state')/'linux-setup/pi-keybinding-upgrades'
 if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup root')
 base.mkdir(parents=True,exist_ok=True);backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base));backup.chmod(0o700)
 if old is not None:atomic(backup/'keybindings.json',old,0o600)
 if content(target)!=old:raise RuntimeError('keybindings changed; no overwrite')
 atomic(target,(json.dumps(result,indent=2)+'\n').encode(),0o600)
 print('Private keybinding backup:',backup);print('Pi bindings installed; run /reload in Pi. No application launched.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 if args.apply:apply()
 else:print('Plan: merge Pi bindings, preserving personal aliases; use --apply.')
