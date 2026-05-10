#!/usr/bin/env bash

set -euo pipefail

APP_NAME="pipx"
PACKAGE_NAME="python-pipx"

echo "==> Installing ${APP_NAME}..."

if command -v pipx >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed."
else
    sudo pacman -S --needed --noconfirm "$PACKAGE_NAME"
fi

echo "==> Ensuring pipx binary path is configured..."

pipx ensurepath

echo "✓ ${APP_NAME} installed successfully."
echo
echo "Note: if pipx was just installed, you may need to restart your terminal"
echo "or run:"
echo 'source ~/.bashrc / source ~/.zshrc depending on your shell'
