#!/usr/bin/env python3
"""Upgrade four-command generations to session-files, and restore older manifests."""
import os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from cohort_fixture import Fixture,ROOT,installer
with tempfile.TemporaryDirectory(prefix='files-cohort-') as d:
    f=Fixture(Path(d))
    try:
        f.start();original_files=installer.files
        def old_files():
            files=original_files();k='.config/hypr/keybinds.lua';data,mode=files[k]
            files[k]=(data.replace(b'"$HOME/.local/bin/session-files"',b'xdg-open "$HOME"'),mode);return files
        with patch.dict(os.environ,f.env,clear=True),patch.object(installer,'BINS',installer.BASE_BINS),patch.object(installer,'files',side_effect=old_files):
            installer.apply(allow=True)
        old=f.backups()[0];old_pointer=os.readlink(f.root/'.local/libexec/agora-desktop/current')
        command=f.root/'.local/bin/session-files';assert not command.exists()
        pid=(f.root/'qs.pid').read_bytes();calls=(f.root/'qs.calls').read_bytes()
        qml=(f.root/'.config/quickshell/shell.qml').read_bytes();metadata=f.state.read_bytes();logical=f.core('list')
        # Never replace a personal command when expanding an existing cohort.
        command.write_bytes(b'personal command');f.run('--apply','--movement-only',ok=False);assert command.read_bytes()==b'personal command'
        command.unlink()
        f.run('--apply','--movement-only')
        new=next(p for p in f.backups() if p!=old)
        assert command.is_symlink() and command.read_bytes()[:4]==b'\x7fELF'
        assert (f.root/'qs.pid').read_bytes()==pid and (f.root/'qs.calls').read_bytes()==calls
        assert (f.root/'.config/quickshell/shell.qml').read_bytes()==qml
        assert f.state.read_bytes()==metadata and f.core('list')==logical
        f.run('--restore',str(new))
        assert not command.exists() and os.readlink(f.root/'.local/libexec/agora-desktop/current')==old_pointer
        assert (f.root/'qs.calls').read_bytes()==calls
        # The pre-expansion four-command backup is still interpreted correctly.
        f.run('--restore',str(old),'--allow-notification-history-reset')
        assert not (f.root/'.local/libexec/agora-desktop/current').exists()
        f.reap()
    finally:f.close()
print('session-files cohort expansion: old-four to five, personal-command refusal, no QML/PID/state change, expansion rollback and old manifest restore passed.')
