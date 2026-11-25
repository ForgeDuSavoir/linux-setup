#!/usr/bin/env python3
"""Targeted Mousepad bridge + merged user Pi preference; no Pi/editor launch."""
import argparse,json,os,stat,tempfile,time
from pathlib import Path
SOURCE=Path(__file__).with_name('launch_external_editor.sh')
def validate(p):
 if not p.is_absolute():raise RuntimeError('absolute path required')
 for ancestor in [p,*p.parents]:
  if ancestor.is_symlink():raise RuntimeError('symlinked target/ancestor refused: '+str(ancestor))
 if p.exists() and (not p.is_file() or p.stat().st_uid!=os.getuid()):raise RuntimeError('invalid target: '+str(p))
def content(p):
 validate(p)
 if not p.exists():return None
 if p.stat().st_size>4*1024*1024:raise RuntimeError('oversized settings')
 return p.read_bytes()
def atomic(p,data,mode):
 p.parent.mkdir(parents=True,exist_ok=True);validate(p)
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode)
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def apply():
 home=Path.home();helper=home/'.local/bin/pi-external-editor';settings=home/'.pi/agent/settings.json'
 old={p:content(p) for p in [helper,settings]}
 value=json.loads(old[settings]) if old[settings] is not None else {}
 if not isinstance(value,dict):raise RuntimeError('Pi settings must be an object')
 value['externalEditor']='pi-external-editor'
 new={helper:SOURCE.read_bytes(),settings:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()}
 if old==new:print('Mousepad Pi editor already configured.');return
 base=Path(os.environ.get('XDG_STATE_HOME') or home/'.local/state')/'linux-setup/pi-editor-upgrades'
 if not base.is_absolute() or any(p.is_symlink() for p in [base,*base.parents]):raise RuntimeError('unsafe backup root')
 base.mkdir(parents=True,exist_ok=True);backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base));backup.chmod(0o700)
 manifest={'phase':'prepared','targets':{str(p):old[p] is not None for p in old}}
 def journal():atomic(backup/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode(),0o600)
 for p,data in old.items():
  if data is not None:atomic(backup/p.name,data,0o600)
 journal()
 for p,data in new.items():
  if content(p)!=old[p]:raise RuntimeError('target changed; inspect backup, no rollback')
  if data!=old[p]:atomic(p,data,0o755 if p==helper else 0o600)
  manifest['phase']='published:'+p.name;journal()
 manifest['phase']='complete';journal();print('Private Pi editor backup:',backup)
 print('Mousepad external editor configured; no Pi/editor/terminal/reload invoked.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 if args.apply:apply()
 else:print('Plan: install blocking Mousepad bridge and merge only externalEditor in user Pi settings; use --apply.')
