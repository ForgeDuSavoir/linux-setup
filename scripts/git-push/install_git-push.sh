#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="git-push"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/git-push.sh"
TARGET_DIR="${HOME}/.local/bin"
TARGET_FILE="${TARGET_DIR}/${SCRIPT_NAME}"

echo "==> Installing ${SCRIPT_NAME}..."

if [[ ! -f "${SOURCE_FILE}" ]]; then
    echo "✗ Missing source file: ${SOURCE_FILE}"
    exit 1
fi

mkdir -p "${TARGET_DIR}"

cp "${SOURCE_FILE}" "${TARGET_FILE}"
chmod +x "${TARGET_FILE}"

echo "✓ ${SCRIPT_NAME} installed to ${TARGET_FILE}"