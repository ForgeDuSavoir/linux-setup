#!/usr/bin/env python3
"""Load the real session components offscreen with fake IPC and a private runtime."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

source = Path(__file__).resolve().parents[1] / 'quickshell/files'
with tempfile.TemporaryDirectory(prefix='session-qml-') as directory:
    root = Path(directory)
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700)
    config = root / 'qml'
    config.mkdir()
    for name in ('SessionService.qml', 'SessionMenu.qml', 'SessionStrip.qml'):
        shutil.copyfile(source / name, config / name)
    binary = root / '.local/bin/session-desktop'
    binary.parent.mkdir(parents=True)
    binary.write_text('''#!/bin/sh
printf '%s\\n' '{"revision":2,"sessions":[{"id":"z","name":"Linux Workflow-1","source":{"kind":"project","project_name":"Linux Workflow"},"number":1},{"id":"a","name":"Forge du Savoir-2","source":{"kind":"project","project_name":"Forge du Savoir"},"number":2}],"active_session_id":"a","displayed_context":"a","context_confirmed":true}'
''')
    binary.chmod(0o700)
    manager = binary.with_name('session-manager')
    manager.write_text('''#!/bin/sh
printf '%s\\n' '{"projects":[{"name":"Linux Workflow","path":"/fixture"}]}'
''')
    manager.chmod(0o700)
    (config / 'shell.qml').write_text('''import Quickshell
import QtQuick
import QtQuick.Window
Scope {
    SessionService { id: state }
    Window {
        visible: true  // Offscreen-only fixture: allow Qt to lay out delegates.
        width: 300; height: 30
        SessionStrip { id: strip; anchors.fill: parent; sessionService: state }
    }
    Timer {
        interval: 1200; running: true
        onTriggered: {
            if (state.sessions.length !== 2 || state.sessions[0].id !== "z"
                    || state.activeId !== "a" || !state.contextConfirmed || state.stale)
                console.error("FIXTURE_FAILED", state.error);
            else {
                console.log("SESSION_QML_FIXTURE_PASSED");
                const many = [];
                for (let i = 0; i < 60; i++)
                    many.push({id: "fixture-" + i, name: "Same Initials-" + (i + 1), source: {kind: "project", project_name: "Same Initials"}, number: i + 1});
                state.sessions = many;
            }
        }
    }
    Timer {
        interval: 1700; running: true
        onTriggered: {
            if (strip.entries.length !== 60 || strip.contentWidth <= strip.width)
                console.error("STRIP_OVERFLOW_FAILED", strip.entries.length, strip.contentWidth, strip.width);
            else {
                state.sessions = [];
                if (strip.entries.length === 0)
                    console.log("STRIP_OVERFLOW_AND_EMPTY_PASSED");
            }
            Qt.quit();
        }
    }
}
''')
    env = {'HOME': str(root), 'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(runtime),
           'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_CACHE_HOME': str(root / 'cache'),
           'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software', 'NO_COLOR': '1'}
    result = subprocess.run(['quickshell', '-p', str(config)], env=env,
                            capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    print(output)
    assert result.returncode == 0 and 'SESSION_QML_FIXTURE_PASSED' in output and 'STRIP_OVERFLOW_AND_EMPTY_PASSED' in output, output
    assert 'ReferenceError' not in output and 'Binding loop' not in output, output
print('Real session service/strip loaded offscreen with isolated fake processes (menu checked by qmllint): passed.')
