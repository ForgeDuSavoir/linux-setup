#!/usr/bin/env python3
"""Targeted extension install in private HOME, with fake Pi capability/core tools."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='pi-notify-install-') as directory:
    root=Path(directory)
    for relative in ['bin','.local/bin','runtime','.pi/agent/extensions','pkg/dist/core/extensions']:
        (root/relative).mkdir(parents=True,exist_ok=True)
    types=root/'pkg/dist/core/extensions/types.d.ts';types.write_text('export interface AgentSettledEvent { type: "agent_settled"; aborted: boolean; }')
    cli=root/'pkg/dist/cli.js';cli.write_text('// never executed during installation\n');cli.chmod(0o700)
    (root/'bin/pi').symlink_to(cli)
    for target,content in [(root/'bin/systemctl','#!/bin/sh\necho 0\n'),
                           (root/'.local/bin/session-manager','#!/bin/sh\necho "fixture (protocol 3)"\n')]:
        target.write_text(content);target.chmod(0o700)
    old_launcher=root/'.local/bin/session-pi';old_launcher.write_text('# old launcher\n')
    settings=root/'.pi/agent/settings.json';settings.write_text('{"keep":"unchanged"}\n')
    footer=root/'.pi/agent/extensions/personal.ts';footer.write_text('// personal extension stays untouched\n')
    env={'HOME':str(root),'PATH':str(root/'bin')+':/usr/bin:/bin','XDG_RUNTIME_DIR':str(root/'runtime'),'XDG_STATE_HOME':str(root/'state'),'RUSTUP_HOME':os.environ.get('RUSTUP_HOME',str(Path.home()/'.rustup')),'CARGO_HOME':os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))}
    def run(*args):
        return subprocess.run(['/usr/bin/python3',str(HERE/'install.py'),*args],env=env,capture_output=True,text=True,timeout=60)
    result=run();assert result.returncode==0 and 'No reload' in result.stdout,result.stdout+result.stderr
    target=root/'.pi/agent/extensions/agora-notifications/index.ts'
    assert not target.exists() and old_launcher.read_text()=='# old launcher\n'
    result=run('--apply');assert result.returncode==0,result.stdout+result.stderr
    assert target.read_bytes()==(HERE/'index.ts').read_bytes()
    assert (root/'.local/bin/agora-notify').read_bytes()==(HERE.parents[2]/'runtime/target/release/agora-notify').read_bytes()
    assert (root/'.local/bin/agora-notify').read_bytes().startswith(b'\x7fELF')
    assert old_launcher.read_bytes()==(HERE.parents[2]/'runtime/target/release/session-pi').read_bytes()
    assert settings.read_text()=='{"keep":"unchanged"}\n' and footer.read_text().startswith('// personal extension')
    backups=list((root/'state/linux-setup/pi-notifications').iterdir())
    assert len(backups)==1 and backups[0].stat().st_mode & 0o777==0o700
    assert (backups[0]/'.local/bin/session-pi').read_text()=='# old launcher\n'
    old_launcher.write_bytes(b'\x7fELFfuture-launcher');preserve_launcher=old_launcher.read_bytes()
    result=run('--apply');assert result.returncode==0,result.stdout+result.stderr
    assert old_launcher.read_bytes()==(HERE.parents[2]/'runtime/target/release/session-pi').read_bytes(), 'install validated Rust; never downgrade to Python'
    other=root/'other';other.write_text('preserve');target.unlink();target.symlink_to(other)
    result=run('--apply');assert result.returncode!=0 and other.read_text()=='preserve'
    target.unlink();types.write_text('old Pi without final settlement')
    result=run('--apply');assert result.returncode!=0 and 'agent_settled' in result.stderr
    assert not target.exists()
print('Pi notification installer: dry run, capability gate, private backup, helper/launcher/extension copies, preserved personal settings/extensions and symlink refusal passed.')
