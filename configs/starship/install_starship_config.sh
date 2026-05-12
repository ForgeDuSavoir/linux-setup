#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Starship"
SOURCE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/starship.toml"
TARGET_FILE="${HOME}/.config/starship.toml"

echo "==> Installing ${CONFIG_NAME} config..."

# Ensure ~/.config exists
mkdir -p "${HOME}/.config"

# Backup existing config if present
if [[ -f "${TARGET_FILE}" ]]; then
    BACKUP_FILE="${TARGET_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
    echo "==> Existing config found, creating backup:"
    echo "    ${BACKUP_FILE}"
    cp "${TARGET_FILE}" "${BACKUP_FILE}"
fi

# Copy config
cp "${SOURCE_FILE}" "${TARGET_FILE}"

echo "✓ ${CONFIG_NAME} config installed successfully."
