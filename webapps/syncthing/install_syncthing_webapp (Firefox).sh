#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="syncthing"
APP_NAME="Syncthing WebApp"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

PROFILE_PATH="$HOME/.local/share/webapps/${WEBAPP_NAME}/firefox-profile"
DESKTOP_FILE_NAME="${WEBAPP_NAME}.desktop"
ICON_FILE_NAME="${WEBAPP_NAME}.svg"

echo "==> Installing ${APP_NAME}..."

if ! command -v syncthing >/dev/null 2>&1; then
    echo "✗ Syncthing is not installed."
    echo "Install Syncthing before installing this webapp."
    exit 1
fi

if ! command -v firefox >/dev/null 2>&1; then
    echo "✗ Firefox is not installed."
    exit 1
fi

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

echo "==> Creating isolated Firefox profile..."

"$WEBAPPS_DIR/create_firefox_profile.sh" "$WEBAPP_NAME"

echo "==> Installing desktop entry..."

sed "s|__PROFILE_PATH__|$PROFILE_PATH|g" \
    "$SCRIPT_DIR/${WEBAPP_NAME}.desktop" \
    > "$DESKTOP_DIR/${DESKTOP_FILE_NAME}"

echo "==> Installing icon..."

cp \
    "$SCRIPT_DIR/${WEBAPP_NAME}.svg" \
    "$ICON_DIR/${ICON_FILE_NAME}"

update-desktop-database "$DESKTOP_DIR" || true

echo "✓ ${APP_NAME} installed successfully."
