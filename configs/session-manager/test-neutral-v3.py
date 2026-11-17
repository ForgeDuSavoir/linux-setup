#!/usr/bin/env python3
"""V3 core/client contract and installers in owned HOME/XDG roots; fake Hyprland only."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BINARY = HERE.parents[2] / 'session-manager/target/debug/session-manager'
assert BINARY.is_file(), 'Build the neighbouring v3 core offline before this test'
assert subprocess.check_output([str(BINARY), '--version'], text=True).strip().endswith('(protocol 3)')


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='neutral-v3-') as directory:
    root = Path(directory)
    for relative in ['config/session-manager', 'runtime', 'state', 'data/applications',
                     'projects/P', 'projects/Neutral', 'Agora', 'bin', '.local/bin',
                     '.config/quickshell', '.config/hypr/Scripts']:
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / 'runtime').chmod(0o700)
    (root / 'config/session-manager/config-v2.toml').write_text(
        'schema_version=2\nproject_source=' + json.dumps(str(root / 'projects')) + '\n')
    (root / 'data/applications/firefox.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Firefox\nExec=never-run %u\n')
    workflow = root / 'config/agora-workflow/config.toml'
    workflow.parent.mkdir()
    workflow.write_text('agora_root=' + json.dumps(str(root / 'Agora')) + '\n')
    env = {'HOME': str(root), 'PATH': str(root / 'bin') + ':/usr/bin:/bin',
           'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data'),
           'XDG_DATA_DIRS': str(root / 'data'), 'XDG_STATE_HOME': str(root / 'state'),
           'XDG_RUNTIME_DIR': str(root / 'runtime'), 'SESSION_MANAGER_BIN': str(BINARY),
           'SESSION_COLUMNS_SCRIPT': str(HERE.parent / 'hypr/files/Scripts/workspace-columns.py')}
    with patch.dict(os.environ, env, clear=True):
        desktop = load('neutral_desktop', HERE / 'session-desktop.py')
        pi = load('neutral_pi', HERE / 'session-pi.py')
        launcher = load('neutral_launcher', HERE / 'session-app-launcher.py')
        pi.MANAGER = launcher.MANAGER = BINARY
        active = [1]
        clients = [{'workspace': {'id': 1, 'name': '1'}}]
        monitor = {'focused': True, 'activeWorkspace': {'id': 1}, 'specialWorkspace': {'name': ''}}
        def query(key):
            return {'monitors': [monitor], 'clients': clients,
                    'workspaces': [{'id': active[0]}, {'id': 1}]}[key]
        def focus(ws):
            active[0] = ws
            monitor['activeWorkspace']['id'] = ws
        desktop.columns.query = query
        desktop.columns.active = lambda: active[0]
        desktop.columns.focus = focus
        desktop.columns.dispatch = lambda _: (_ for _ in ()).throw(AssertionError('no real dispatcher'))
        daemon = subprocess.Popen([str(BINARY), 'daemon'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not (root / 'runtime/session-manager/ipc-v3.sock').exists():
                assert daemon.poll() is None, 'fixture daemon failed'
                assert time.monotonic() < deadline, 'fixture startup timeout'
                time.sleep(0.02)
            a = desktop.invoke('start', {'kind': 'neutral'})['session']
            p = desktop.invoke('start', {'kind': 'project', 'project_name': 'P'})['session']
            b = desktop.invoke('start', {'kind': 'neutral'})['session']
            assert a['name'] == 'Neutral-1' and b['name'] == 'Neutral-2'
            assert len({a['id'], p['id'], b['id']}) == 3
            state = desktop.columns.load()
            assert state['owners'] == {'1': 'neutral', '2': a['id'], '3': p['id'], '4': b['id']}
            assert clients == [{'workspace': {'id': 1, 'name': '1'}}]
            assert desktop.status()['context_confirmed']
            assert desktop.status()['displayed_context'] == b['id']
            # A neutral start must never adopt the legacy normal window or scratchpads.
            clients.append({'workspace': {'id': -9, 'name': 'special:session-ai'}})
            desktop.invoke('stop', a['id'])
            assert len(clients) == 2
            clients.append({'workspace': {'id': -10, 'name': 'special:sm-' + b['id'] + '-ai'}})
            try:
                desktop.invoke('stop', b['id'])
                raise AssertionError('nonempty neutral scratchpad must block stop')
            except RuntimeError as error:
                assert 'open windows' in str(error)
            clients.pop()
            # Current neutral launchers must not consult an unavailable project source.
            (root / 'projects').rename(root / 'detached-projects')
            assert pi.launch_command()[1:] == [str(root / 'Agora'), 'pi']
            assert launcher.selected_project_path() is None
            assert launcher.query('application', 'list')['applications'][0]['origin'] == 'installed'
            notify = load('neutral_notify', HERE / 'agora-notify.py')
            # Use the read-only confirmed snapshot, not application identity or a shared bucket.
            snapshot = desktop.status()
            with patch.object(notify.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps(snapshot), '')
                assert notify.capture() == 'session:' + b['id']
            desktop.invoke('deactivate')
            assert desktop.status()['displayed_context'] == 'neutral'
            assert desktop.status()['active_session_id'] is None
            assert desktop.columns.load()['owners']['4'] == b['id']
            assert clients[1]['workspace']['name'] == 'special:session-ai'
        finally:
            if daemon.poll() is None:
                daemon.send_signal(signal.SIGTERM)
            daemon.wait(timeout=8)
            daemon.stderr.close()

        # Production installation is deliberately blocked on v2, before copying clients/QML.
        manager = root / '.local/bin/session-manager'
        manager.write_text('#!/bin/sh\necho "session-manager fixture (protocol 2)"\n')
        manager.chmod(0o700)
        for script in [HERE / 'configure_session_manager.sh', HERE / 'install_desktop_integration.sh',
                       HERE.parent / 'quickshell/install_quickshell_config.sh']:
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True, timeout=10)
            assert result.returncode != 0 and 'require protocol 3' in result.stderr, result.stderr
        assert not (root / '.config/quickshell/SessionMenu.qml').exists()
        assert not (root / '.local/bin/session-desktop').exists()

        # Exercise the actual targeted installers against a staged v3 stack only.
        manager.unlink()
        manager.symlink_to(BINARY)
        (root / 'detached-projects').rename(root / 'projects')
        systemctl = root / 'bin/systemctl'
        systemctl.write_text('#!/bin/sh\ncase "$*" in *MainPID*) echo 0;; esac\nexit 0\n')
        systemctl.chmod(0o700)
        result = subprocess.run(['bash', str(HERE / 'configure_session_manager.sh')],
                                env={**env, 'SESSION_MANAGER_PROJECT_SOURCE': str(root / 'projects')},
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        for name in ['SessionMenu.qml', 'SessionStrip.qml', 'SessionService.qml', 'NotificationStore.qml']:
            assert (root / '.config/quickshell' / name).read_bytes() == (HERE.parent / 'quickshell/files' / name).read_bytes()
        assert (root / '.local/bin/session-desktop').read_bytes() == (HERE / 'session-desktop.py').read_bytes()
        systemctl.write_text('#!/bin/sh\necho ' + str(os.getpid()) + '\n')
        result = subprocess.run(['bash', str(HERE / 'install_desktop_integration.sh')],
                                env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and 'different executable' in result.stderr
        result = subprocess.run(['bash', str(HERE.parents[1] / 'packages/productivity/session-manager/install_session_manager.sh')],
                                env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and 'Stop the known' in result.stderr
        assert not (root / '.cache/linux-setup/session-manager').exists(), 'must refuse before fetching/replacing anything'
print('V3 real core/fake desktop: multiple neutral UUIDs, empty columns, guards, launchers, capture and staged installers passed.')
