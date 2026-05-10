#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Flatpak"
PACKAGE_NAME="flatpak"
APP_COMMAND="flatpak"

echo "==> Installing ${APP_NAME}..."

if command -v "$APP_COMMAND" >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed."
    exit 0
fi

if ! command -v pacman >/dev/null 2>&1; then
    echo "✗ pacman is required to install ${APP_NAME}."
    exit 1
fi

sudo pacman -S --needed --noconfirm "$PACKAGE_NAME"

echo "✓ ${APP_NAME} installed successfully."
