#!/usr/bin/env python3
"""Install native contextual Obsidian + same-ID desktop override; no app launch/reload."""
import argparse,fcntl,hashlib,importlib.util,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
GRAPHICAL=Path('/usr/bin/obsidian')
SYSTEM_DESKTOP=Path('/usr/share/applications/obsidian.desktop')
spec=importlib.util.spec_from_file_location('obsidian_builder',HERE/'install_notify.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def sha(data):return hashlib.sha256(data).hexdigest()
def paths():
    home=Path.home();data=Path(os.environ.get('XDG_DATA_HOME') or home/'.local/share');state=Path(os.environ.get('XDG_STATE_HOME') or home/'.local/state')
    if not data.is_absolute() or not state.is_absolute():raise RuntimeError('XDG data/state paths must be absolute')
    return [home/'.local/bin/session-obsidian',data/'applications/obsidian.desktop'],state/'linux-setup/obsidian-upgrades'
def snapshot(p):
    builder.validate_target(p)
    if not p.exists():return {'kind':'absent'}
    s=p.stat()
    if s.st_uid!=os.getuid() or s.st_nlink!=1:raise RuntimeError('foreign-owned/hardlinked target')
    return {'kind':'file','sha256':sha(p.read_bytes()),'mode':s.st_mode&0o777}
def atomic(p,data,mode):
    builder.validate_target(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
        os.replace(name,p);fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:Path(name).unlink(missing_ok=True)
def quote_exec(path):
    # Desktop string escaping, then Exec quoting; %% is a literal percent field code.
    escaped=''.join('\\'+c if c in '\\"$`' else c for c in str(path)).replace('%','%%')
    return '"'+escaped.replace('\\','\\\\')+'"'
def desktop(source,binary):
    text=source.decode('utf-8');lines=text.splitlines();out=[];main=False;seen=False
    # Gio checks the executable before %% expansion. env keeps percent-containing
    # HOME paths in argv, not in that executable lookup. No shell is involved.
    command='/usr/bin/env -- '+quote_exec(binary)+' %U'
    for line in lines:
        if line.startswith('['):
            if main and not seen:raise RuntimeError('desktop entry has no Exec')
            main=line=='[Desktop Entry]'
        if main and line.startswith('Exec='):
            if seen:raise RuntimeError('duplicate desktop Exec')
            # Do not silently discard custom command-line flags or an unrelated handler.
            previous=line[5:].strip()
            if previous not in ['/usr/bin/obsidian %U','obsidian %U','/usr/bin/obsidian %u','obsidian %u',quote_exec(binary)+' %U',command]:
                raise RuntimeError('personal Obsidian Exec requires explicit review')
            line='Exec='+command;seen=True
        if main and line.startswith('TryExec='):line='TryExec='+str(binary).replace('\\','\\\\')
        if main and line.startswith('DBusActivatable='):line='DBusActivatable=false'
        out.append(line)
    if not seen:raise RuntimeError('missing main desktop Exec')
    return ('\n'.join(out)+'\n').encode()
def record(backup,manifest):atomic(backup/'manifest.json',json.dumps(manifest,indent=2).encode(),0o600)
def apply(targets,base):
    binary,entry=targets
    if not GRAPHICAL.is_file():raise RuntimeError('install graphical Obsidian first')
    before=[snapshot(p) for p in targets]
    source=entry if entry.exists() else SYSTEM_DESKTOP
    # Prepare/validate both assets before the first publication.
    entry_data=desktop(source.read_bytes(),binary)
    compiled=builder.build_runtime('session-obsidian','(Rust; exact registered vault)')
    payloads=[compiled.read_bytes(),entry_data];modes=[0o755,0o644]
    after=[{'kind':'file','sha256':sha(d),'mode':mode} for d,mode in zip(payloads,modes)]
    if before==after:print('Contextual Obsidian already current; no launch/reload.');return
    backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base));print(f'Private backup: {backup}',flush=True)
    manifest={'schema':1,'home':str(Path.home()),'phase':'prepared','entries':[]}
    for i,(p,old,new,data) in enumerate(zip(targets,before,after,payloads)):
        if old['kind']=='file':atomic(backup/f'before-{i}',p.read_bytes(),0o600)
        atomic(backup/f'after-{i}',data,0o600)
        manifest['entries'].append({'target':str(p),'before':old,'after':new})
    record(backup,manifest)
    # Two-file publication is NOT transactional. Record uncertainty; never retry/rollback implicitly.
    for i,(p,data,mode) in enumerate(zip(targets,payloads,modes)):
        if snapshot(p)!=before[i]:raise RuntimeError('target changed before publication')
        manifest['phase']=f'publishing-{i}';record(backup,manifest)
        atomic(p,data,mode)
        manifest['phase']=f'published-{i}';record(backup,manifest)
    manifest['phase']='complete';record(backup,manifest)
    print('Installed native session-obsidian + existing obsidian.desktop ID; no vault/app/core/shell launch or reload.')
def restore(backup,targets):
    if not backup.is_absolute() or backup.is_symlink() or not backup.is_dir():raise RuntimeError('absolute real backup required')
    builder.validate_target(backup/'manifest.json')
    m=json.loads((backup/'manifest.json').read_text())
    if m.get('schema')!=1 or m.get('home')!=str(Path.home()) or [r['target'] for r in m['entries']]!=list(map(str,targets)):raise RuntimeError('backup target mismatch')
    for i,(p,r) in enumerate(zip(targets,m['entries'])):
        if snapshot(p) not in [r['before'],r['after']]:raise RuntimeError('target edited since installation; refusing restore')
        for phase in ['before','after']:
            s=r[phase]
            if s['kind']=='file':
                payload=backup/f'{phase}-{i}';builder.validate_target(payload)
                if sha(payload.read_bytes())!=s['sha256']:raise RuntimeError('backup payload changed')
    for i,(p,r) in reversed(list(enumerate(zip(targets,m['entries'])))):
        if snapshot(p) not in [r['before'],r['after']]:raise RuntimeError('target changed during restore')
        if r['before']['kind']=='absent':p.unlink(missing_ok=True)
        else:atomic(p,(backup/f'before-{i}').read_bytes(),r['before']['mode'])
    m['phase']='restored';record(backup,m);print('Explicit Obsidian return completed; no app launch or reload.')
def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group();group.add_argument('--apply',action='store_true');group.add_argument('--restore',type=Path);args=parser.parse_args()
    if not args.apply and args.restore is None:print('Plan: native session-obsidian + same-ID user desktop override, backed up/atomic per file. No Obsidian/CLI enable/registry write/window move/reload. Use --apply.');return
    os.umask(0o077);targets,base=paths();builder.validate_target(base/'install.lock');base.mkdir(parents=True,exist_ok=True)
    with (base/'install.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.restore is not None:restore(args.restore,targets)
        else:apply(targets,base)
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:raise SystemExit(f'Obsidian integration stopped: {e}; inspect private backup/journal, no automatic rollback/replay')
