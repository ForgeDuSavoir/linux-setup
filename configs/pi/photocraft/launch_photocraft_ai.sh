#!/usr/bin/env bash

set -euo pipefail

fail() {
    echo "✗ $1" >&2
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -u critical 'PhotoCraft + assistant' "$1" || true
    fi
    exit 1
}

if (( $# > 1 )); then
    echo 'Usage: photocraft-ai [document.pcraft]' >&2
    exit 2
fi

for tool in photocraft photocraft-cli pi kitty ss flock python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "Required command missing: $tool"
    fi
done

PROJECT=""
if (( $# == 1 )); then
    if [[ ! -f "$1" || "$1" != *.pcraft ]]; then
        fail "PhotoCraft document not found: $1"
    fi
    PROJECT="$(realpath -e -- "$1")"
fi

# Do not attach Pi to a different or uncontrolled PhotoCraft window.
if pgrep -u "$(id -u)" -x photocraft >/dev/null 2>&1; then
    fail 'Close the existing PhotoCraft window before opening PhotoCraft + assistant.'
fi
if [[ -n "$(ss -H -lnt '( sport = :7878 )')" ]]; then
    fail 'Control port 7878 is already in use; refusing to connect to an unknown process.'
fi

SESSION_DIR="${HOME}/.local/share/photocraft-ai"
SESSION_HELPER="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/photocraft-ai-session"
if [[ ! -f "$SESSION_DIR/.pi/mcp.json" || ! -x "$SESSION_HELPER" ]]; then
    fail 'PhotoCraft Pi configuration not installed. Run the linux-setup PhotoCraft installer.'
fi
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/photocraft"
TOKEN_FILE="$STATE_DIR/control.token"
umask 077
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [[ -e "$TOKEN_FILE" ]]; then
    chmod 600 "$TOKEN_FILE"
fi
exec 9> "$STATE_DIR/launch.lock"
if ! flock -n 9; then
    fail 'Another PhotoCraft + assistant launch is already in progress.'
fi

if [[ -n "$PROJECT" ]]; then
    if ! SESSION_INFO="$("$SESSION_HELPER" "$PROJECT" "$SESSION_DIR")"; then
        fail 'Could not resolve the document conversation.'
    fi
    read -r SESSION_ID SESSION_STATE <<< "$SESSION_INFO"
    ROOT="$(dirname -- "$PROJECT")"
else
    ROOT="${HOME}/Pictures/PhotoCraft-AI"
    mkdir -p "$ROOT"
fi

# Restrict live automation to the document's directory. The headless server
# keeps its separate, fixed PhotoCraft-AI workspace.
APP_ARGS=(photocraft --new-instance --control 7878 --control-token-file "$TOKEN_FILE"
    --automation-read-root "$ROOT" --automation-write-root "$ROOT")
if [[ -n "$PROJECT" ]]; then
    APP_ARGS+=(-- "$PROJECT")
fi
nohup "${APP_ARGS[@]}" >> "$STATE_DIR/photocraft-ai.log" 2>&1 < /dev/null 9>&- &
PHOTOCRAFT_PID=$!

ready=false
for ((i = 0; i < 120; i++)); do
    if ! kill -0 "$PHOTOCRAFT_PID" 2>/dev/null; then
        fail "PhotoCraft exited early; see $STATE_DIR/photocraft-ai.log"
    fi
    if [[ -n "$(ss -H -lnt '( sport = :7878 )')" && -s "$TOKEN_FILE" ]]; then
        ready=true
        break
    fi
    sleep 0.25
done
if [[ "$ready" != true ]]; then
    kill "$PHOTOCRAFT_PID" 2>/dev/null || true
    fail "PhotoCraft did not open its control port; see $STATE_DIR/photocraft-ai.log"
fi

if [[ -n "$PROJECT" ]]; then
    TITLE="PhotoCraft - $(basename -- "$PROJECT")"
    REQUEST="Aide-moi à apprendre PhotoCraft avec le document ouvert : $PROJECT. Utilise le skill photocraft. Commence par inspecter l'interface et le document en lecture seule, puis demande-moi ce que je souhaite apprendre. Ne modifie, n'enregistre et n'exporte rien sans mon accord."
    if [[ "$SESSION_STATE" == existing ]]; then
        PI_ARGS=(pi --session-id "$SESSION_ID")
    else
        PI_ARGS=(pi --session-id "$SESSION_ID" --name "$TITLE" "$REQUEST")
    fi
else
    PI_ARGS=(pi --name 'PhotoCraft - assistant'
        "Aide-moi à apprendre PhotoCraft. Utilise le skill photocraft. Commence par inspecter l'interface en lecture seule, puis demande-moi ce que je souhaite apprendre. Ne modifie, n'enregistre et n'exporte rien sans mon accord.")
fi

if ! kitty --detach --directory "$SESSION_DIR" --title 'PhotoCraft + assistant' \
    "${PI_ARGS[@]}" 9>&-; then
    kill "$PHOTOCRAFT_PID" 2>/dev/null || true
    fail 'Could not start Pi; closing the PhotoCraft instance started here.'
fi
