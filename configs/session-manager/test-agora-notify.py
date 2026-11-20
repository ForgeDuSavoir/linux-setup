#!/usr/bin/env python3
"""Notification helper and asynchronous script tests; no real notifications/editors."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SETUP = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('AGORA_NOTIFY_TEST_BIN', str(SETUP / 'runtime/target/release/agora-notify')))
assert SOURCE.is_file(), 'Build the Rust notification helper first'
A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'

with tempfile.TemporaryDirectory(prefix='agora-notify-') as directory:
    root = Path(directory)
    binary = root / '.local/bin'
    binary.mkdir(parents=True)
    helper = binary / 'agora-notify'
    shutil.copyfile(SOURCE, helper)
    helper.chmod(0o700)
    log = root / 'notifications'
    status_file = root / 'status'
    calls_file = root / 'captures'
    status = binary / 'session-desktop'
    status.write_text('''#!/usr/bin/python3
import os,pathlib
with open(os.environ['CAPTURES'],'a') as f: f.write('status\\n')
print(pathlib.Path(os.environ['STATUS']).read_text())
''')
    notify = binary / 'notify-send'
    notify.write_text('''#!/usr/bin/python3
import json,os,sys
with open(os.environ['NOTIFICATIONS'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
''')
    status.chmod(0o700)
    notify.chmod(0o700)
    env = {'HOME': str(root), 'PATH': f'{binary}:/usr/bin:/bin', 'STATUS': str(status_file),
           'CAPTURES': str(calls_file), 'NOTIFICATIONS': str(log)}
    def set_status(identity):
        status_file.write_text(json.dumps({'active_session_id': identity, 'displayed_context': identity or 'neutral',
                                          'context_confirmed': True, 'sessions': [{'id': identity}] if identity else []}))
    def run(*args, extra=None, check=True):
        return subprocess.run([str(helper), *args], env={**env, **(extra or {})},
                              capture_output=True, text=True, check=check)
    set_status(A)
    captured = run('capture').stdout.strip()
    assert captured == 'session:' + A
    set_status(B)
    literal = 'A message with spaces; $(never-run)'
    run('send', '--context', captured, '--', literal, 'Body "quoted"')
    sent = json.loads(log.read_text().splitlines()[-1])
    assert sent[-2:] == [literal, 'Body "quoted"']
    assert sent[1] == 'string:x-agora-context:session:' + A
    assert calls_file.read_text().splitlines() == ['status'], 'send must never recapture context'
    assert run('capture', extra={'AGORA_NOTIFICATION_CONTEXT': captured}).stdout.strip() == captured
    run('send', '--global', 'System operation', extra={'AGORA_NOTIFICATION_CONTEXT': captured})
    assert json.loads(log.read_text().splitlines()[-1])[1] == 'string:x-agora-context:global'
    run('send', 'Unscoped operation')
    assert json.loads(log.read_text().splitlines()[-1])[1] == 'string:x-agora-context:global'
    for invalid in ('', 'session:not-a-uuid', '../bad', 'unknown'):
        before = log.read_text()
        assert run('send', '--context', invalid, 'Reject me', check=False).returncode != 0
        assert log.read_text() == before
    set_status(None)
    assert run('capture').stdout.strip() == 'neutral'
    status_file.write_text('{"context_confirmed":false}')
    assert run('capture', check=False).returncode != 0

    # Real pre-edit wrapper, fake auto-editor failure after changing selection.
    auto = binary / 'auto-editor'
    auto.write_text('''#!/usr/bin/python3
import json,os,pathlib
B='22222222-2222-2222-2222-222222222222'
pathlib.Path(os.environ['STATUS']).write_text(json.dumps({'active_session_id':B,'displayed_context':B,'context_confirmed':True,'sessions':[{'id':B}]}))
raise SystemExit(1)
''')
    auto.chmod(0o700)
    video = root / 'fixture.mkv'
    video.write_bytes(b'not-real-video')
    set_status(A)
    result = subprocess.run(['/bin/bash', str(SETUP / 'scripts/pre-edit/pre-edit.sh'), str(video)],
                            env=env, cwd=root, capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(status_file.read_text())['active_session_id'] == B
    assert json.loads(log.read_text().splitlines()[-1])[1] == 'string:x-agora-context:session:' + A

    before_captures = calls_file.read_text()
    result = subprocess.run(['/bin/bash', str(SETUP / 'scripts/pre-edit/pre-edit.sh'), str(video)],
                            env={**env, 'AGORA_NOTIFICATION_CONTEXT': captured}, cwd=root,
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert calls_file.read_text() == before_captures, 'inherited origin must not be queried again by a child'
    assert json.loads(log.read_text().splitlines()[-1])[1] == 'string:x-agora-context:session:' + A

    # Both recording stop hooks propagate the earlier recording-start snapshot.
    preedit = binary / 'pre-edit'
    preedit.write_text('#!/bin/sh\n[ "$AGORA_NOTIFICATION_CONTEXT" = "session:' + A + '" ] || exit 9\nexit 0\n')
    preedit.chmod(0o700)
    for name in ('obs-post-record', 'obs-post-record-gaming'):
        recording = root / (name + '.mkv')
        recording.write_bytes(b'fixture')
        subprocess.run(['/bin/bash', str(SETUP / f'configs/obs/scripts-sh/{name}.sh'), str(recording), captured],
                       env=env, cwd=root, check=True, capture_output=True, text=True)
        assert json.loads(log.read_text().splitlines()[-1])[1] == 'string:x-agora-context:session:' + A

    # Validate actual OBS Lua hooks with a fake OBS API and no os.execute/io.popen.
    lua_test = root / 'test.lua'
    lua_test.write_text('''local A = "session:11111111-1111-1111-1111-111111111111"
local B = "session:22222222-2222-2222-2222-222222222222"
local selected = A
local captures = 0
local executed = {}
obslua = {OBS_FRONTEND_EVENT_RECORDING_STARTED=1, OBS_FRONTEND_EVENT_RECORDING_STOPPED=2,
 obs_frontend_get_last_recording=function() return "/fixture/with 'quote' and $(literal).mkv" end,
 obs_frontend_add_event_callback=function() end}
io.popen = function(command)
 assert(command:find("agora%-notify capture"))
 captures = captures + 1
 return {read=function() return selected .. "\\n" end, close=function() return true end}
end
os.execute = function(command) table.insert(executed, command); return 0 end
dofile(arg[1])
on_event(1)
selected = B
on_event(2)
assert(captures == 1)
assert(executed[1]:find(A, 1, true) and not executed[1]:find(B, 1, true))
assert(executed[1]:find("'\\\\''", 1, true), "file paths must be shell-quoted")
on_event(2)
assert(captures == 1 and executed[2]:find("'global'", 1, true))
''')
    for name in ('obs-post-record', 'obs-post-record-gaming'):
        subprocess.run(['lua', str(lua_test), str(SETUP / f'configs/obs/scripts-lua/{name}.lua')], check=True)

    lua_dir = root / 'obs-lua'
    lua_dir.mkdir()
    subprocess.run(['/bin/bash', str(SETUP / 'configs/obs/configure_obs.sh'), '--scripts-only'],
                   env={**env, 'OBS_LUA_DIR': str(lua_dir)}, check=True, capture_output=True, text=True)
    assert not (root / '.config/obs-studio').exists(), 'script-only installation must not replace OBS settings'
    for name in ('obs-post-record', 'obs-post-record-gaming'):
        assert (lua_dir / (name + '.lua')).read_bytes() == (SETUP / f'configs/obs/scripts-lua/{name}.lua').read_bytes()
        assert (binary / (name + '.sh')).is_file()

print('Notification helper and real script wrappers: capture-once, literal arguments, global mode and OBS start/stop passed.')
