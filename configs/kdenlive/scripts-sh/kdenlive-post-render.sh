#!/usr/bin/env bash

set -euo pipefail

INPUT="${1:-}"

notify() {
    command -v notify-send >/dev/null 2>&1 && notify-send "$1" "$2"
}

if [[ -z "$INPUT" ]]; then
    notify "Kdenlive post-render" "No rendered file path received."
    exit 1
fi

# If Kdenlive sends a full message, try to extract the first existing video path.
if [[ -f "$INPUT" ]]; then
    RENDERED_FILE="$INPUT"
else
    RENDERED_FILE="$(printf '%s\n' "$INPUT" | grep -oE '/[^"]+\.(mp4|mkv|mov|webm|avi)' | head -n 1 || true)"
fi

if [[ -z "${RENDERED_FILE:-}" || ! -f "$RENDERED_FILE" ]]; then
    notify "Kdenlive post-render failed" "Rendered file not found."
    exit 1
fi

RENDER_DIR="$(dirname "$RENDERED_FILE")"
PROJECT_DIR="$(dirname "$RENDER_DIR")"
FINAL_DIR="${PROJECT_DIR}/final"

mkdir -p "$FINAL_DIR"

mv "$RENDERED_FILE" "$FINAL_DIR/"

notify "Kdenlive post-render" "Moved render to: $FINAL_DIR"