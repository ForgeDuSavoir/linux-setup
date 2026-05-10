#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONT_DIR="$HOME/.local/share/fonts"

echo "==> Installing fonts..."

mkdir -p "$FONT_DIR"

FOUND_FONTS=false

while IFS= read -r -d '' font_file; do
    FOUND_FONTS=true
    echo "→ Installing $(basename "$font_file")"
    cp -u "$font_file" "$FONT_DIR/"
done < <(find "$SCRIPT_DIR" \
    -type f \
    \( -iname "*.ttf" -o -iname "*.otf" \) \
    -print0)

if [[ "$FOUND_FONTS" = false ]]; then
    echo "⚠ No font files found in:"
    echo "  $SCRIPT_DIR"
    exit 0
fi

echo "==> Refreshing font cache..."

fc-cache -fv >/dev/null

echo "✓ Fonts installed successfully."
