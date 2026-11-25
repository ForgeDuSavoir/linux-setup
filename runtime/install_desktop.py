#!/usr/bin/env python3
"""R8 desktop cohort installer. Never initialize a login or mutate logical sessions."""
import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
SETUP=HERE.parent
BASE_BINS=('workspace-controller','session-desktop','session-startup','agora-desktop-admin')
BINS=(*BASE_BINS,'session-files')
spec=importlib.util.spec_from_file_location('desktop_runtime_builder',HERE/'install_notify.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def run(args,input=None):
    result=subprocess.run([str(a) for a in args],input=input,capture_output=True,text=True,timeout=35)
    if result.returncode:raise RuntimeError(f'{args[0]} failed: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout

def sha(data):return hashlib.sha256(data).hexdigest()
def validate(path,link=False):
    if not path.is_absolute():raise RuntimeError('absolute paths required')
    for p in path.parents:
        if p.is_symlink():raise RuntimeError(f'symlinked ancestor: {p}')
    if path.is_symlink():
        if not link:raise RuntimeError(f'symlinked target: {path}')
    elif path.exists():
        m=path.stat()
        if m.st_uid!=os.getuid() or not (stat.S_ISREG(m.st_mode) or stat.S_ISDIR(m.st_mode)):raise RuntimeError(f'foreign/nonregular target: {path}')

def atomic_bytes(path,data,mode=0o600):
    validate(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:Path(name).unlink(missing_ok=True)

def write_json(path,value):atomic_bytes(path,(json.dumps(value)+'\n').encode())

def root():return Path.home()/'.local/libexec/agora-desktop'
def current():return root()/'current'
def runtime():return Path(os.environ.get('XDG_RUNTIME_DIR') or '/tmp')/'hyprland'

def files():
    result={}
    for folder,prefix in [('configs/hypr/files','.config/hypr'),('configs/quickshell/files','.config/quickshell')]:
        for path in (SETUP/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.name=='workspace-columns.py':continue
            if path.is_symlink():raise RuntimeError('linked source asset')
            relative=str(Path(prefix)/path.relative_to(SETUP/folder))
            result[relative]=(path.read_bytes(),0o755 if 'Scripts' in path.parts else 0o644)
    return result

def stage():
    validate(root())
    env={**os.environ,'CARGO_TARGET_DIR':str(HERE/'target')}
    subprocess.run(['cargo','+1.96.1','build','--manifest-path',str(HERE/'Cargo.toml'),'--release','--offline','--locked',*[x for name in BINS for x in ['--bin',name]]],env=env,check=True,timeout=180)
    assets=files()
    for name in BINS:
        p=HERE/'target/release'/name
        if p.is_symlink() or p.read_bytes()[:4]!=b'\x7fELF':raise RuntimeError('expected ELF cohort')
        version=run([p,'--version']).strip()
        if not version.startswith(name+' 0.1.0 '):raise RuntimeError('unexpected runtime version')
        assets[name]=(p.read_bytes(),0o755)
    caps=json.loads(run([HERE/'target/release/agora-desktop-admin','capabilities']))
    if caps.get('version')!=1 or caps.get('core_protocol')!=3 or caps.get('desktop_schema')!=3:raise RuntimeError('incompatible pure admin ABI')
    entries={n:{'sha256':sha(data),'mode':mode} for n,(data,mode) in assets.items()}
    identity=sha(json.dumps(entries,sort_keys=True).encode())[:24]
    directory=root()/'generations'/identity
    validate(directory)
    if directory.exists():verify_generation(directory);return directory
    directory.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix='.stage-',dir=directory.parent))
    try:
        for name,(data,mode) in assets.items():atomic_bytes(tmp/name,data,mode)
        write_json(tmp/'generation.json',{'version':1,'files':entries,'capabilities':caps})
        os.rename(tmp,directory)
    finally:
        if tmp.exists():shutil.rmtree(tmp)
    verify_generation(directory)
    return directory

def verify_generation(directory):
    validate(directory)
    if directory.parent!=root()/'generations':raise RuntimeError('generation outside managed root')
    m=directory/'generation.json';validate(m)
    manifest=json.loads(m.read_text())
    if manifest.get('version')!=1 or not set(BASE_BINS)<=set(manifest.get('files',{})):raise RuntimeError('invalid generation')
    for name,record in manifest['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise RuntimeError('unsafe generation member')
        p=directory/name;validate(p)
        if sha(p.read_bytes())!=record['sha256'] or stat.S_IMODE(p.stat().st_mode)!=record['mode']:raise RuntimeError('generation modified')
    return manifest

def managed_current():
    p=current();validate(p,link=True)
    if not p.is_symlink():
        if p.exists():raise RuntimeError('unmanaged current pointer')
        return None
    target=Path(os.readlink(p))
    verify_generation(target)
    return str(target)

def public_link(name):return str(current()/name)
def snapshot_path(path):
    validate(path,link=True)
    if path.is_symlink():return {'kind':'link','target':os.readlink(path)}
    if not path.exists():return {'kind':'absent'}
    if not path.is_file():raise RuntimeError('nonregular installation target')
    return {'kind':'file','sha256':sha(path.read_bytes()),'mode':stat.S_IMODE(path.stat().st_mode)}

def symlink(path,target):
    validate(path,link=True);path.parent.mkdir(parents=True,exist_ok=True)
    name=path.parent/(path.name+'.link-'+next(tempfile._get_candidate_names()))
    try:os.symlink(target,name);os.replace(name,path)
    finally:name.unlink(missing_ok=True)
    fd=os.open(path.parent,os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def shell_pid(output,config):
    matches=[]
    for block in output.split('Instance ')[1:]:
        fields=dict(line.strip().split(': ',1) for line in block.splitlines() if ': ' in line)
        if fields.get('Config path')==str(config):matches.append(int(fields['Process ID']))
    if len(matches)>1:raise RuntimeError('multiple matching Quickshell instances')
    return matches[0] if matches else None

def desktop_snapshot():
    clients=json.loads(run(['hyprctl','-j','clients']))
    monitors=json.loads(run(['hyprctl','-j','monitors']))
    return {'clients':sorted([{'address':c['address'],'workspace':c['workspace']} for c in clients],key=lambda c:c['address']),
            'monitors':[{'id':m.get('id'),'activeWorkspace':m.get('activeWorkspace'),'specialWorkspace':m.get('specialWorkspace'),'focused':m.get('focused')} for m in monitors]}

def core_snapshot():return json.loads(run([Path.home()/'.local/bin/session-manager','--json','session','list']))
def admin(generation,op,data):return json.loads(run([generation/'agora-desktop-admin',op],json.dumps(data)))
def read_runtime(name):
    p=runtime()/name;validate(p)
    if not p.exists():return None
    m=p.stat()
    if not p.is_file() or m.st_nlink!=1:raise RuntimeError('unsafe runtime file')
    return p.read_bytes()

@contextlib.contextmanager
def locked():
    p=runtime();validate(p);p.mkdir(parents=True,exist_ok=True)
    name=p/'workspace-columns.lock';validate(name)
    fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        m=os.fstat(fd)
        if not stat.S_ISREG(m.st_mode) or m.st_uid!=os.getuid() or m.st_nlink!=1:raise RuntimeError('unsafe lock')
        fcntl.flock(fd,fcntl.LOCK_EX)
        yield
    finally:os.close(fd)

def guard(offline,allow,reduced):
    run(['bash','-c','source "$1"; session_manager_require_v3','bash',SETUP/'configs/session-manager/require_protocol_v3.sh'])
    if not offline and not reduced and not allow:raise RuntimeError('full apply requires --allow-notification-history-reset (separate explicit approval)')
    if reduced and not managed_current():raise RuntimeError('first activation requires full cohort/QML approval, not movement/startup-only')
    if offline:
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):raise RuntimeError('offline install refused in a known login')
        if shutil.which('hyprctl') and json.loads(run(['hyprctl','-j','instances'])):raise RuntimeError('offline install refused: compositor exists')
        if shutil.which('quickshell'):
            listing=run(['quickshell','list','--all']).strip()
            if listing not in ['', 'No running instances.']:raise RuntimeError('offline install refused: shell exists or listing is ambiguous')
    elif not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):raise RuntimeError('known current login signature required')

def stop_shell(offline,reduced):
    if offline or reduced:return None
    pid=shell_pid(run(['quickshell','list','--all']),Path.home()/'.config/quickshell/shell.qml')
    if pid:
        exe=shutil.which('quickshell');proc=Path(f'/proc/{pid}')
        if not exe or not (proc/'exe').exists() or not os.path.samefile(proc/'exe',exe) or proc.stat().st_uid!=os.getuid():raise RuntimeError('known shell executable/UID mismatch')
        run(['quickshell','kill','--pid',pid])
        for _ in range(50):
            if not proc.exists() or (proc/'stat').read_text().split(') ',1)[1].split()[0]=='Z':break
            time.sleep(.1)
        else:raise RuntimeError('known shell did not exit')
    return pid

def snapshots(offline):
    return None if offline else {'desktop':desktop_snapshot(),'core':core_snapshot()}
def defer(generation,offline):
    if offline:return
    previous=read_runtime('session-startup.json')
    result=admin(generation,'defer-marker',{'instance':os.environ['HYPRLAND_INSTANCE_SIGNATURE'],'previous':json.loads(previous) if previous is not None else None})
    if result['changed']:write_json(runtime()/'session-startup.json',result['marker'])

def validate_state(generation):
    raw=read_runtime('workspace-columns.json')
    if raw is not None:
        state=json.loads(raw)
        if state.get('version')!=3:raise RuntimeError('R8 requires already validated v3 metadata; no implicit schema migration')
        admin(generation,'validate-state',{'state':state})
    return raw

def backup_base():
    base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'linux-setup/desktop-cohort'
    validate(base);base.mkdir(parents=True,exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=base))

def journal(backup,manifest,phase):
    manifest['phase']=phase;write_json(backup/'manifest.json',manifest)

def target_plan(gm,offline,reduced):
    if reduced not in [None,'movement','startup','visuals']:raise RuntimeError('unknown cohort mode')
    selected=[n for n in gm['files'] if n not in BINS]
    if not offline:
        critical=['.config/hypr/hyprland.lua','.config/hypr/keybinds.lua','.config/hypr/startup.lua','.config/hypr/Scripts/scratchpad.sh']
        selected=[n for n in selected if n.startswith('.config/quickshell/') or n in critical]
    if reduced=='movement':selected=[n for n in selected if n in ['.config/hypr/keybinds.lua','.config/hypr/hyprland.lua','.config/hypr/Scripts/scratchpad.sh']]
    if reduced=='startup':selected=['.config/hypr/startup.lua']
    if reduced=='visuals':selected=['.config/hypr/visuals.lua']
    targets={str(Path('.local/bin')/n):{'kind':'link','target':public_link(n)} for n in BINS if n in gm['files']}
    targets.update({n:{'kind':'file',**gm['files'][n]} for n in selected})
    return targets

def apply(offline=False,allow=False,reduced=None):
    guard(offline,allow,reduced)
    generation=stage();gm=verify_generation(generation);old_current=managed_current()
    home=Path.home()
    old_bins=verify_generation(Path(old_current))['files'] if old_current else {}
    targets=target_plan(gm,offline,reduced)
    for name in BINS:
        p=home/'.local/bin'/name;s=snapshot_path(p)
        if s['kind']=='link' and s['target']!=public_link(name):raise RuntimeError('unmanaged public command symlink')
        if old_current and s!={'kind':'link','target':public_link(name)}:
            if name not in old_bins and s=={'kind':'absent'}:continue # Explicit additive command expansion.
            raise RuntimeError('active cohort entry point was modified')
    if reduced:
        qml=home/'.config/quickshell/shell.qml';validate(qml)
        if 'workspace-columns.py' in qml.read_text() or 'workspace-controller' not in qml.read_text():raise RuntimeError('reduced install requires native QML already activated')
    with locked():
        state=validate_state(generation);before=snapshots(offline)
        # Validate/propose marker while installer owns the lock: pure subprocess, no nested flock.
        previous=read_runtime('session-startup.json')
        if not offline:admin(generation,'defer-marker',{'instance':os.environ['HYPRLAND_INSTANCE_SIGNATURE'],'previous':json.loads(previous) if previous is not None else None})
        initial={name:snapshot_path(home/name) for name in targets}
        if any(record['kind']=='link' for name,record in initial.items() if name not in {str(Path('.local/bin')/n) for n in BINS}):raise RuntimeError('linked config target; inspect explicitly before cohort installation')
        if old_current==str(generation) and initial==targets:
            print('Desktop cohort already current; no files, marker or shell changed.');return
        backup=backup_base()
        manifest={'version':1,'phase':'prepared','shell_was_running':bool(shell_pid(run(['quickshell','list','--all']),home/'.config/quickshell/shell.qml')) if not offline and not reduced else False,'current_before':old_current,'current_after':str(generation),'before':initial,'after':targets,'reduced':reduced,'offline':offline}
        if state is not None:atomic_bytes(backup/'workspace-state-before.json',state)
        if previous is not None:atomic_bytes(backup/'startup-marker-before.json',previous)
        if before is not None:write_json(backup/'before.json',before)
        for name,record in initial.items():
            if record['kind']=='file':atomic_bytes(backup/'files'/name,(home/name).read_bytes(),record['mode'])
        journal(backup,manifest,'prepared');print(f'Private cohort backup: {backup}',flush=True)
        # No automatic rollback after any uncertain external response or publication.
        pid=stop_shell(offline,reduced);journal(backup,manifest,'shell-stopped')
        defer(generation,offline)
        # Recheck snapshots and originals immediately before first publication.
        if snapshots(offline)!=before or read_runtime('workspace-columns.json')!=state:raise RuntimeError('desktop/core/metadata changed before publication')
        if managed_current()!=old_current or {n:snapshot_path(home/n) for n in targets}!=initial:raise RuntimeError('installation target changed before publication')
        symlink(current(),str(generation));journal(backup,manifest,'current-published')
        for name,record in targets.items():
            path=home/name
            if record==snapshot_path(path):continue
            if record['kind']=='link':symlink(path,record['target'])
            else:
                # atomic_bytes never follows/replaces an unapproved symlink.
                atomic_bytes(path,(generation/name).read_bytes(),record['mode'])
        journal(backup,manifest,'files-published')
        if not offline:run(['hyprctl','reload'])
        if snapshots(offline)!=before or read_runtime('workspace-columns.json')!=state:raise RuntimeError('desktop/core/metadata changed; inspect backup, no repair')
        if before is not None:write_json(backup/'after.json',before)
        journal(backup,manifest,'verified')
    if pid:
        run(['quickshell','--daemonize','-p',home/'.config/quickshell'])
    journal(backup,manifest,'complete')
    print('Native cohort installed; no logical-session/native-window mutation or startup initializer executed.')

def restore(backup,offline=False,allow=False):
    validate(backup)
    m=backup.stat()
    if m.st_uid!=os.getuid() or stat.S_IMODE(m.st_mode)&0o077:raise RuntimeError('owned private backup required')
    path=backup/'manifest.json';validate(path);manifest=json.loads(path.read_text())
    if manifest.get('version')!=1:raise RuntimeError('unknown backup protocol')
    reduced=manifest.get('reduced')
    guard(offline,allow,reduced)
    generation=Path(manifest['current_after']);gm=verify_generation(generation)
    if manifest.get('after')!=target_plan(gm,manifest.get('offline',False),reduced) or set(manifest.get('before',{}))!=set(manifest['after']):raise RuntimeError('backup target set is not the recorded managed cohort')
    for name,record in manifest['before'].items():
        if record.get('kind')=='link' and record.get('target')!=public_link(Path(name).name):raise RuntimeError('unsafe prior symlink in backup')
        if record.get('kind')=='file' and (type(record.get('mode')) is not int or not 0<=record['mode']<=0o777):raise RuntimeError('unsafe prior permissions')
    if manifest['current_before']:verify_generation(Path(manifest['current_before']))
    home=Path.home()
    with locked():
        state=validate_state(generation);before=snapshots(offline)
        if managed_current() not in [manifest['current_before'],manifest['current_after']]:raise RuntimeError('a later cohort is active; restore one explicit step at a time')
        for name,old in manifest['before'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:raise RuntimeError('unsafe backup member')
            now=snapshot_path(home/name)
            if now not in [old,manifest['after'][name]]:raise RuntimeError('foreign later target edit; refusing restore')
            if old['kind']=='file':
                p=backup/'files'/name;validate(p)
                if sha(p.read_bytes())!=old['sha256']:raise RuntimeError('corrupt backup')
        if manifest.get('phase')=='restored' and managed_current()==manifest['current_before'] and all(snapshot_path(home/n)==r for n,r in manifest['before'].items()):
            print('Cohort already restored; no shell/files/marker change.');return
        pid=stop_shell(offline,reduced)
        defer(generation,offline) # Never restore old logical metadata/marker or reset this login.
        journal(backup,manifest,'restoring')
        for name,old in manifest['before'].items():
            p=home/name
            if old==snapshot_path(p):continue
            if old['kind']=='absent':p.unlink(missing_ok=True)
            elif old['kind']=='link':symlink(p,old['target'])
            else:
                # Remove only our exact managed ABI symlink, never follow it.
                if p.is_symlink():p.unlink()
                atomic_bytes(p,(backup/'files'/name).read_bytes(),old['mode'])
        if manifest['current_before']:symlink(current(),manifest['current_before'])
        else:current().unlink(missing_ok=True)
        if not offline:run(['hyprctl','reload'])
        if snapshots(offline)!=before or read_runtime('workspace-columns.json')!=state:raise RuntimeError('desktop/core/state changed during restore; inspect')
        journal(backup,manifest,'restored-files')
    if not offline and not reduced and (pid or manifest.get('shell_was_running')):run(['quickshell','--daemonize','-p',home/'.config/quickshell'])
    journal(backup,manifest,'restored')
    print('Explicit cohort files restored; logical metadata/current-login marker never rolled back.')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    action=p.add_mutually_exclusive_group();action.add_argument('--apply',action='store_true');action.add_argument('--stage',action='store_true');action.add_argument('--restore',type=Path)
    p.add_argument('--preflight',action='store_true');p.add_argument('--allow-notification-history-reset',action='store_true');p.add_argument('--offline',action='store_true')
    mode=p.add_mutually_exclusive_group();mode.add_argument('--movement-only',action='store_true');mode.add_argument('--startup-only',action='store_true');mode.add_argument('--visuals-only',action='store_true')
    a=p.parse_args(argv)
    if a.preflight:
        guard(a.offline,a.allow_notification_history_reset,'movement' if a.movement_only else 'startup' if a.startup_only else 'visuals' if a.visuals_only else None)
        print('Preflight only; no files, state or shell changed.');return
    if not any([a.apply,a.stage,a.restore]):
        print('Plan only. Stage immutable cohort without activation: --stage. Full activation: --apply --allow-notification-history-reset, or explicitly offline with no compositor. Reduced updates require already native cohort/QML. No reset/window action.');return
    os.umask(0o077)
    if a.stage:print('Staged only, no live pointer/files/marker/QML change:',stage());return
    if a.restore:restore(a.restore,a.offline,a.allow_notification_history_reset)
    else:apply(a.offline,a.allow_notification_history_reset,'movement' if a.movement_only else 'startup' if a.startup_only else 'visuals' if a.visuals_only else None)

if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.SubprocessError) as e:raise SystemExit(f'Desktop cohort stopped: {e}; inspect journal/backup; no automatic rollback/retry.')
