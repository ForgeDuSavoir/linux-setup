#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TMP="$(mktemp -d -t photocraft-ai-test-XXXXXX)"
cleanup() {
    if [[ -f "$TMP/app-pid" ]]; then kill "$(< "$TMP/app-pid")" 2>/dev/null || true; fi
    rm -rf -- "$TMP"
}
trap cleanup EXIT
mkdir -p "$TMP/bin" "$TMP/home/.local/share/photocraft-ai/.pi" "$TMP/project with spaces"
printf '{}\n' > "$TMP/home/.local/share/photocraft-ai/.pi/mcp.json"
printf 'mock document\n' > "$TMP/project with spaces/my photo.pcraft"

cat > "$TMP/bin/photocraft" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$TEST_APP_ARGS"
echo "$$" > "$TEST_APP_PID"
printf 'test token\n' > "$TEST_TOKEN"
touch "$TEST_LISTENER"
trap 'exit 0' TERM
while true; do sleep 1; done
EOF
for tool in photocraft-cli pi notify-send; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/bin/$tool"
done
cat > "$TMP/bin/pgrep" <<'EOF'
#!/usr/bin/env bash
[[ "${TEST_EXISTING:-0}" == 1 ]]
EOF
cat > "$TMP/bin/ss" <<'EOF'
#!/usr/bin/env bash
if [[ -e "$TEST_LISTENER" ]]; then echo LISTEN; fi
EOF
cat > "$TMP/bin/kitty" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$TEST_KITTY_ARGS"
EOF
chmod +x "$TMP/bin/"*
export HOME="$TMP/home" XDG_STATE_HOME="$TMP/home/.local/state" PATH="$TMP/bin:$PATH" TEST_LISTENER="$TMP/listener" \
    TEST_TOKEN="$TMP/home/.local/state/photocraft/control.token" TEST_APP_ARGS="$TMP/app-args" \
    TEST_KITTY_ARGS="$TMP/kitty-args" TEST_APP_PID="$TMP/app-pid"
project="$TMP/project with spaces/my photo.pcraft"
if "$SCRIPT_DIR/launch_photocraft_ai.sh" "$TMP/missing.pcraft" > "$TMP/out" 2>&1; then
    echo 'Missing document was accepted' >&2; exit 1
fi
TEST_EXISTING=1; export TEST_EXISTING
if "$SCRIPT_DIR/launch_photocraft_ai.sh" "$project" > "$TMP/out" 2>&1; then
    echo 'Existing PhotoCraft window was ignored' >&2; exit 1
fi
unset TEST_EXISTING
"$SCRIPT_DIR/launch_photocraft_ai.sh" "$project"
python3 - "$TMP/app-args" "$TMP/kitty-args" "$project" "$TMP/home" <<'PY'
import pathlib, sys
app, kitty, project = (pathlib.Path(sys.argv[1]).read_text().splitlines(), pathlib.Path(sys.argv[2]).read_text().splitlines(), sys.argv[3])
assert app[:3] == ['--new-instance','--control','7878'], app
assert '--control-token-file' in app and '--automation-read-root' in app, app
assert app[app.index('--automation-read-root') + 1] == str(pathlib.Path(project).parent), app
assert app[app.index('--automation-write-root') + 1] == str(pathlib.Path(project).parent), app
assert app[-2:] == ['--',project], app
assert '--directory' in kitty and '--detach' in kitty, kitty
assert '--session-id' in kitty and '--name' in kitty, kitty
assert any(project in arg and 'skill photocraft' in arg for arg in kitty), kitty
sid = kitty[kitty.index('--session-id') + 1]
sidecar = pathlib.Path(project).parent / f'.{pathlib.Path(project).name}.pi-session'
assert sidecar.read_text().strip() == sid and sidecar.stat().st_mode & 0o777 == 0o600
pi_dir = pathlib.Path(sys.argv[4]) / '.local/share/photocraft-ai'
sdir = pathlib.Path(sys.argv[4]) / '.pi/agent/sessions' / ('--' + str(pi_dir).lstrip('/').replace('/', '-') + '--')
sdir.mkdir(parents=True)
import json
with (sdir / ('2026-01-01T00-00-00-000Z_' + sid + '.jsonl')).open('w') as out:
    out.write(json.dumps({'type':'session','version':3,'id':sid,'cwd':str(pi_dir)}) + '\n')
PY
if "$SCRIPT_DIR/launch_photocraft_ai.sh" "$project" > "$TMP/out" 2>&1; then
    echo 'Control port collision was ignored' >&2; exit 1
fi
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"
"$SCRIPT_DIR/launch_photocraft_ai.sh" "$project"
python3 - "$TMP/kitty-args" "$project" <<'PY'
import pathlib,sys
args=pathlib.Path(sys.argv[1]).read_text().splitlines(); p=pathlib.Path(sys.argv[2]); sid=(p.parent/f'.{p.name}.pi-session').read_text().strip()
assert args[args.index('--session-id') + 1] == sid and '--name' not in args and not any('document ouvert :' in a for a in args), args
PY
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"
mv "$TMP/project with spaces" "$TMP/moved folder with spaces"
project="$TMP/moved folder with spaces/my photo.pcraft"
"$SCRIPT_DIR/launch_photocraft_ai.sh" "$project"
python3 - "$TMP/kitty-args" "$project" <<'PY'
import pathlib,sys
args=pathlib.Path(sys.argv[1]).read_text().splitlines(); p=pathlib.Path(sys.argv[2]); sid=(p.parent/f'.{p.name}.pi-session').read_text().strip()
assert args[args.index('--session-id') + 1] == sid and '--name' not in args, args
PY
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"
"$SCRIPT_DIR/launch_photocraft_ai.sh"
python3 - "$TMP/app-args" "$TMP/kitty-args" "$TMP/home" <<'PY'
import pathlib,sys
app,pi,home=(pathlib.Path(sys.argv[1]).read_text().splitlines(),pathlib.Path(sys.argv[2]).read_text().splitlines(),pathlib.Path(sys.argv[3]))
assert '--' not in app and app[app.index('--automation-read-root')+1] == str(home/'Pictures/PhotoCraft-AI'),app
assert '--session-id' not in pi and '--name' in pi,pi
PY
echo '✓ PhotoCraft launcher tests passed (new, resume, moved folder, empty, port collision, existing window).'
