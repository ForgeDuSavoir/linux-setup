#!/usr/bin/env python3
"""Open Pi in the active session's current project directory, without a picker."""
import json
import os
import re
from pathlib import Path
import tomllib
import subprocess
import sys

MANAGER = Path.home() / '.local/bin/session-manager'
TERMINAL = Path.home() / '.local/bin/launch-terminal-command'
NOTIFY = Path.home() / '.local/bin/agora-notify'
def workflow_config():
    root = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    if not root.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    return root / 'agora-workflow/config.toml'


def agora_root():
    config = workflow_config()
    try:
        with config.open('rb') as file:
            settings = tomllib.load(file)
    except FileNotFoundError as error:
        raise ValueError(f'configure agora_root in {config} before opening neutral Pi') from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f'invalid TOML in {config}') from error
    value = settings.get('agora_root')
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError(f'agora_root must be an absolute directory path in {config}')
    path = Path(value)
    if not path.is_dir():
        raise ValueError(f'configured Agora directory does not exist: {path}')
    return path


def terminal_command(path):
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError('working directory is unavailable')
    return [str(TERMINAL), str(path), 'pi']


def query(*args):
    result = subprocess.run([str(MANAGER), '--json', *args], check=True,
                            capture_output=True, text=True, timeout=35)
    return json.loads(result.stdout)


def launch_plan():
    state = query('session', 'list')
    active = state.get('active_session_id')
    session = next((item for item in state['sessions'] if item['id'] == active), None)
    if session is None:
        if active is not None:
            raise ValueError('active session is missing from the session list')
        return terminal_command(agora_root()), 'neutral'
    source = session.get("source")
    if source == {"kind": "neutral"}:
        return terminal_command(agora_root()), 'session:' + active
    if (not isinstance(source, dict) or set(source) != {"kind", "project_name"}
            or source["kind"] != "project" or not isinstance(source["project_name"], str)):
        raise ValueError("invalid v3 session source")
    projects = query('project', 'list')['projects']
    project = next((item for item in projects if item['name'] == source['project_name']), None)
    if project is None:
        raise ValueError('active session project is no longer available')
    path = Path(project['path'])
    # An active session never falls back to Agora if its project is missing.
    return terminal_command(path), 'session:' + active


def launch_command():
    # Keep the routing interface used by isolated callers; main adds launch metadata.
    return launch_plan()[0]


def capture_context(expected, env):
    try:
        result = subprocess.run([str(NOTIFY), 'capture'], env=env, check=True,
                                capture_output=True, text=True, timeout=2)
        value = result.stdout.strip()
        valid = value in ('global', 'neutral') or re.fullmatch(
            r'session:[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value)
        if valid and (expected is None or value == expected):
            return value
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 'global'  # Never guess the originating UUID from a project path/name.


def main():
    if sys.argv[1:] == ['--agora']:
        command, expected = terminal_command(agora_root()), None
    elif not sys.argv[1:]:
        command, expected = launch_plan()
    else:
        raise ValueError('usage: session-pi [--agora]')
    env = os.environ.copy()
    # A new terminal has a new launch origin; do not reuse the caller's job tag.
    env.pop('AGORA_NOTIFICATION_CONTEXT', None)
    context = capture_context(expected, env)
    env['AGORA_NOTIFICATION_CONTEXT'] = context
    # Command arguments survive terminal-server reuse even when its environment does not.
    command = [*command[:2], 'env', 'AGORA_NOTIFICATION_CONTEXT=' + context, *command[2:]]
    subprocess.run(command, check=True, env=env)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'Session Pi launcher: {error}', file=sys.stderr)
        sys.exit(1)
