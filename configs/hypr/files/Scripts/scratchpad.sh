#!/usr/bin/env bash

set -euo pipefail

usage() {
    printf 'Usage: %s <toggle|move> <global|1|2|3|4|5>\n' "${0##*/}" >&2
    exit 2
}

[[ $# -eq 2 ]] || usage

action="$1"
scope="$2"

case "${scope}" in
    global) scratchpad_name="global" ;;
    1|ai) scratchpad_name="session-ai" ;;
    2|notes) scratchpad_name="session-notes" ;;
    3|tasks) scratchpad_name="session-tasks" ;;
    4|5) scratchpad_name="session-${scope}" ;;
    *) usage ;;
esac

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
