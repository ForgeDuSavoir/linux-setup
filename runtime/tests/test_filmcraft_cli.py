#!/usr/bin/env python3
"""R7 syntax/path guard/lock tests in private fixture HOME."""
import fcntl,json,os,subprocess,tempfile
from pathlib import Path
from filmcraft_fixture import ROOT,BIN,fixture
with tempfile.TemporaryDirectory(prefix='r7-cli-') as d:
    root=Path(d);source=root/'recording.mkv';source.write_bytes(b'fixture');project=root/'premontage.fcproj';project.write_text(json.dumps(fixture()))
    env={'HOME':str(root),'PATH':'/usr/bin:/bin'}
    for args in [[],['--help'],[str(source)],[str(source),str(project),'extra'],[str(root/'missing'),str(project)]]:
        r=subprocess.run([str(BIN),*args],env=env,capture_output=True,timeout=3);assert r.returncode==1
    r=subprocess.run([str(BIN),'--version'],env={},capture_output=True,text=True);assert r.returncode==0 and '(Rust; exact stereo stream)' in r.stdout
    other=root/'other';other.mkdir();foreign=other/'recording.mkv';foreign.write_bytes(b'foreign')
    r=subprocess.run([str(BIN),str(foreign),str(project)],env=env,capture_output=True,timeout=3);assert r.returncode==1 and foreign.read_bytes()==b'foreign'
    before=project.read_bytes()
    with project.open('rb') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        r=subprocess.run([str(BIN),str(source),str(project)],env=env,capture_output=True,text=True,timeout=3)
        assert r.returncode==1 and 'verrouillé' in r.stderr
    assert project.read_bytes()==before and not list(root.glob('*.wav'))
    pre_edit=(ROOT.parent/'scripts/pre-edit/pre-edit.sh').read_text()
    assert 'filmcraft-patch-desktop-audio "$INPUT" "$FILMCRAFT_PROJECT"' in pre_edit
print('R7 CLI: syntax, missing/different-folder files, side-effect-free version, interprocess flock and existing literal pre-edit entry passed.')
