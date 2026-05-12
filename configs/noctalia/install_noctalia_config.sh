#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="Noctalia"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE_DIR="${SCRIPT_DIR}"
TARGET_DIR="${HOME}/.config/noctalia"

FILES_TO_COPY=(
    "settings.json"
    "plugins.json"
    "colors.json"
)

echo "==> Installing ${CONFIG_NAME} config..."

# Ensure target directory exists
mkdir -p "${TARGET_DIR}"

# Copy each config file
for file in "${FILES_TO_COPY[@]}"; do
    SOURCE_FILE="${SOURCE_DIR}/${file}"
    TARGET_FILE="${TARGET_DIR}/${file}"

    if [[ ! -f "${SOURCE_FILE}" ]]; then
        echo "⚠ Skipping missing file: ${file}"
        continue
    fi

    # Backup existing file
    if [[ -f "${TARGET_FILE}" ]]; then
        BACKUP_FILE="${TARGET_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
        echo "==> Backing up existing ${file} to:"
        echo "    ${BACKUP_FILE}"
        cp "${TARGET_FILE}" "${BACKUP_FILE}"
    fi

    echo "==> Copying ${file}..."
    cp "${SOURCE_FILE}" "${TARGET_FILE}"
done

echo "✓ ${CONFIG_NAME} config installed successfully."
