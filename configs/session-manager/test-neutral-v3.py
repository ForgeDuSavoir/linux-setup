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
           'SESSION_COLUMNS_SCRIPT': str(HERE.parent / 'hypr/files/Scripts/workspace-columns.py'),
           'RUSTUP_HOME': os.environ.get('RUSTUP_HOME', str(Path.home()/'.rustup')),
           'CARGO_HOME': os.environ.get('CARGO_HOME', str(Path.home()/'.cargo')),
           'CARGO_NET_OFFLINE': 'true'}
    with patch.dict(os.environ, env, clear=True):
        desktop = load('neutral_desktop', HERE / 'session-desktop.py')
        pi = load('neutral_pi', HERE / 'session-pi.py')
        pi.MANAGER = BINARY
        (root / '.local/bin/session-manager').symlink_to(BINARY)
        launcher_binary = HERE / 'app-launcher/target/release/session-app-launcher'
        fake_gtk = root / 'bin/gtk-launch'
        fake_gtk.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/browser-args"\n')
        fake_gtk.chmod(0o700)
        active = [1]
        clients = [{'workspace': {'id': 1, 'name': '1'}}]
        monitor = {'focused': True, 'activeWorkspace': {'id': 1}, 'specialWorkspace': {'name': ''}}
        def query(key):
            return {'instances': [{'instance': os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', 'fixture-login')}],
                    'monitors': [monitor], 'clients': clients,
                    'workspaces': [{'id': active[0]}, {'id': 1}]}[key]
        native_file = root / 'native-monitor.json'
        native_file.write_text(json.dumps([monitor]))
        hypr = root / 'bin/hyprctl'
        hypr.write_text('#!/usr/bin/python3\nimport os\nfrom pathlib import Path\nprint("[]" if "instances" in __import__("sys").argv else (Path(os.environ["HOME"])/"native-monitor.json").read_text())\n')
        hypr.chmod(0o700)
        def focus(ws):
            active[0] = ws
            monitor['activeWorkspace']['id'] = ws
            native_file.write_text(json.dumps([monitor]))
        desktop.columns.query = query
        desktop.columns.active = lambda: active[0]
        desktop.columns.focus = focus
        desktop.columns.focus_empty = focus
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
            assert state['owners'] == {'1': 'neutral', '4': b['id']}
            assert state['order'] == [1, 4], 'departed empty workspaces are not reserved'
            assert [s['id'] for s in desktop.request('list')['sessions']] == [a['id'], p['id'], b['id']]
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
            subprocess.run([str(launcher_binary), '--browser'], env=env, check=True, timeout=8)
            assert (root / 'browser-args').read_text() == 'firefox.desktop\n'
            assert desktop.request('list')['active_session_id'] == b['id']
            notify = load('neutral_notify', HERE / 'agora-notify.py')
            # Use the read-only confirmed snapshot, not application identity or a shared bucket.
            snapshot = desktop.status()
            with patch.object(notify.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps(snapshot), '')
                assert notify.capture() == 'session:' + b['id']
            desktop.invoke('deactivate')
            assert desktop.status()['displayed_context'] == 'neutral'
            assert desktop.status()['active_session_id'] is None
            assert '4' not in desktop.columns.load()['owners']
            assert b['id'] in [s['id'] for s in desktop.request('list')['sessions']]
            assert clients[1]['workspace']['name'] == 'special:session-ai'
            desktop.invoke('switch', b['id'])
            desktop.invoke('stop', b['id'])
            after_stop = desktop.status()
            assert after_stop['active_session_id'] == p['id'] and after_stop['context_confirmed']
            assert [s['id'] for s in after_stop['sessions']] == [p['id']]
            original = desktop.request('list')
            try:
                desktop.invoke('stop', p['id'])
                raise AssertionError('last graphical session must not be stopped')
            except RuntimeError as error:
                assert 'last open session' in str(error)
            assert desktop.request('list') == original, 'refused stop must be revision-stable'
            startup = load('neutral_startup', HERE / 'session-startup.py')
            startup.desktop = desktop
            startup.columns = desktop.columns
            with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'fixture-login'}):
                assert startup.initialize()
                fresh = desktop.request('list')
                assert len(fresh['sessions']) == 1
                assert fresh['sessions'][0]['name'] == 'Neutral-1'
                assert fresh['sessions'][0]['source'] == {'kind': 'neutral'}
                assert desktop.status()['context_confirmed']
                assert not startup.initialize()
                assert desktop.request('list') == fresh, 'repeat startup must not change revision'
            with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'fixture-relogin'}):
                assert startup.initialize()
                relogin = desktop.request('list')
                assert len(relogin['sessions']) == 1 and relogin['sessions'][0]['name'] == 'Neutral-1'
                assert relogin['active_session_id'] != fresh['active_session_id']
                assert desktop.status()['context_confirmed']
            assert clients == [{'workspace': {'id': 1, 'name': '1'}},
                               {'workspace': {'id': -9, 'name': 'special:session-ai'}}]
        finally:
            if daemon.poll() is None:
                daemon.send_signal(signal.SIGTERM)
            daemon.wait(timeout=8)
            daemon.stderr.close()

        # Production installation is deliberately blocked on v2, before copying clients/QML.
        manager = root / '.local/bin/session-manager'
        manager.unlink()  # Remove the owned fixture symlink; never write through it to BINARY.
        manager.write_text('#!/bin/sh\necho "session-manager fixture (protocol 2)"\n')
        manager.chmod(0o700)
        for script in [HERE / 'configure_session_manager.sh', HERE / 'install_desktop_integration.sh',
                       HERE.parent / 'quickshell/install_quickshell_config.sh']:
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True, timeout=10)
            assert result.returncode != 0 and 'require protocol 3' in result.stderr, result.stderr
        assert not (root / '.config/quickshell/SessionMenu.qml').exists()
        assert not (root / '.local/bin/session-desktop').exists()

        # Exercise the actual targeted installers against a staged v3 stack only.
        personal=root/'detached-projects/P/.session-manager/apps/session-pi.desktop'
        personal.parent.mkdir(parents=True,exist_ok=True)
        personal.write_text('[Desktop Entry]\nType=Application\nName=Personal Pi\nExec=session-pi\n')
        personal_bytes=personal.read_bytes()
        manager.unlink()
        manager.symlink_to(BINARY)
        (root / 'detached-projects').rename(root / 'projects')
        systemctl = root / 'bin/systemctl'
        systemctl.write_text('#!/bin/sh\ncase "$*" in *MainPID*) echo 0;; esac\nexit 0\n')
        systemctl.chmod(0o700)
        result = subprocess.run(['bash', str(HERE / 'configure_session_manager.sh')],
                                env={**env, 'SESSION_MANAGER_PROJECT_SOURCE': str(root / 'projects'),'AGORA_DESKTOP_OFFLINE':'1'},
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        for name in ['SessionMenu.qml', 'SessionStrip.qml', 'SessionService.qml', 'NotificationStore.qml']:
            assert (root / '.config/quickshell' / name).read_bytes() == (HERE.parent / 'quickshell/files' / name).read_bytes()
        assert (root / '.local/bin/session-desktop').is_symlink()
        assert (root / '.local/bin/session-desktop').read_bytes()[:4]==b'\x7fELF'
        assert (root/'.local/bin/session-pi').read_bytes()==(HERE.parents[1]/'runtime/target/release/session-pi').read_bytes()
        assert (root/'projects/P/.session-manager/apps/session-pi.desktop').read_bytes()==personal_bytes
        systemctl.write_text('#!/bin/sh\necho ' + str(os.getpid()) + '\n')
        result = subprocess.run(['bash', str(HERE / 'install_desktop_integration.sh')],
                                env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and 'different executable' in result.stderr
        result = subprocess.run(['bash', str(HERE.parents[1] / 'packages/productivity/session-manager/install_session_manager.sh')],
                                env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and 'Stop the known' in result.stderr
        assert not (root / '.cache/linux-setup/session-manager').exists(), 'must refuse before fetching/replacing anything'
print('V3 real core/fake desktop: multiple neutral UUIDs, empty columns, guards, launchers, capture and staged installers passed.')
