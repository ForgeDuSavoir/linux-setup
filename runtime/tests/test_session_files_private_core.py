#!/usr/bin/env python3
"""Real private core + Rust desktop status; fake native tools/default opener only."""
import json,subprocess,tempfile
from pathlib import Path
from cohort_fixture import Fixture,ROOT
BIN=ROOT/'target/release/session-files'
with tempfile.TemporaryDirectory(prefix='files-core-') as d:
    f=Fixture(Path(d))
    try:
        f.start()
        desktop=f.root/'.local/bin/session-desktop';desktop.unlink();desktop.symlink_to(ROOT/'target/release/session-desktop')
        opener=f.root/'bin/xdg-open';opener.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n(Path(os.environ["HOME"])/"opened").write_text(json.dumps(sys.argv[1:]))\n');opener.chmod(0o700)
        def owner(sid):
            state=json.loads(f.state.read_text());state['owners']['1']=sid or 'neutral';f.state.write_text(json.dumps(state))
        def check(path):
            logical=f.core('list');metadata=f.state.read_bytes()
            r=subprocess.run([str(BIN)],env=f.env,capture_output=True,text=True,timeout=8);assert r.returncode==0,r.stderr
            assert json.loads((f.root/'opened').read_text())==[str(path)]
            assert f.core('list')==logical and f.state.read_bytes()==metadata
            assert not list(f.root.rglob('app-usage.json'))
        check(f.root)
        a=f.core('start','--project','P')['session']['id'];owner(a);check(f.root/'projects/P')
        (f.root/'projects').rename(f.root/'unavailable');check(f.root);(f.root/'unavailable').rename(f.root/'projects')
        b=f.core('start','--neutral')['session']['id'];owner(b);check(f.root)
        f.core('switch',a);owner(b);check(f.root) # Inconsistent logical/spatial owner.
        f.core('deactivate');owner(None);check(f.root)
    finally:f.close()
print('session-files private core: project, unavailable catalogue, Neutral, no session and spatial mismatch; readonly state/core, fake opener, no GUI.')
