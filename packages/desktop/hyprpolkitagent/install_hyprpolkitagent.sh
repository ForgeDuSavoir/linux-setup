#!/usr/bin/env bash

set -euo pipefail

APP_NAME="hyprpolkitagent"
PACKAGE_NAME="hyprpolkitagent"
APP_COMMAND="/usr/lib/hyprpolkitagent/hyprpolkitagent"
PACKAGE_MANAGER="pacman"
INSTALL_COMMAND="sudo pacman -S --needed --noconfirm ${PACKAGE_NAME}"

echo "==> Installing ${APP_NAME}..."

if [[ -n "${APP_COMMAND}" ]] && command -v "$APP_COMMAND" >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed."
else
    if [[ -z "${PACKAGE_MANAGER}" ]]; then
        echo "✗ PACKAGE_MANAGER is not set."
        exit 1
    fi

    if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
        echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
        echo "Install ${PACKAGE_MANAGER} first, then run this script again."
        exit 1
    fi

    if [[ -z "${INSTALL_COMMAND}" ]]; then
        echo "✗ INSTALL_COMMAND is not set."
        exit 1
    fi

    eval "$INSTALL_COMMAND"
fi

echo "==> Enabling ${APP_NAME} user service..."
systemctl --user enable --now hyprpolkitagent.service

echo "✓ ${APP_NAME} installed and enabled successfully."
