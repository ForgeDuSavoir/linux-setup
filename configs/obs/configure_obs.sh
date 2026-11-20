#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="OBS"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "${1:-}" == --scripts-only && $# -eq 1 ]]; then
    exec bash "${SCRIPT_DIR}/install_obs_scripts.sh"
elif [[ "${1:-}" == --launchers-only && $# -eq 1 ]]; then
    exec python3 "${SCRIPT_DIR}/install_project_launchers.py" --apply --desktop-only
elif [[ $# -ne 0 ]]; then
    echo "Usage: $0 [--scripts-only|--launchers-only]" >&2
    exit 2
fi

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

bash "${SCRIPT_DIR}/install_obs_scripts.sh"
python3 "${SCRIPT_DIR}/install_project_launchers.py" --apply

echo "✓ ${CONFIG_NAME} config installed successfully."