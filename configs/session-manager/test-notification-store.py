#!/usr/bin/env python3
"""Real Quickshell notification server on a PRIVATE D-Bus, no live desktop/bus."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'


def inside():
    source = Path(__file__).resolve().parents[1] / 'quickshell/files'
    with tempfile.TemporaryDirectory(prefix='notification-store-') as directory:
        root = Path(directory)
        runtime = root / 'runtime'
        runtime.mkdir(mode=0o700)
        config = root / 'qml'
        config.mkdir()
        for name in ('NotificationStore.qml', 'NotificationPolicy.js', 'SessionStrip.qml'):
            shutil.copyfile(source / name, config / name)
        (config / 'shell.qml').write_text('''import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Window
Scope {
    // Exercise startup before the referenced session object is initialized.
    NotificationStore { id: store; sessionService: session }
    Scope {
        id: session
        property var sessions: [{id:"UUID_A",name:"Neutral-1",source:{kind:"neutral"},number:1},{id:"UUID_B",name:"Neutral-2",source:{kind:"neutral"},number:2},{id:"44444444-4444-4444-4444-444444444444",name:"C-1",source:{kind:"project",project_name:"Gamma"},number:1}]
        property bool busy: false
        property string displayedContext: "UUID_A"
        property string visualContext: "UUID_A"
        property bool contextConfirmed: true
        property bool stale: false
        signal updated()
    }
    Window {
        visible: false; width: 300; height: 30
        SessionStrip { id: strip; anchors.fill: parent; sessionService: session; notificationState: store }
    }
    function redCases(item) {
        let count = 0;
        if (item.objectName && item.objectName.indexOf("session-case-") === 0 && String(item.background.border.color) === "#d66b6b") count++;
        for (const child of item.children || []) count += redCases(child);
        return count;
    }
    IpcHandler {
        target: "fixture"
        function state(): string { return JSON.stringify({history:store.history, unread:store.unread, popups:store.popupNotifications.length, redCases:redCases(strip)}); }
        function context(value: string, confirmed: bool): void {
            session.contextConfirmed = false;
            session.displayedContext = value;
            session.contextConfirmed = confirmed;
            if (confirmed) session.visualContext = value;
            session.updated();
        }
        function clear(): void { store.clearHistory(); }
        function remove(key: string): void { store.removeHistory(key); }
        function hover(identity: string, value: bool): void { store.setHovered(Number(identity), value); }
    }
}
'''.replace('UUID_A', A).replace('UUID_B', B))
        env = {'HOME': str(root), 'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(runtime),
               'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_CACHE_HOME': str(root / 'cache'),
               'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software', 'NO_COLOR': '1',
               'DBUS_SESSION_BUS_ADDRESS': os.environ['DBUS_SESSION_BUS_ADDRESS']}
        log = root / 'log'
        with log.open('w') as output:
            process = subprocess.Popen(['quickshell', '-p', str(config)], env=env, stdout=output, stderr=output)
        try:
            def dbus(method, *args):
                return subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.freedesktop.Notifications',
                                       '--object-path', '/org/freedesktop/Notifications',
                                       '--method', 'org.freedesktop.Notifications.' + method, *map(str, args)],
                                      env=env, capture_output=True, text=True, timeout=5, check=True).stdout
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(log.read_text())
                try:
                    dbus('GetServerInformation')
                    break
                except subprocess.CalledProcessError:
                    time.sleep(0.05)
            else:
                raise RuntimeError('fixture server not ready: ' + log.read_text())
            def ipc(method, *args):
                result = subprocess.run(['quickshell', 'ipc', '-p', str(config), 'call', 'fixture', method, *map(str, args)],
                                        env=env, capture_output=True, text=True, timeout=5, check=True)
                return result.stdout.strip()
            def state():
                return json.loads(ipc('state'))
            def notify(hint=None, replace=0, duration=60000):
                hints = "{}" if hint is None else "{'x-agora-context': <'" + hint + "'>}"
                output = dbus('Notify', 'Fixture', replace, '', 'Synthetic test', 'No private content', '[]', hints, duration)
                return int(re.search(r'uint32 (\d+)', output)[1])
            def find(identity):
                return next(item for item in state()['history'] if item['id'] == identity)
            # Global/untagged notifications must never mark any session, even
            # before there are scoped history entries to populate the map.
            global_only = notify('global')
            assert not state()['unread'] and state()['redCases'] == 0, state()
            unknown_only = notify()
            assert not state()['unread'] and state()['redCases'] == 0, state()
            ipc('clear')
            background = notify('session:' + B)
            assert find(background)['unread'] and not find(background)['popup']
            assert state()['popups'] == 0
            assert state()['redCases'] == 1, 'session case must really render a red border'
            global_id = notify('global')
            assert find(global_id)['popup'] and state()['popups'] == 1
            assert state()['redCases'] == 1, 'global popup must preserve B attention without marking neutral/C'
            notify('global', global_id)
            notify(None, global_id)
            assert state()['redCases'] == 1, 'repeated global/untagged messages must not fan out badges'
            foreground = notify('session:' + A)
            assert find(foreground)['popup'] and state()['popups'] == 2
            before_red = state()['redCases']
            ipc('context', B, 'false')
            assert state()['redCases'] == before_red, 'pending switch must not flash extra red cases'
            assert not find(foreground)['unread'], 'unknown intermediate context must not mark the outgoing popup early'
            assert find(background)['unread'], 'unconfirmed context must not acknowledge'
            assert state()['popups'] == 1, 'scoped popups are masked while confirmation is pending'
            ipc('context', A, 'true')  # Simulate failed/cancelled selection, still on A.
            assert not find(foreground)['unread'] and find(foreground)['popup']
            assert find(background)['unread'] and state()['redCases'] == before_red
            ipc('context', B, 'false')
            assert state()['redCases'] == before_red
            ipc('context', B, 'true')
            assert not find(background)['unread'] and not find(background)['popup']
            assert find(foreground)['unread'] and not find(foreground)['popup'] and find(foreground)['live'], 'hiding must not close the native notification'
            assert state()['popups'] == 1, 'only global popup remains; no backlog replay'
            replaced = notify('session:' + A, background)
            assert replaced == background
            assert sum(item['id'] == background for item in state()['history']) == 1
            assert find(background)['unread']
            ipc('context', A, 'true')
            assert not find(background)['unread']
            ipc('context', B, 'true')
            notify('session:' + A, background)
            assert not find(background)['unread'], 'identical replacement is idempotent (no change signal from Quickshell)'
            expired = notify('session:' + A, duration=100)
            time.sleep(0.3)
            assert not find(expired)['live'] and find(expired)['unread']
            hovered = notify('global', duration=250)
            ipc('hover', hovered, 'true')
            time.sleep(0.4)
            assert find(hovered)['live'], 'hover pauses ordinary timeout'
            ipc('hover', hovered, 'false')
            time.sleep(0.4)
            assert not find(hovered)['live']
            dbus('CloseNotification', global_id)
            assert not find(global_id)['live']
            unknown = notify()
            assert find(unknown)['context'] == 'unknown' and find(unknown)['popup']
            orphan = notify('session:33333333-3333-3333-3333-333333333333')
            assert find(orphan)['orphan'] and find(orphan)['popup']
            neutral = notify('neutral')
            assert find(neutral)['unread'] and not find(neutral)['popup']
            ipc('context', 'neutral', 'true')
            assert not find(neutral)['unread'] and not find(neutral)['popup']
            ipc('remove', find(background)['key'])
            assert all(item['id'] != background for item in state()['history'])
            subprocess.run([str(Path(__file__).resolve().parents[2] / 'runtime/target/release/agora-notify'),
                            'send', '--context', 'session:' + A, '--app-name', 'Helper fixture',
                            'Synthetic helper test', 'Literal private-bus payload'], env=env, check=True, timeout=15)
            emitted = state()['history'][0]
            assert emitted['appName'] == 'Helper fixture' and emitted['context'] == 'session:' + A
            assert emitted['unread'] and not emitted['popup']
            ipc('clear')
            assert not state()['history'] and not state()['unread'] and state()['popups'] == 0
            assert state()['redCases'] == 0
            # Rendering is absent offscreen, but native lifetimes/Notify replacements run.
            text = log.read_text()
            assert 'ReferenceError' not in text and 'TypeError' not in text, text
            print('Private D-Bus: real notifications, hints, replacements, expiry, masking, entry and history passed.')
        except Exception:
            print(log.read_text(), file=sys.stderr)
            raise
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=10)


if __name__ == '__main__':
    if sys.argv[1:] == ['--inside']:
        inside()
    else:
        result = subprocess.run(['dbus-run-session', '--', '/usr/bin/python3', str(Path(__file__).resolve()), '--inside'],
                                env={'PATH': '/usr/bin:/bin'}, check=False, timeout=45)
        sys.exit(result.returncode)
