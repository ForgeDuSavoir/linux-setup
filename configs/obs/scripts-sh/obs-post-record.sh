#!/usr/bin/env bash

set -euo pipefail

video="$1"

video_dir="$(dirname "$video")"
filename="$(basename "$video")"
name="${filename%.*}"

project_dir="$video_dir/$name"

# Ensure pre-edit exists
if ! command -v pre-edit >/dev/null 2>&1; then
    notify-send "OBS Automation" "Error: pre-edit command not found"
    exit 1
fi

mkdir -p "$project_dir"
mv "$video" "$project_dir/$filename"
cd "$project_dir"

# Run auto-editor workflow
if pre-edit "$filename"; then
    notify-send "OBS Automation" "Pre-edit completed: $name"
else
    notify-send "OBS Automation" "Pre-edit failed: $name"
    exit 1
fi