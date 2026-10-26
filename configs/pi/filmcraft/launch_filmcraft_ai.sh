#!/usr/bin/env bash

set -euo pipefail

fail() {
    echo "✗ $1" >&2
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -u critical 'FilmCraft + assistant' "$1" || true
    fi
    exit 1
}

if (( $# > 1 )); then
    echo "Usage: filmcraft-ai [project.fcproj]" >&2
    exit 2
fi

for tool in filmcraft filmcraft-cli pi kitty ss flock python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "Required command missing: $tool"
    fi
done

PROJECT=""
if (( $# == 1 )); then
    if [[ ! -f "$1" || "$1" != *.fcproj ]]; then
        fail "FilmCraft project not found: $1"
    fi
    PROJECT="$(realpath -e -- "$1")"
fi

# Never redirect another session's assistant to an unrelated project. A regular
# FilmCraft window also cannot be upgraded to a controlled one in place.
if pgrep -u "$(id -u)" -x filmcraft >/dev/null 2>&1; then
    fail 'Close the existing FilmCraft window before opening FilmCraft + assistant.'
fi
if [[ -n "$(ss -H -lnt '( sport = :9876 )')" ]]; then
    fail 'Control port 9876 is already in use; refusing to connect to an unknown process.'
fi

SESSION_DIR="${HOME}/.local/share/filmcraft-ai"
SESSION_HELPER="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/filmcraft-ai-session"
if [[ ! -f "$SESSION_DIR/.pi/mcp.json" || ! -x "$SESSION_HELPER" ]]; then
    fail 'FilmCraft Pi configuration not installed. Run the linux-setup FilmCraft installer.'
fi
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/filmcraft-ai"
umask 077
mkdir -p "$STATE_DIR"
exec 9> "$STATE_DIR/launch.lock"
if ! flock -n 9; then
    fail 'Another FilmCraft + assistant launch is already in progress.'
fi

if [[ -n "$PROJECT" ]]; then
    if ! SESSION_INFO="$("$SESSION_HELPER" "$PROJECT" "$SESSION_DIR")"; then
        fail 'Could not resolve the project conversation.'
    fi
    read -r SESSION_ID SESSION_STATE <<< "$SESSION_INFO"
    nohup filmcraft --control 9876 "$PROJECT" >> "$STATE_DIR/filmcraft.log" 2>&1 < /dev/null 9>&- &
else
    nohup filmcraft --control 9876 --empty >> "$STATE_DIR/filmcraft.log" 2>&1 < /dev/null 9>&- &
fi
FILMCRAFT_PID=$!

ready=false
for ((i = 0; i < 120; i++)); do
    if ! kill -0 "$FILMCRAFT_PID" 2>/dev/null; then
        fail "FilmCraft exited early; see $STATE_DIR/filmcraft.log"
    fi
    if [[ -n "$(ss -H -lnt '( sport = :9876 )')" ]]; then
        ready=true
        break
    fi
    sleep 0.25
done
if [[ "$ready" != true ]]; then
    kill "$FILMCRAFT_PID" 2>/dev/null || true
    fail "FilmCraft did not open its control port; see $STATE_DIR/filmcraft.log"
fi

if [[ -n "$PROJECT" ]]; then
    TITLE="FilmCraft - $(basename -- "$PROJECT")"
    REQUEST="Aide-moi à apprendre FilmCraft avec le projet ouvert : $PROJECT. Utilise le skill filmcraft. Commence par inspecter l'interface et le projet en lecture seule, puis demande-moi ce que je souhaite apprendre. Ne modifie rien sans mon accord."
    if [[ "$SESSION_STATE" == existing ]]; then
        PI_ARGS=(pi --session-id "$SESSION_ID")
    else
        PI_ARGS=(pi --session-id "$SESSION_ID" --name "$TITLE" "$REQUEST")
    fi
else
    TITLE="FilmCraft - assistant"
    REQUEST="Aide-moi à apprendre FilmCraft. Utilise le skill filmcraft. Commence par inspecter l'interface en lecture seule, puis demande-moi ce que je souhaite apprendre. Ne modifie rien sans mon accord."
    PI_ARGS=(pi --name "$TITLE" "$REQUEST")
fi

# The dedicated Pi directory activates the project-local FilmCraft MCP override
# after Pi's one-time project trust approval; other Pi sessions remain unaffected.
if ! kitty --detach --directory "$SESSION_DIR" --title 'FilmCraft + assistant' \
    "${PI_ARGS[@]}" 9>&-; then
    kill "$FILMCRAFT_PID" 2>/dev/null || true
    fail 'Could not start Pi; closing the FilmCraft instance started here.'
fi
