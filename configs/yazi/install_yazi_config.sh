#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Yazi"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/init.lua"
TARGET_DIR="${HOME}/.config/yazi"
TARGET_FILE="${TARGET_DIR}/init.lua"

echo "==> Installing ${CONFIG_NAME} config..."

if [[ ! -f "${SOURCE_FILE}" ]]; then
    echo "✗ Source config not found: ${SOURCE_FILE}"
    exit 1
fi

mkdir -p "${TARGET_DIR}"

if [[ -f "${TARGET_FILE}" ]] && ! cmp -s "${SOURCE_FILE}" "${TARGET_FILE}"; then
    BACKUP_FILE="${TARGET_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
    echo "==> Existing config found, creating backup:"
    echo "    ${BACKUP_FILE}"
    cp "${TARGET_FILE}" "${BACKUP_FILE}"
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"

echo "✓ ${CONFIG_NAME} config installed successfully."
