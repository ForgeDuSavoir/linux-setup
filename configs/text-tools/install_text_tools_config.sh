#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Text tools"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/files/config.sh"
TARGET_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/text-tools"
TARGET_FILE="${TARGET_DIR}/config.sh"

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

install -m 0644 "${SOURCE_FILE}" "${TARGET_FILE}"

echo "✓ ${CONFIG_NAME} config installed successfully."
