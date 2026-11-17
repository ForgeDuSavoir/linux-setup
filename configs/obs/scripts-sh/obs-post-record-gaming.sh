#!/usr/bin/env bash

set -euo pipefail

# A stop hook must use the value frozen at RECORDING_STARTED, not capture
# whichever session happens to be selected after recording finishes.
export AGORA_NOTIFICATION_CONTEXT="${2:-${AGORA_NOTIFICATION_CONTEXT:-global}}"
notify() {
    if command -v agora-notify >/dev/null 2>&1; then
        agora-notify send --app-name "OBS Automation" "$@" || true
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "$@" || true
    fi
}

video="$1"

video_dir="$(dirname "$video")"
filename="$(basename "$video")"
name="${filename%.*}"

project_dir="$video_dir/$name"

# Ensure pre-edit exists
if ! command -v pre-edit >/dev/null 2>&1; then
    notify "OBS Automation" "Error: pre-edit command not found"
    exit 1
fi

mkdir -p "$project_dir"
mv "$video" "$project_dir/$filename"
cd "$project_dir"

# Run auto-editor workflow
if pre-edit "$filename"; then
    notify "OBS Automation" "Pre-edit completed: $name"
else
    notify "OBS Automation" "Pre-edit failed: $name"
    exit 1
fi