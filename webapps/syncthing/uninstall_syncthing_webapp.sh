#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="syncthing"
APP_NAME="Syncthing WebApp"

DESKTOP_FILE="$HOME/.local/share/applications/${WEBAPP_NAME}.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/${WEBAPP_NAME}.svg"
PROFILE_DIR="$HOME/.local/share/webapps/${WEBAPP_NAME}"

echo "==> Uninstalling ${APP_NAME}..."

if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    echo "✓ Removed desktop entry."
fi

if [[ -f "$ICON_FILE" ]]; then
    rm -f "$ICON_FILE"
    echo "✓ Removed icon."
fi

if [[ -d "$PROFILE_DIR" ]]; then
    rm -rf "$PROFILE_DIR"
    echo "✓ Removed isolated Firefox profile."
fi

update-desktop-database "$HOME/.local/share/applications" || true

echo "✓ ${APP_NAME} uninstalled successfully."
