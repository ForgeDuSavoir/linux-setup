#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Qt Wayland support"

echo "==> Installing ${APP_NAME}..."

if ! command -v pacman >/dev/null 2>&1; then
    echo "✗ pacman is required."
    exit 1
fi

sudo pacman -S --needed --noconfirm \
    qt5-wayland \
    qt6-wayland

echo "✓ ${APP_NAME} installed successfully."
