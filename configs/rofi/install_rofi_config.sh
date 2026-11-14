#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Rofi application menus"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="${SCRIPT_DIR}/files"
TARGET_DIR="${HOME}/.config/rofi"

THEME_SOURCE="${SOURCE_DIR}/project-launcher.rasi"
THEME_TARGET="${TARGET_DIR}/project-launcher.rasi"
LAUNCHER_TARGET="${HOME}/.local/bin/agora-project-launcher"

echo "==> Installing ${CONFIG_NAME}..."

for source in "${THEME_SOURCE}"; do
    if [[ ! -f "${source}" ]]; then
        echo "✗ Source file not found: ${source}"
        exit 1
    fi
done

mkdir -p "${TARGET_DIR}"
# Keep the shared theme used by SUPER+D and SUPER+A, not the retired project picker.
install -m 0644 "${THEME_SOURCE}" "${THEME_TARGET}"
if [[ -L "${LAUNCHER_TARGET}" ]]; then
    echo "✗ Refusing to remove a symlinked retired launcher: ${LAUNCHER_TARGET}" >&2
    exit 1
fi
rm -f -- "${LAUNCHER_TARGET}"

echo "✓ ${CONFIG_NAME} installed successfully."
