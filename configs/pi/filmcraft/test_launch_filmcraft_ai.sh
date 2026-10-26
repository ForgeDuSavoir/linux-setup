#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TMP="$(mktemp -d)"
cleanup() {
    if [[ -f "$TMP/app-pid" ]]; then
        kill "$(< "$TMP/app-pid")" 2>/dev/null || true
    fi
    rm -rf "$TMP"
}
trap cleanup EXIT
mkdir -p "$TMP/bin" "$TMP/home/.local/share/filmcraft-ai/.pi" "$TMP/project with spaces"
printf '{}\n' > "$TMP/home/.local/share/filmcraft-ai/.pi/mcp.json"
printf 'test project\n' > "$TMP/project with spaces/obs cut.fcproj"

cat > "$TMP/bin/filmcraft" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$TEST_FILMCRAFT_ARGS"
echo "$$" > "$TEST_APP_PID"
touch "$TEST_LISTENER"
trap 'rm -f "$TEST_LISTENER"; exit 0' TERM
while true; do sleep 1; done
EOF
for tool in filmcraft-cli pi notify-send; do
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
export HOME="$TMP/home" PATH="$TMP/bin:$PATH" TEST_LISTENER="$TMP/listener" \
    TEST_KITTY_ARGS="$TMP/kitty-args" TEST_FILMCRAFT_ARGS="$TMP/filmcraft-args" TEST_APP_PID="$TMP/app-pid"

if "$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/missing.fcproj" > "$TMP/out" 2>&1; then
    echo 'Missing project was accepted' >&2; exit 1
fi
TEST_EXISTING=1
export TEST_EXISTING
if "$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/project with spaces/obs cut.fcproj" > "$TMP/out" 2>&1; then
    echo 'Existing FilmCraft window was ignored' >&2; exit 1
fi
unset TEST_EXISTING
"$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/project with spaces/obs cut.fcproj"
python - "$TMP/filmcraft-args" "$TMP/kitty-args" "$TMP/project with spaces/obs cut.fcproj" "$TMP/home" <<'PY'
import json, pathlib, sys
app, kitty, project = (pathlib.Path(sys.argv[1]).read_text().splitlines(), pathlib.Path(sys.argv[2]).read_text().splitlines(), sys.argv[3])
home = pathlib.Path(sys.argv[4])
assert app == ['--control', '9876', project], app
assert '--directory' in kitty and '--detach' in kitty, kitty
assert any(project in arg for arg in kitty), kitty
assert '--session-id' in kitty and '--name' in kitty, kitty
sid = kitty[kitty.index('--session-id') + 1]
assert (pathlib.Path(project).parent / f'.{pathlib.Path(project).name}.pi-session').read_text().strip() == sid
pi_dir = home / '.local/share/filmcraft-ai'
session_dir = home / '.pi/agent/sessions' / ('--' + str(pi_dir).lstrip('/').replace('/', '-') + '--')
session_dir.mkdir(parents=True)
with (session_dir / ('2026-01-01T00-00-00-000Z_' + sid + '.jsonl')).open('w') as out:
    out.write(json.dumps({'type':'session','version':3,'id':sid,'cwd':str(pi_dir)}) + '\n')
    out.write(json.dumps({'type':'message','message':{'role':'user','content':[{'type':'text','text':kitty[-1]}]}}) + '\n')
PY
if "$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/project with spaces/obs cut.fcproj" > "$TMP/out" 2>&1; then
    echo 'Control port collision was ignored' >&2; exit 1
fi
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"
"$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/project with spaces/obs cut.fcproj"
python - "$TMP/kitty-args" "$TMP/project with spaces/obs cut.fcproj" <<'PY'
import pathlib, sys
args = pathlib.Path(sys.argv[1]).read_text().splitlines()
sid = (pathlib.Path(sys.argv[2]).parent / f'.{pathlib.Path(sys.argv[2]).name}.pi-session').read_text().strip()
assert args[args.index('--session-id') + 1] == sid
assert '--name' not in args and not any('projet ouvert :' in arg for arg in args), args
PY
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"
mv "$TMP/project with spaces" "$TMP/project moved with spaces"
"$SCRIPT_DIR/launch_filmcraft_ai.sh" "$TMP/project moved with spaces/obs cut.fcproj"
python - "$TMP/kitty-args" "$TMP/project moved with spaces/obs cut.fcproj" <<'PY'
import pathlib, sys
args = pathlib.Path(sys.argv[1]).read_text().splitlines()
sid = (pathlib.Path(sys.argv[2]).parent / f'.{pathlib.Path(sys.argv[2]).name}.pi-session').read_text().strip()
assert args[args.index('--session-id') + 1] == sid and '--name' not in args, args
PY
kill "$(< "$TEST_APP_PID")" 2>/dev/null || true
rm -f "$TEST_LISTENER"

# A project created with the previous launcher had two separate Pi sessions.
# The earliest one must win instead of silently continuing the latest one.
python - "$TMP/home" "$TMP/legacy project.fcproj" <<'PY'
import json, pathlib, sys
home, project = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); project.write_text('{}')
pi_dir = home / '.local/share/filmcraft-ai'
sdir = home / '.pi/agent/sessions' / ('--' + str(pi_dir).lstrip('/').replace('/', '-') + '--')
for date, sid in [('2025-01-01','oldest-session'), ('2025-02-01','later-session')]:
    f = sdir / (date + 'T00-00-00-000Z_' + sid + '.jsonl')
    with f.open('w') as out:
        out.write(json.dumps({'type':'session','id':sid,'cwd':str(pi_dir)}) + '\n')
        out.write(json.dumps({'type':'message','message':{'role':'user','content':[{'type':'text','text':f'Aide-moi à apprendre FilmCraft avec le projet ouvert : {project}. Utilise le skill filmcraft.'}]}}) + '\n')
PY
result="$("$SCRIPT_DIR/filmcraft-ai-session" "$TMP/legacy project.fcproj" "$TMP/home/.local/share/filmcraft-ai")"
[[ "$result" == 'oldest-session existing' ]]
echo '✓ FilmCraft launcher tests passed (first session, reopening, folder move, legacy first session, port collisions).'
