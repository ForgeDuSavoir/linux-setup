#!/usr/bin/env python3
"""Capture a work context once, or emit a standard notification with that context."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def validate_context(value):
    if value in ('global', 'neutral') or re.fullmatch(r'session:[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value):
        return value
    raise ValueError('context must be global, neutral or session:<canonical UUID>')


def capture():
    inherited = os.environ.get('AGORA_NOTIFICATION_CONTEXT')
    if inherited is not None:
        return validate_context(inherited)
    client = Path.home() / '.local/bin/session-desktop'
    result = subprocess.run([str(client), 'status'], check=True, capture_output=True, text=True, timeout=35)
    state = json.loads(result.stdout)
    if not isinstance(state, dict):
        raise ValueError('invalid desktop status response')
    if state.get('context_confirmed') is not True:
        raise ValueError('desktop context is not confirmed; choose an explicit context or global')
    displayed = state.get('displayed_context')
    if displayed == 'neutral' and state.get('active_session_id') is None:
        return 'neutral'
    if displayed != state.get('active_session_id') or not any(s['id'] == displayed for s in state.get('sessions', [])):
        raise ValueError('inconsistent session context')
    return validate_context('session:' + str(displayed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('capture', help='print inherited context or confirmed desktop context; never emit')
    send = commands.add_parser('send', help='emit; never look up the active session at completion time')
    context = send.add_mutually_exclusive_group()
    context.add_argument('--context')
    context.add_argument('--global', dest='global_context', action='store_true')
    send.add_argument('-u', '--urgency', choices=('low', 'normal', 'critical'), default='normal')
    send.add_argument('-a', '--app-name', default='Agora scripts')
    send.add_argument('-t', '--expire-time', type=int)
    send.add_argument('-r', '--replace-id', type=int)
    send.add_argument('summary')
    send.add_argument('body', nargs='?', default='')
    args = parser.parse_args(argv)
    if args.command == 'capture':
        print(capture())
        return 0
    # Missing context is deliberately global, not a late selection snapshot.
    value = 'global' if args.global_context else (args.context if args.context is not None else os.environ.get('AGORA_NOTIFICATION_CONTEXT', 'global'))
    value = validate_context(value)
    command = ['notify-send', '--hint', 'string:x-agora-context:' + value,
               '--app-name', args.app_name, '--urgency', args.urgency]
    if args.expire_time is not None:
        command += ['--expire-time', str(args.expire_time)]
    if args.replace_id is not None:
        if not 0 <= args.replace_id <= 4294967295:
            raise ValueError('replacement ID must be an unsigned 32-bit integer')
        command += ['--replace-id', str(args.replace_id)]
    command += ['--', args.summary, args.body]
    subprocess.run(command, check=True, timeout=10)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'agora-notify: {error}', file=sys.stderr)
        sys.exit(1)
