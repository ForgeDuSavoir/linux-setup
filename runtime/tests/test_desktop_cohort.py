#!/usr/bin/env python3
"""R8 first activation, repeat/reduced updates, private daemon and explicit rollback."""
import json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from cohort_fixture import Fixture,ROOT,installer

with tempfile.TemporaryDirectory(prefix='r8-cohort-') as d:
    f=Fixture(Path(d))
    try:
        f.start();a=f.core('start','--project','P');logical=f.core('list');raw=f.state.read_bytes();marker=f.marker.read_bytes()
        # Keep spatial/logical mismatch: installer never repairs it by focus/adoption.
        source_qml=(f.root/'.config/quickshell/shell.qml').read_bytes();pid=(f.root/'qs.pid').read_text()
        f.run();assert not (f.root/'.local/libexec/agora-desktop').exists()
        for args in [('--apply',),('--apply','--movement-only'),('--apply','--startup-only'),('--apply','--offline')]:f.run(*args,ok=False)
        assert (f.root/'qs.pid').read_text()==pid and f.marker.read_bytes()==marker
        f.run('--stage')
        assert (f.root/'.config/quickshell/shell.qml').read_bytes()==source_qml and (f.root/'qs.pid').read_text()==pid
        assert not (f.root/'.local/libexec/agora-desktop/current').exists()
        f.run('--apply','--allow-notification-history-reset')
        backup=f.backups()[0];assert json.loads((backup/'manifest.json').read_text())['phase']=='complete'
        assert f.state.read_bytes()==raw and f.core('list')==logical and f.marker.read_bytes()==marker
        assert (f.root/'qs.pid').read_text()!=pid;f.reap()
        for name in installer.BINS:
            p=f.root/'.local/bin'/name;assert p.is_symlink() and p.read_bytes()[:4]==b'\x7fELF'
        shell=f.root/'.config/quickshell/shell.qml';assert 'workspace-controller' in shell.read_text() and 'workspace-columns.py' not in shell.read_text()
        # Read-only native ABI works despite a poisoned historical controller.
        status=subprocess.run([str(f.root/'.local/bin/session-desktop'),'status'],env=f.env,capture_output=True,text=True,timeout=5)
        assert status.returncode==0 and not json.loads(status.stdout)['context_confirmed']
        # Repeated startup in this same login never executes/reset/relaunches a bar.
        calls=(f.root/'qs.calls').read_text();r=subprocess.run([str(f.root/'.local/bin/session-startup')],env=f.env,capture_output=True,timeout=5)
        assert r.returncode==0 and f.core('list')==logical and (f.root/'qs.calls').read_text()==calls
        f.run('--apply','--allow-notification-history-reset');assert len(f.backups())==1 and (f.root/'qs.calls').read_text()==calls
        # A controlled damaged-generation refusal must not even stop the shell.
        gen=(f.root/'.local/libexec/agora-desktop/current').resolve()
        damaged=gen/'workspace-controller';original=damaged.read_bytes();damaged.write_bytes(b'bad')
        f.run('--apply','--allow-notification-history-reset',ok=False);assert (f.root/'qs.calls').read_text()==calls
        damaged.write_bytes(original)
        # Restore refuses foreign later files.
        key=f.root/'.config/hypr/keybinds.lua';new=key.read_bytes();key.write_bytes(b'personal edit')
        f.run('--restore',str(backup),'--allow-notification-history-reset',ok=False);assert key.read_bytes()==b'personal edit'
        key.write_bytes(new)
        f.run('--restore',str(backup),'--allow-notification-history-reset')
        assert (f.root/'.config/quickshell/shell.qml').read_bytes()==source_qml
        assert (f.root/'.local/bin/session-desktop').read_text()=='# old session-desktop\n'
        assert f.state.read_bytes()==raw and f.core('list')==logical and f.marker.read_bytes()==marker
        f.reap()
        # Inject an interruption after pointer/publication starts, not a rollback.
        original_atomic=installer.atomic_bytes
        def fail_key(path,data,mode=0o600):
            if path==f.root/'.config/hypr/keybinds.lua':raise OSError('synthetic interrupted publication')
            return original_atomic(path,data,mode)
        with patch.dict(os.environ,f.env,clear=True),patch.object(installer,'atomic_bytes',side_effect=fail_key):
            try:installer.apply(allow=True);raise AssertionError('fault not reached')
            except OSError:pass
        failed=next(p for p in f.backups() if p!=backup)
        assert json.loads((failed/'manifest.json').read_text())['phase']=='current-published'
        assert f.state.read_bytes()==raw and f.core('list')==logical
        f.run('--restore',str(failed),'--allow-notification-history-reset')
        assert (f.root/'.config/quickshell/shell.qml').read_bytes()==source_qml
        f.reap()
        # Failure after stopping shell but before a pointer/file is published.
        prior=set(f.backups())
        with patch.dict(os.environ,f.env,clear=True),patch.object(installer,'defer',side_effect=OSError('pre-pointer failure')):
            try:installer.apply(allow=True);raise AssertionError('fault not reached')
            except OSError:pass
        untouched=(set(f.backups())-prior).pop()
        assert json.loads((untouched/'manifest.json').read_text())['phase']=='shell-stopped'
        assert not (f.root/'qs.pid').exists()
        f.run('--restore',str(untouched),'--allow-notification-history-reset')
        assert (f.root/'qs.pid').exists() and f.core('list')==logical and f.state.read_bytes()==raw
        f.reap()
    finally:f.close()
print('R8 private native/core cohort: gate, stage/no activation, first handoff, no-op repeat, poisoned Python independence, same-login startup, corruption/foreign edits, partial failure and explicit restore passed.')
