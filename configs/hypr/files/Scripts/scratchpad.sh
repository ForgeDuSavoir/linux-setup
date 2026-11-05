#!/usr/bin/env bash

set -euo pipefail

usage() {
    printf 'Usage: %s <toggle|move> <global|1|2|3|4|5>\n' "${0##*/}" >&2
    exit 2
}

[[ $# -eq 2 ]] || usage

# Serialize scratchpad routing against a session-menu context change. Without
# this lock a shortcut can read the old UUID then dispatch after a switch.
runtime="${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is required}/hyprland"
mkdir -p -- "${runtime}"
exec 9>"${runtime}/workspace-columns.lock"
flock -x 9

action="$1"
scope="$2"

case "${scope}" in
    global) scratchpad_name="global" ;;
    1|ai) slot="ai" ;;
    2|notes) slot="notes" ;;
    3|tasks) slot="tasks" ;;
    4|5) slot="${scope}" ;;
    *) usage ;;
esac

if [[ "${scope}" != global ]]; then
    # An unselected context keeps the old special workspaces accessible as
    # neutral scratchpads. Existing windows are never silently reassigned.
    response="$("${SESSION_MANAGER_BIN:-${HOME}/.local/bin/session-manager}" --json session list)" || {
        echo 'scratchpad: session state unavailable; refusing to target a special workspace' >&2
        exit 1
    }
    session_id="$(jq -er 'if (.sessions | type) != "array" then error("invalid response") elif .active_session_id == null then "" elif .active_session_id as $id | any(.sessions[]; .id == $id) then .active_session_id else error("unknown active session") end' <<<"${response}")" || {
        echo 'scratchpad: invalid session response; refusing to target a special workspace' >&2
        exit 1
    }
    if [[ -n "${session_id}" ]]; then
        [[ "${session_id}" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || {
            echo 'scratchpad: invalid session ID' >&2
            exit 1
        }
        scratchpad_name="sm-${session_id}-${slot}"
    else
        scratchpad_name="session-${slot}"
    fi
fi

case "${action}" in
    toggle)
        hyprctl dispatch "hl.dsp.workspace.toggle_special(\"${scratchpad_name}\")"
        ;;
    move)
        active_window_workspace="$(hyprctl activewindow -j | jq -r '.workspace.name // empty')"
        [[ -n "${active_window_workspace}" ]] || exit 0

        if [[ "${active_window_workspace}" == "special:${scratchpad_name}" ]]; then
            # activeworkspace remains the normal workspace even when a
            # special workspace is visible above it.
            workspace_id="$(hyprctl activeworkspace -j | jq -er '.id | select(. > 0)')" || exit 0
            hyprctl dispatch "hl.dsp.window.move({ workspace = ${workspace_id} })"
        else
            hyprctl dispatch "hl.dsp.window.move({ workspace = \"special:${scratchpad_name}\" })"
        fi
        ;;
    *) usage ;;
esac
