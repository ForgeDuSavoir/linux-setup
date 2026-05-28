#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="OBS"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

SOURCE_CONFIG_DIR="${SCRIPT_DIR}/files"
SOURCE_LUA_DIR="${SCRIPT_DIR}/scripts-lua"
SOURCE_SH_DIR="${SCRIPT_DIR}/scripts-sh"

TARGET_CONFIG_DIR="${HOME}/.config/obs-studio"
TARGET_LUA_DIR="/usr/share/obs/obs-plugins/frontend-tools/scripts/custom"
TARGET_BIN_DIR="${HOME}/.local/bin"

echo "==> Installing ${CONFIG_NAME} config..."

if [[ ! -d "${SOURCE_CONFIG_DIR}" ]]; then
    echo "✗ Source config directory not found: ${SOURCE_CONFIG_DIR}"
    exit 1
fi

mkdir -p "${HOME}/.config"
sudo mkdir -p "${TARGET_LUA_DIR}"
mkdir -p "${TARGET_BIN_DIR}"

if [[ -d "${TARGET_CONFIG_DIR}" ]]; then
    BACKUP_DIR="${TARGET_CONFIG_DIR}.bak.$(date +%Y%m%d-%H%M%S)"
    echo "==> Existing OBS config found, creating backup:"
    echo "    ${BACKUP_DIR}"
    mv "${TARGET_CONFIG_DIR}" "${BACKUP_DIR}"
fi

echo "==> Copying OBS config..."
cp -r "${SOURCE_CONFIG_DIR}" "${TARGET_CONFIG_DIR}"

if [[ -d "${SOURCE_LUA_DIR}" ]]; then
    echo "==> Installing OBS Lua scripts..."
    sudo cp "${SOURCE_LUA_DIR}"/*.lua "${TARGET_LUA_DIR}/"
else
    echo "⚠ Lua scripts directory not found, skipping:"
    echo "  ${SOURCE_LUA_DIR}"
fi

if [[ -d "${SOURCE_SH_DIR}" ]]; then
    echo "==> Installing OBS shell scripts..."
    cp "${SOURCE_SH_DIR}"/*.sh "${TARGET_BIN_DIR}/"

    echo "==> Making OBS shell scripts executable..."
    chmod +x "${TARGET_BIN_DIR}"/*.sh
else
    echo "⚠ Shell scripts directory not found, skipping:"
    echo "  ${SOURCE_SH_DIR}"
fi

echo "✓ ${CONFIG_NAME} config installed successfully."