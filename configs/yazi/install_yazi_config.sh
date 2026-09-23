#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Yazi"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILES=(init.lua keymap.toml yazi.toml)
TARGET_DIR="${HOME}/.config/yazi"
LAUNCHER_SOURCE="${SCRIPT_DIR}/launch_yazi.sh"
LAUNCHER_TARGET="${HOME}/.local/bin/launch-yazi"

echo "==> Installing ${CONFIG_NAME} config..."

for source_name in "${SOURCE_FILES[@]}"; do
    if [[ ! -f "${SCRIPT_DIR}/${source_name}" ]]; then
        echo "✗ Source config not found: ${SCRIPT_DIR}/${source_name}"
        exit 1
    fi
done

if [[ ! -f "${LAUNCHER_SOURCE}" ]]; then
    echo "✗ Yazi launcher not found: ${LAUNCHER_SOURCE}"
    exit 1
fi

mkdir -p "${TARGET_DIR}" "$(dirname "${LAUNCHER_TARGET}")"

for source_name in "${SOURCE_FILES[@]}"; do
    source_file="${SCRIPT_DIR}/${source_name}"
    target_file="${TARGET_DIR}/${source_name}"

    if [[ -f "${target_file}" ]] && ! cmp -s "${source_file}" "${target_file}"; then
        backup_file="${target_file}.bak.$(date +%Y%m%d-%H%M%S)"
        echo "==> Existing config found, creating backup:"
        echo "    ${backup_file}"
        cp "${target_file}" "${backup_file}"
    fi

    cp "${source_file}" "${target_file}"
done

install -m 0755 "${LAUNCHER_SOURCE}" "${LAUNCHER_TARGET}"

echo "✓ ${CONFIG_NAME} config installed successfully."
