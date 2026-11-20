#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="obs-gaming"

BIN_FILE="${HOME}/.local/bin/${SCRIPT_NAME}"
DESKTOP_FILE="${HOME}/.local/share/applications/${SCRIPT_NAME}.desktop"

echo "==> Uninstalling ${SCRIPT_NAME}..."

if [[ -f "${BIN_FILE}" ]]; then
    rm "${BIN_FILE}"
    echo "✓ Removed script:"
    echo "  ${BIN_FILE}"
else
    echo "• Script not found:"
    echo "  ${BIN_FILE}"
fi

if [[ -f "${DESKTOP_FILE}" ]]; then
    rm "${DESKTOP_FILE}"
    echo "✓ Removed desktop entry:"
    echo "  ${DESKTOP_FILE}"
else
    echo "• Desktop entry not found:"
    echo "  ${DESKTOP_FILE}"
fi

echo
echo "✓ ${SCRIPT_NAME} uninstalled successfully."