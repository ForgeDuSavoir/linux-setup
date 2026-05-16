#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="obs-fds"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

SOURCE_SCRIPT="${SCRIPT_DIR}/${SCRIPT_NAME}.sh"
SOURCE_DESKTOP="${SCRIPT_DIR}/${SCRIPT_NAME}.desktop"

BIN_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${HOME}/.local/share/applications"

TARGET_SCRIPT="${BIN_DIR}/${SCRIPT_NAME}"
TARGET_DESKTOP="${APPLICATIONS_DIR}/${SCRIPT_NAME}.desktop"

echo "==> Installing ${SCRIPT_NAME}..."

if [[ ! -f "${SOURCE_SCRIPT}" ]]; then
    echo "✗ Missing source script:"
    echo "  ${SOURCE_SCRIPT}"
    exit 1
fi

if [[ ! -f "${SOURCE_DESKTOP}" ]]; then
    echo "✗ Missing desktop file:"
    echo "  ${SOURCE_DESKTOP}"
    exit 1
fi

mkdir -p "${BIN_DIR}"
mkdir -p "${APPLICATIONS_DIR}"

echo "==> Installing launcher script..."

cp "${SOURCE_SCRIPT}" "${TARGET_SCRIPT}"
chmod +x "${TARGET_SCRIPT}"

echo "==> Installing desktop entry..."

sed "s|__HOME_DIR__|${HOME}|g" "${SOURCE_DESKTOP}" > "${TARGET_DESKTOP}"

chmod +x "${TARGET_DESKTOP}"

echo "✓ ${SCRIPT_NAME} installed successfully."
echo
echo "Script:"
echo "  ${TARGET_SCRIPT}"
echo
echo "Desktop entry:"
echo "  ${TARGET_DESKTOP}"