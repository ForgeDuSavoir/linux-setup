#!/usr/bin/env bash

set -euo pipefail

APP_NAME="pnpm"
APP_COMMAND="pnpm"
PACKAGE_MANAGER="npm"
PACKAGE_NAME="pnpm"

if command -v "$APP_COMMAND" >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed: $($APP_COMMAND --version)"
    exit 0
fi

echo "==> Installing ${APP_NAME}..."

if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
    echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
    echo "Install Node.js and npm first, then run this script again."
    exit 1
fi

sudo "$PACKAGE_MANAGER" install --global "$PACKAGE_NAME"

if ! command -v "$APP_COMMAND" >/dev/null 2>&1; then
    echo "✗ ${APP_NAME} installation failed."
    exit 1
fi

echo "✓ ${APP_NAME} installed successfully: $($APP_COMMAND --version)"
