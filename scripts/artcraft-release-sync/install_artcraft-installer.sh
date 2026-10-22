#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/../../packages/artcraft/install_artcraft_apps.sh"
TARGET_DIR="${HOME}/.local/bin"
TARGET_FILE="${TARGET_DIR}/install-artcraft-releases"

if [[ ! -f "$SOURCE_FILE" || ! -f "${SCRIPT_DIR}/artcraft-apps.list" ]]; then
    echo "✗ Missing ArtCraft installer or app list." >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"
cp "$SOURCE_FILE" "$TARGET_FILE"
cp "${SCRIPT_DIR}/artcraft-apps.list" "${TARGET_DIR}/artcraft-apps.list"
chmod +x "$TARGET_FILE"
echo "✓ ArtCraft package updater installed to $TARGET_FILE"
