#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Fit Scroller"
RELEASES_API_URL="https://api.github.com/repos/ForgeDuSavoir/fit-scroller-layout/releases/latest"
TARGET_DIR="${HOME}/.config/hypr/layouts"
INSTALL_DIR="${TARGET_DIR}/fit-scroller"

echo "==> Installing ${APP_NAME} layout..."

if [[ -f "${INSTALL_DIR}/init.lua" ]]; then
    echo "✓ ${APP_NAME} layout is already installed."
    exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "✗ curl is required to install ${APP_NAME}."
    exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
    echo "✗ tar is required to install ${APP_NAME}."
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

ARCHIVE_URL="$(
    curl -fsSL "${RELEASES_API_URL}" \
        | sed -n 's/.*"browser_download_url": "\(https:[^"]*fit-scroller-layout-v[^"]*\.tar\.gz\)".*/\1/p' \
        | head -n 1
)"

if [[ -z "${ARCHIVE_URL}" ]]; then
    echo "✗ Could not find a ${APP_NAME} release archive."
    exit 1
fi

ARCHIVE_PATH="${TMP_DIR}/fit-scroller-layout.tar.gz"

curl -fL "${ARCHIVE_URL}" -o "${ARCHIVE_PATH}"

mkdir -p "${TARGET_DIR}"
tar -C "${TARGET_DIR}" -xzf "${ARCHIVE_PATH}"

if [[ ! -f "${INSTALL_DIR}/init.lua" ]]; then
    echo "✗ ${APP_NAME} installation failed: ${INSTALL_DIR}/init.lua was not found."
    exit 1
fi

echo "✓ ${APP_NAME} layout installed successfully."
