#!/usr/bin/env python3
"""R7 private syscall failures/late race and externally interrupted fake CLI."""
import json,os,signal,subprocess,tempfile,time
from pathlib import Path
from filmcraft_fixture import ROOT,BIN,fixture
def setup(root,world):
    root.mkdir();(root/'recording.mkv').write_bytes(b'fixture')
    public=root/'premontage.fcproj';public.write_text(json.dumps(fixture()));original=public.read_bytes()
    (root/'world').write_text(json.dumps(world));bin=root/'bin';bin.mkdir()
    for name in ['ffprobe','ffmpeg','filmcraft-cli']:
        p=bin/name;p.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom filmcraft_fixture import cli\ncli()\n');p.chmod(0o700)
    return public,original,{'HOME':str(root),'PATH':str(bin)+':/usr/bin:/bin','FILM_WORLD':str(root/'world'),'PYTHONDONTWRITEBYTECODE':'1'}
with tempfile.TemporaryDirectory(prefix='r7-fault-') as d:
    root=Path(d);shim=root/'faults.so'
    subprocess.run(['cc','-shared','-fPIC',str(ROOT/'tests/filmcraft_faults.c'),'-ldl','-o',str(shim)],check=True,capture_output=True)
    for kind in ['before','after','lost-reply','late-edit']:
        folder=root/kind;project,original,env=setup(folder,{})
        result=subprocess.run([str(BIN),str(folder/'recording.mkv'),str(project)],env={**env,'LD_PRELOAD':str(shim),'R7_FAULT':kind},capture_output=True,text=True,timeout=10)
        assert result.returncode==1,(kind,result.stderr)
        assert (folder/'recording_bureau.wav').is_file()
        backups=list(folder.glob('.filmcraft-original-*'))
        if kind=='before':
            assert project.read_bytes()==original and not backups
        else:
            assert len(backups)==1 and json.loads(project.read_text())['_inspect']['audio'].__len__()==3
            assert backups[0].read_bytes()==original+(b'\n ' if kind=='late-edit' else b'')
            assert str(backups[0]) in result.stderr
        assert not list(folder.glob('.filmcraft-bureau-*')) and not list(folder.glob('.filmcraft-pad-*'))
    for stage in ['before','missing']:
        folder=root/('timeout-'+stage);project,original,env=setup(folder,{'sleep':stage})
        process=subprocess.Popen([str(BIN),str(folder/'recording.mkv'),str(project)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            deadline=time.monotonic()+5
            while True:
                calls=(folder/'calls').read_text() if (folder/'calls').exists() else ''
                if ('"inspect", "sequence"' in calls if stage=='before' else 'media.findMissing' in calls):break
                assert process.poll() is None and time.monotonic()<deadline;time.sleep(.01)
            # Harness timeout owns the entire isolated fake-process group only.
            os.killpg(process.pid,signal.SIGTERM);process.communicate(timeout=3)
            assert project.read_bytes()==original
            if stage=='missing':assert (folder/'recording_bureau.wav').is_file()
            else:assert not (folder/'recording_bureau.wav').exists()
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.communicate()
print('R7 syscall faults before/after exchange, lost reply, late external edit and two harness timeouts preserve all originals/concurrent data; no replay/rollback or live process.')
