#!/usr/bin/env python3
"""Isolated files, fake OBS helpers and actual Gio; never run camera/OBS commands."""
import importlib.util,json,os,subprocess,tempfile,time
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('profiles',HERE/'install_project_launchers.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fails(fn):
    try:fn()
    except (OSError,RuntimeError):return
    raise AssertionError('unsafe plan accepted')
with tempfile.TemporaryDirectory(prefix='obs-project-') as d:
 h=Path(d)/'Home "quotes" \\ $` % é';h.mkdir();projects=h/'projects';projects.mkdir();data=h/'data';state=h/'state';base=state/'backups';base.mkdir(parents=True)
 env={**os.environ,'HOME':str(h),'XDG_DATA_HOME':str(data),'XDG_STATE_HOME':str(state),'SESSION_MANAGER_PROJECT_SOURCE':str(projects)}
 with patch.dict(os.environ,env,clear=True):
    # Two projects with unrelated user-owned profiles/exclusions.
    for key,(project,command,folder,template) in m.PROFILES.items():
        p=projects/project/'.session-manager/apps';p.mkdir(parents=True)
        (p/'exclude.txt').write_text('keep-this.desktop\n');(p/'firefox.desktop').write_text('personal browser')
        b=h/'.local/bin'/command;b.parent.mkdir(parents=True,exist_ok=True)
        b.write_text('#!/usr/bin/python3\nimport os,sys,json\nfrom pathlib import Path\nPath(os.environ["OBS_TEST_CAPTURE"]).write_text(json.dumps([Path(sys.argv[0]).name,sys.argv[1:]]))\n');b.chmod(0o755)
        old=data/'applications'/(command+'.desktop');old.parent.mkdir(parents=True,exist_ok=True)
        old.write_text((m.ROOT/'scripts'/folder/template).read_text().replace('__HOME_DIR__',str(h)))
    helpers={c:(h/'.local/bin'/c).read_bytes() for _,c,_,_ in m.PROFILES.values()}
    untouched={p:p.read_bytes() for p in projects.glob('*/.session-manager/apps/*')}
    ops=m.plan(h,projects,list(m.PROFILES),True);assert len(ops)==4
    m.apply(ops,base)
    for i,(key,(project,command,folder,template)) in enumerate(m.PROFILES.items()):
        entry=projects/project/'.session-manager/apps/com.obsproject.Studio.desktop'
        assert entry.exists() and not (data/'applications'/(command+'.desktop')).exists()
        capture=h/('capture'+str(i))
        r=subprocess.run(['gio','launch',str(entry)],env={**env,'OBS_TEST_CAPTURE':str(capture),'DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(h/'no-bus')},capture_output=True,text=True)
        assert r.returncode==0,(r.stderr,entry.read_text())
        for _ in range(100):
            if capture.exists():break
            time.sleep(.01)
        assert json.loads(capture.read_text())==[command,[]]
    assert all(p.read_bytes()==v for p,v in untouched.items())
    assert all((h/'.local/bin'/c).read_bytes()==v for c,v in helpers.items())
    assert m.plan(h,projects,list(m.PROFILES),True)==[]
    assert len(list(base.iterdir()))==1
    # Unknown project/local/global content is not overwritten or deleted.
    fds=projects/m.PROFILES['fds'][0]/'.session-manager/apps/com.obsproject.Studio.desktop';original=fds.read_bytes();fds.write_bytes(original+b'# personal\n')
    fails(lambda:m.plan(h,projects,['fds'],True));fds.write_bytes(original)
    legacy=data/'applications/obs-fds.desktop';legacy.write_text('personal entry')
    fails(lambda:m.plan(h,projects,['fds'],True));assert legacy.read_text()=='personal entry';legacy.unlink()
    fds.unlink();fds.symlink_to(next(iter(untouched)))
    fails(lambda:m.plan(h,projects,['fds'],True));fds.unlink();fds.write_bytes(original)
    fails(lambda:m.plan(h,Path('relative'),['fds'],True))
    # A rename/deleted project is not recreated and its legacy global is retained.
    qmk=projects/m.PROFILES['qmk'][0];qmk.rename(projects/'moved')
    legacy=data/'applications/obs-gaming.desktop';legacy.write_text('not touched without project')
    assert m.plan(h,projects,['qmk'],True)==[] and legacy.exists();legacy.unlink()
    # Fresh regular installation installs the correct canonical helper names,
    # including the previously broken Gaming installer filename.
    for key,(_,c,folder,_) in m.PROFILES.items():
        planned=m.plan(h,projects,[key],False)
        row=next(o for o in planned if o[0]==h/'.local/bin'/c)
        assert row[1]==(m.ROOT/'scripts'/folder/(folder+'.sh')).read_bytes()
    assert not (h/'.local/bin/run-obs-gaming').exists()
    # Target failure never removes the old shortcut before the project is ready.
    legacy=data/'applications/obs-fds.desktop'
    legacy.write_text((m.ROOT/'scripts/run-obs-fds/obs-fds.desktop').read_text().replace('__HOME_DIR__',str(h)))
    fds.unlink();ops=m.plan(h,projects,['fds'],True);real=m.atomic
    def fault(p,data,mode):
        if p==fds:raise OSError('injected project publication failure')
        return real(p,data,mode)
    with patch.object(m,'atomic',side_effect=fault):fails(lambda:m.apply(ops,base))
    assert legacy.exists() and not fds.exists()
    # A concurrent personal edit after planning is refused before publication.
    legacy.write_text('changed after plan');fails(lambda:m.apply(ops,base))
    assert legacy.read_text()=='changed after plan' and not fds.exists()
print('OBS project launchers: exact-ID overrides, global migration, literal Gio/complex HOME, preserved helpers/other profiles, idempotence, personal/symlink/relative guards, absent project and canonical install names passed; no OBS/camera.')
