#!/usr/bin/env python3
"""Initialize one empty Neutral session per Hyprland instance, then start the bar.

Desktop policy only: the persistent core is reset through its existing API, not
by deleting state files. Never run this as a generic daemon/Quickshell restart hook.
"""
import fcntl
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
DESKTOP = HERE / 'session-desktop.py'
if not DESKTOP.exists():
    DESKTOP = HERE / 'session-desktop'
loader = importlib.machinery.SourceFileLoader('startup_desktop', str(DESKTOP))
spec = importlib.util.spec_from_loader(loader.name, loader)
desktop = importlib.util.module_from_spec(spec)
loader.exec_module(desktop)
columns = desktop.columns


class AlreadyAttempted(RuntimeError):
    """An incomplete attempt must not replay potentially committed requests."""


def signature():
    value = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    if not value or len(value) > 512:
        raise RuntimeError('missing/invalid Hyprland instance signature')
    return value


def marker_path():
    return columns.RUNTIME / 'session-startup.json'


def read_marker():
    path = marker_path()
    if path.is_symlink():
        raise RuntimeError('symlinked startup marker')
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    if (not isinstance(value, dict) or value.get('version') != 1
            or not isinstance(value.get('instance'), str)
            or value.get('phase') not in ('initializing', 'failed', 'ready', 'deferred')):
        raise RuntimeError('invalid startup marker; inspect it before retrying')
    return value


def write_marker(instance, phase, **fields):
    path = marker_path()
    if path.is_symlink():
        raise RuntimeError('symlinked startup marker')
    fd, name = tempfile.mkstemp(prefix='.session-startup-', dir=columns.RUNTIME)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'version': 1, 'instance': instance, 'phase': phase, **fields}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def defer_current_locked():
    """Installation only, under the workspace lock: protect the current login."""
    instance = signature()
    previous = read_marker()
    if previous is None or previous['instance'] != instance:
        write_marker(instance, 'deferred')


def wait_for_core(seconds=10):
    deadline = time.monotonic() + seconds
    while True:
        try:
            return desktop.request('list', timeout=2)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            if isinstance(error, RuntimeError) and str(error) != 'transport.unavailable':
                raise
            if time.monotonic() >= deadline:
                raise RuntimeError('Session Manager unavailable at graphical startup') from error
            time.sleep(0.1)


def session_ids(snapshot):
    rows = snapshot.get('sessions')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError('invalid startup session list')
    ids = [row.get('id') for row in rows]
    if (any(not isinstance(sid, str) or not sid for sid in ids)
            or len(set(ids)) != len(ids)
            or snapshot.get('active_session_id') not in [None, *ids]):
        raise RuntimeError('invalid startup session identities')
    return ids


def initialize():
    """Return True for a first attempt; repeat calls in the same login are no-ops."""
    instance = signature()
    columns.RUNTIME.mkdir(parents=True, exist_ok=True)
    with (columns.RUNTIME / 'workspace-columns.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = read_marker()
        if previous and previous['instance'] == instance:
            if previous['phase'] in ('ready', 'deferred'):
                return False
            raise AlreadyAttempted('startup already attempted; inspect state instead of replaying requests')
        # A crash/uncertain acknowledgement cannot silently cause a second reset.
        write_marker(instance, 'initializing')
        try:
            instances = columns.query('instances')
            if len(instances) != 1 or instances[0].get('instance') != instance:
                raise RuntimeError('startup requires exactly this one Hyprland instance')
            special = desktop.visible_scratchpad()  # Retain the single-monitor policy.
            clients = columns.query('clients')
            if any(c.get('workspace', {}).get('name', '').startswith('special:sm-') for c in clients):
                raise RuntimeError('scoped scratchpad windows already exist; startup reset refused')
            before = wait_for_core()
            ids = session_ids(before)
            existing = {w['id'] for w in columns.query('workspaces') if w['id'] > 0}
            existing.add(columns.active())
            state = columns.validate(columns.project_state(None, existing))
            backup = Path(tempfile.mkdtemp(prefix='session-startup-backup-', dir=columns.RUNTIME))
            if columns.STATE.exists():
                shutil.copy2(columns.STATE, backup / 'workspace-state.json')
            (backup / 'core-before.json').write_text(json.dumps(before))
            (backup / 'core-before.json').chmod(0o600)
            # Old IDs can be reused by the new compositor: never inherit old UUID owners.
            columns.save(state)
            desktop.hide_scratchpad(special)
            for sid in ids:
                reply = desktop.request('stop', sid)  # Intentional new-login exception to UI stop guards.
                if reply.get('stopped_session_id') != sid:
                    raise RuntimeError('invalid startup stop acknowledgement')
            remaining = desktop.request('list')
            if session_ids(remaining) or remaining.get('active_session_id') is not None:
                raise RuntimeError('sessions changed during startup; refusing further resets')
            created = desktop.request('start', '--neutral').get('session', {})
            sid = created.get('id')
            if not isinstance(sid, str) or not sid:
                raise RuntimeError('invalid startup neutral acknowledgement')
            target = columns.fresh_workspace(state, sid)
            columns.select(state, target, fresh=True)
            after = desktop.request('list')
            if (session_ids(after) != [sid] or after.get('active_session_id') != sid
                    or after['sessions'][0].get('source') != {'kind': 'neutral'}
                    or after['sessions'][0].get('number') != 1
                    or columns.active() != target or desktop.visible_scratchpad()):
                raise RuntimeError('initial neutral session/desktop not confirmed')
            write_marker(instance, 'ready', session_id=sid)
        except Exception:
            write_marker(instance, 'failed')
            raise
    return True


def main():
    if len(sys.argv) != 1:
        raise SystemExit('usage: session-startup (Hyprland startup only)')
    try:
        if not initialize():
            return 0  # No second bar and no reset after config/shell reload or repeated event.
    except AlreadyAttempted as error:
        print(f'session-startup: {error}', file=sys.stderr)
        return 1
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        message = f'session-startup failed: {error}; use the menu to recover; no automatic retry'
        print(message, file=sys.stderr)
        try:
            subprocess.run(['logger', '-t', 'session-startup', '--', message], timeout=2, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
        # Still expose the menu on first-attempt failure, rather than losing the bar.
    os.execvp('quickshell', ['quickshell'])


if __name__ == '__main__':
    sys.exit(main())
