#!/usr/bin/env bash

set -euo pipefail

COMPONENT_NAME="Quickshell NotificationServer"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/files/NotificationService.qml"
TARGET_DIR="${HOME}/.config/quickshell"
TARGET_FILE="${TARGET_DIR}/NotificationService.qml"

echo "==> Installing ${COMPONENT_NAME}..."

if ! command -v quickshell >/dev/null 2>&1; then
    echo "✗ Quickshell is required to install ${COMPONENT_NAME}."
    echo "Run the Quickshell package installer first."
    exit 1
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
    echo "✗ Source file not found: ${SOURCE_FILE}"
    exit 1
fi

if [[ ! -f "${TARGET_DIR}/shell.qml" ]]; then
    echo "✗ Quickshell config not found: ${TARGET_DIR}/shell.qml"
    echo "Run install_quickshell_config.sh first."
    exit 1
fi

install -m 0644 "${SOURCE_FILE}" "${TARGET_FILE}"

if ! grep -Fq 'NotificationService {}' "${TARGET_DIR}/shell.qml"; then
    if ! grep -q '^Scope {$' "${TARGET_DIR}/shell.qml"; then
        echo "✗ Unable to locate the root Scope in ${TARGET_DIR}/shell.qml."
        exit 1
    fi

    SHELL_BACKUP="${TARGET_DIR}/shell.qml.bak.$(date +%Y%m%d-%H%M%S)"
    cp "${TARGET_DIR}/shell.qml" "${SHELL_BACKUP}"
    sed -i '/^Scope {$/a\    NotificationService {}' "${TARGET_DIR}/shell.qml"

    echo "==> NotificationService enabled in shell.qml."
    echo "    Backup: ${SHELL_BACKUP}"
fi

echo "✓ ${COMPONENT_NAME} installed successfully."
echo "  Restart Quickshell to activate it."
