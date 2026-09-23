#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Quickshell"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="${SCRIPT_DIR}/files"
TARGET_DIR="${HOME}/.config/quickshell"
RUNNING_PID="$(pgrep -o -x quickshell || true)"

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

if [[ -n "${RUNNING_PID}" ]] && command -v quickshell >/dev/null 2>&1; then
    echo "==> Restarting ${CONFIG_NAME}..."
    quickshell kill --pid "${RUNNING_PID}"

    for _ in {1..50}; do
        if ! kill -0 "${RUNNING_PID}" 2>/dev/null; then
            break
        fi
        sleep 0.1
    done

    quickshell --daemonize
fi

echo "✓ ${CONFIG_NAME} config installed successfully."
