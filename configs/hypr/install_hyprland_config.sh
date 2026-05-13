#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Hyprland"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="${SCRIPT_DIR}/files"
TARGET_DIR="${HOME}/.config/hypr"

echo "==> Installing ${CONFIG_NAME} config..."

if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "✗ Source directory not found: ${SOURCE_DIR}"
    exit 1
fi

mkdir -p "${HOME}/.config"

if [[ -d "${TARGET_DIR}" ]]; then
    BACKUP_DIR="${TARGET_DIR}.bak.$(date +%Y%m%d-%H%M%S)"
    echo "==> Existing config found, creating backup:"
    echo "    ${BACKUP_DIR}"
    mv "${TARGET_DIR}" "${BACKUP_DIR}"
fi

echo "==> Copying config..."
cp -r "${SOURCE_DIR}" "${TARGET_DIR}"

if [[ -d "${TARGET_DIR}/Scripts" ]]; then
    echo "==> Making Hyprland scripts executable..."
    find "${TARGET_DIR}/Scripts" -type f -exec chmod +x {} \;
fi

echo "✓ ${CONFIG_NAME} config installed successfully."
