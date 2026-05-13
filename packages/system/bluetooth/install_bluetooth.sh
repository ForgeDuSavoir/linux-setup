#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Bluetooth Support"
PACKAGE_NAME="bluez bluez-utils blueman"
PACKAGE_MANAGER="pacman"
INSTALL_COMMAND="sudo pacman -S --needed --noconfirm ${PACKAGE_NAME}"

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

ALL_INSTALLED=true

for package in ${PACKAGE_NAME}; do
    if ! pacman -Q "${package}" >/dev/null 2>&1; then
        ALL_INSTALLED=false
        break
    fi
done

if [[ "${ALL_INSTALLED}" == true ]]; then
    echo "✓ ${APP_NAME} is already installed."
    exit 0
fi

if [[ -z "${INSTALL_COMMAND}" ]]; then
    echo "✗ INSTALL_COMMAND is not set."
    exit 1
fi

eval "$INSTALL_COMMAND"

echo "==> Enabling Bluetooth service..."

sudo systemctl enable --now bluetooth.service

echo "✓ ${APP_NAME} installed successfully."
