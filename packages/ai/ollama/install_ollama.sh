#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Ollama"
PACKAGE_NAME="ollama"
APP_COMMAND="ollama"
PACKAGE_MANAGER="pacman"
INSTALL_COMMAND="sudo pacman -S --needed --noconfirm ${PACKAGE_NAME}"

echo "==> Installing ${APP_NAME}..."

if [[ -n "${APP_COMMAND}" ]] && command -v "${APP_COMMAND}" >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed."
    exit 0
fi

if ! command -v "${PACKAGE_MANAGER}" >/dev/null 2>&1; then
    echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
    exit 1
fi

${INSTALL_COMMAND}

echo "✓ ${APP_NAME} installed successfully."
