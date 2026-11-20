#!/usr/bin/env python3
"""Install OBS helpers and project-only overrides; never run OBS/camera or replace settings."""
import argparse,fcntl,hashlib,json,os,shutil,tempfile,time,tomllib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PROFILES={
 'fds':('Forge du Savoir YouTube','obs-fds','run-obs-fds','obs-fds.desktop'),
 'qmk':('hQamonky YouTube','obs-gaming','run-obs-gaming','obs-gaming.desktop'),
}
def safe(path):
    if not path.is_absolute() or any(p.is_symlink() for p in [path,*path.parents]):raise RuntimeError(f'unsafe/symlinked path: {path}')
    if path.exists() and not path.is_file():raise RuntimeError(f'nonregular target: {path}')
def stamp(p):
    safe(p)
    if not p.exists():return None
    s=p.stat()
    if s.st_uid!=os.getuid() or s.st_nlink!=1:raise RuntimeError(f'foreign-owned/hardlinked target: {p}')
    return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':s.st_mode&0o777}
def atomic(p,data,mode):
    safe(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
        os.replace(name,p)
        sync_directory(p.parent)
    finally:Path(name).unlink(missing_ok=True)
def sync_directory(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def quote(p):
    value=''.join('\\'+c if c in '\\"$`' else c for c in str(p)).replace('%','%%')
    return '"'+value.replace('\\','\\\\')+'"'
def project_source(home):
    if os.environ.get('SESSION_MANAGER_PROJECT_SOURCE'):return Path(os.environ['SESSION_MANAGER_PROJECT_SOURCE'])
    config=Path(os.environ.get('XDG_CONFIG_HOME') or home/'.config')
    if not config.is_absolute():raise RuntimeError('XDG_CONFIG_HOME must be absolute')
    path=config/'session-manager/config-v2.toml'
    if path.exists():return Path(tomllib.loads(path.read_text())['project_source'])
    return home/'Obsidian/Agora/2 Projects'
def plan(home,source,profiles,desktop_only):
    if not source.is_absolute() or any(p.is_symlink() for p in [source,*source.parents]):raise RuntimeError('project source must be an absolute real directory')
    data=Path(os.environ.get('XDG_DATA_HOME') or home/'.local/share')
    if not data.is_absolute():raise RuntimeError('XDG_DATA_HOME must be absolute')
    ops=[]
    for key in profiles:
        project_name,command,directory,template=PROFILES[key]
        launcher=home/'.local/bin'/command
        if not desktop_only:
            code=(ROOT/'scripts'/directory/(directory+'.sh')).read_bytes()
            ops.append((launcher,code,0o755,stamp(launcher)))
        elif stamp(launcher) is None or not os.access(launcher,os.X_OK):raise RuntimeError(f'install the OBS helper first: {launcher}')
        project=source/project_name
        if not project.exists():
            print(f'Skipping absent project: {project_name}; no project directory or global deletion.')
            continue
        if not project.is_dir() or project.is_symlink():raise RuntimeError('project must be a real directory')
        original=(ROOT/'scripts'/directory/template).read_text()
        # Preserve desktop metadata, use literal absolute argv without shell expansion.
        lines=original.splitlines()
        entry='\n'.join(('Exec=/usr/bin/env -- '+quote(launcher)) if s.startswith('Exec=') else
                       'Comment=Launch OBS with the Forge du Savoir scene collection' if key=='fds' and s.startswith('Comment=') else s
                       for s in lines)+'\n'
        dest=project/'.session-manager/apps/com.obsproject.Studio.desktop';old=stamp(dest)
        if old is not None and dest.read_bytes()!=entry.encode():raise RuntimeError(f'preserving personal project override; review before replacing: {dest}')
        ops.append((dest,entry.encode(),0o644,old))
        legacy_names=[command+'.desktop']+(['run-obs-gaming.desktop'] if key=='qmk' else [])
        expected=original.replace('__HOME_DIR__',str(home)).encode()
        for name in legacy_names:
            legacy=data/'applications'/name
            legacy_before=stamp(legacy)
            if legacy_before is not None:
                if legacy_before['sha256']!=hashlib.sha256(expected).hexdigest():raise RuntimeError(f'personal legacy desktop requires review: {legacy}')
                ops.append((legacy,None,None,legacy_before))
    return [(p,d,m,b) for p,d,m,b in ops if d is None or b!={'sha256':hashlib.sha256(d).hexdigest(),'mode':m}]
def apply(ops,base):
    if not ops:print('OBS project launchers already current; no changes.');return
    backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base));print(f'Private OBS launcher backup: {backup}',flush=True)
    rows=[]
    for i,(p,data,mode,before) in enumerate(ops):
        if stamp(p)!=before:raise RuntimeError('target changed before backup')
        if before is not None:
            shutil.copy2(p,backup/f'before-{i}');os.chmod(backup/f'before-{i}',0o600)
            if hashlib.sha256((backup/f'before-{i}').read_bytes()).hexdigest()!=before['sha256']:raise RuntimeError('target changed during backup')
        rows.append({'target':str(p),'before':before,'after':None if data is None else {'sha256':hashlib.sha256(data).hexdigest(),'mode':mode}})
    manifest={'schema':1,'phase':'prepared','operations':rows}
    def journal():atomic(backup/'manifest.json',json.dumps(manifest,indent=2).encode(),0o600)
    journal()
    # All project writes precede their corresponding legacy deletions.
    # Not a multi-file transaction: retain the journal/backups on any uncertainty.
    for i,(p,data,mode,before) in enumerate(ops):
        if stamp(p)!=before:raise RuntimeError('target changed before publication')
        manifest['phase']=f'publishing-{i}';journal()
        if data is None:p.unlink();sync_directory(p.parent)
        else:atomic(p,data,mode)
        manifest['phase']=f'published-{i}';journal()
    manifest['phase']='complete';journal()
    print('OBS project overrides installed; no OBS/camera/settings/session/shell action.')
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--desktop-only',action='store_true',help='keep installed helper scripts byte-for-byte');parser.add_argument('--only',choices=list(PROFILES));parser.add_argument('--project-source',type=Path);args=parser.parse_args()
    if not args.apply:print('Plan: install obs-fds/obs-gaming and same-ID OBS overrides in existing FDS/QMK projects; back up/remove only exact legacy global entries after project publication. --desktop-only preserves current helpers. Use --apply.');return
    os.umask(0o077);home=Path.home();base=Path(os.environ.get('XDG_STATE_HOME') or home/'.local/state')/'linux-setup/obs-project-launchers'
    safe(base/'install.lock');base.mkdir(parents=True,exist_ok=True)
    with (base/'install.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        ops=plan(home,args.project_source or project_source(home),[args.only] if args.only else list(PROFILES),args.desktop_only)
        apply(ops,base)
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,TypeError) as e:raise SystemExit(f'OBS launcher installation stopped: {e}; inspect private backup/journal, no automatic rollback or replay')
