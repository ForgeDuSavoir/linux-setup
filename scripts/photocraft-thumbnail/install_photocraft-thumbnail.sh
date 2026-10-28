#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
for tool in python3 ffmpeg ffprobe photocraft-cli; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "✗ $tool is required for photocraft-thumbnail." >&2
        exit 1
    fi
done
if [[ ! -s "$SCRIPT_DIR/photocraft-thumbnail-mask.zip" ]]; then
    echo '✗ PhotoCraft reference mask is missing.' >&2
    exit 1
fi
mkdir -p "${HOME}/.local/bin"
install -m 0644 "$SCRIPT_DIR/photocraft-thumbnail-mask.zip" "${HOME}/.local/bin/photocraft-thumbnail-mask.zip"
install -m 0755 "$SCRIPT_DIR/photocraft-thumbnail.py" "${HOME}/.local/bin/photocraft-thumbnail"
echo "✓ photocraft-thumbnail and reference mask installed to ${HOME}/.local/bin/"
