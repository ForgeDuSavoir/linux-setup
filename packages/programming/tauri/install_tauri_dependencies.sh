#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Tauri Linux development dependencies"
PACKAGE_MANAGER="pacman"
PACKAGES=(
    webkit2gtk-4.1
    base-devel
    curl
    wget
    file
    openssl
    appmenu-gtk-module
    libappindicator-gtk3
    librsvg
    xdotool
)

if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
    echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
    echo "This installer targets Arch Linux and CachyOS."
    exit 1
fi

MISSING_PACKAGES=()
for package in "${PACKAGES[@]}"; do
    if ! "$PACKAGE_MANAGER" -Q "$package" >/dev/null 2>&1; then
        MISSING_PACKAGES+=("$package")
    fi
done

if (( ${#MISSING_PACKAGES[@]} == 0 )); then
    echo "✓ ${APP_NAME} are already installed."
    exit 0
fi

echo "==> Installing ${APP_NAME}: ${MISSING_PACKAGES[*]}..."
sudo "$PACKAGE_MANAGER" -S --needed --noconfirm "${MISSING_PACKAGES[@]}"
echo "✓ ${APP_NAME} installed successfully."
