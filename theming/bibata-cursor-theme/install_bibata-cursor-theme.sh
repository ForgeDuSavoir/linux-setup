#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Bibata Cursor Theme"
PACKAGE_NAME="bibata-cursor-theme"
PACKAGE_CHECK="bibata-cursor-theme"
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


# Check via package manager
if [[ -n "${PACKAGE_CHECK}" ]]; then
    if "${PACKAGE_MANAGER}" -Q "${PACKAGE_CHECK}" >/dev/null 2>&1; then
        echo "✓ ${APP_NAME} is already installed."
        exit 0
    fi
fi

if [[ -z "${INSTALL_COMMAND}" ]]; then
    echo "✗ INSTALL_COMMAND is not set."
    exit 1
fi

eval "$INSTALL_COMMAND"

echo "✓ ${APP_NAME} installed successfully."
