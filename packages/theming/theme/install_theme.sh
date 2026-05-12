#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Themes"
PACKAGE_NAME="adw-gtk-theme papirus-icon-theme noto-fonts-emoji bibata-cursor-theme"
PACKAGE_MANAGER="pacman"
INSTALL_COMMAND="sudo pacman -S --needed ${PACKAGE_NAME}"

echo "==> Installing ${APP_NAME}..."

if [[ -z "${PACKAGE_MANAGER}" ]]; then
    echo "✗ PACKAGE_MANAGER is not set."
    exit 1
fi

if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
    echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
    echo "Install ${PACKAGE_MANAGER} first, then run this script again."
    exit 1
fi

eval "$INSTALL_COMMAND"

echo "✓ ${APP_NAME} installed successfully."
