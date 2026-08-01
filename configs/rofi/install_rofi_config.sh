#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Rofi project launcher"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="${SCRIPT_DIR}/files"
TARGET_DIR="${HOME}/.config/rofi"
TARGET_SCRIPT_DIR="${HOME}/.local/bin"

THEME_SOURCE="${SOURCE_DIR}/project-launcher.rasi"
CONVERSATION_THEME_SOURCE="${SOURCE_DIR}/conversation-navigation.rasi"
LAUNCHER_SOURCE="${SOURCE_DIR}/agora-project-launcher.sh"
THEME_TARGET="${TARGET_DIR}/project-launcher.rasi"
CONVERSATION_THEME_TARGET="${TARGET_DIR}/conversation-navigation.rasi"
LAUNCHER_TARGET="${TARGET_SCRIPT_DIR}/agora-project-launcher"

echo "==> Installing ${CONFIG_NAME}..."

for source in "${THEME_SOURCE}" "${CONVERSATION_THEME_SOURCE}" "${LAUNCHER_SOURCE}"; do
    if [[ ! -f "${source}" ]]; then
        echo "✗ Source file not found: ${source}"
        exit 1
    fi
done

mkdir -p "${TARGET_DIR}" "${TARGET_SCRIPT_DIR}"
install -m 0644 "${THEME_SOURCE}" "${THEME_TARGET}"
install -m 0644 "${CONVERSATION_THEME_SOURCE}" "${CONVERSATION_THEME_TARGET}"
install -m 0755 "${LAUNCHER_SOURCE}" "${LAUNCHER_TARGET}"

echo "✓ ${CONFIG_NAME} installed successfully."
