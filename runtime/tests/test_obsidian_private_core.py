#!/usr/bin/env python3
"""Genuine private v3 core + Rust desktop status, no Obsidian process."""
import json,subprocess,tempfile
from pathlib import Path
from cohort_fixture import Fixture,ROOT
BIN=ROOT/'target/release/session-obsidian';A='0123456789abcdef';P='fedcba9876543210'
with tempfile.TemporaryDirectory(prefix='obsidian-core-') as d:
    f=Fixture(Path(d))
    try:
        f.start()
        desktop=f.root/'.local/bin/session-desktop';desktop.unlink();desktop.symlink_to(ROOT/'target/release/session-desktop')
        config=Path(f.env.get('XDG_CONFIG_HOME') or f.root/'.config')
        (config/'obsidian').mkdir(parents=True);(config/'agora-workflow').mkdir(parents=True,exist_ok=True)
        agora=f.root/'Agora';agora.mkdir();(agora/'.obsidian').mkdir()
        project=f.root/'projects/P';(project/'.obsidian').mkdir()
        (config/'agora-workflow/config.toml').write_text('agora_root = '+json.dumps(str(agora)))
        registry=config/'obsidian/obsidian.json';registry.write_text(json.dumps({'vaults':{A:{'path':str(agora)},P:{'path':str(project)}}}))
        def owner(sid):
            state=json.loads(f.state.read_text());state['owners']['1']=sid or 'neutral';f.state.write_text(json.dumps(state))
        def check(id):
            logical=f.core('list');metadata=f.state.read_bytes();registered=registry.read_bytes()
            r=subprocess.run([str(BIN),'--print-uri'],env=f.env,capture_output=True,text=True,timeout=8);assert r.returncode==0,r.stderr
            assert r.stdout.strip()=='obsidian://open?vault='+id
            assert f.core('list')==logical and f.state.read_bytes()==metadata and registry.read_bytes()==registered
            assert not list(f.root.rglob('app-usage.json'))
        check(A)
        a=f.core('start','--project','P')['session']['id'];owner(a);check(P)
        (project/'.obsidian').rmdir();check(A);(project/'.obsidian').mkdir()
        registry.write_text(json.dumps({'vaults':{A:{'path':str(agora)}}}));check(A)
        registry.write_text(json.dumps({'vaults':{A:{'path':str(agora)},P:{'path':str(project)}}}))
        b=f.core('start','--neutral')['session']['id'];owner(b);check(A)
        f.core('switch',a);owner(b);check(A)
        f.core('deactivate');owner(None);check(A)
    finally:f.close()
print('Obsidian private core: exact project, missing marker/registration, Neutral/no session and spatial mismatch; readonly core/metadata/registry, no GUI.')
