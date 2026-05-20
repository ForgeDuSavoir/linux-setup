#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="google-calendar"
APP_NAME="Calendar"
WEBAPP_URL="https://calendar.google.com/"
APP_COMMENT="Google Agenda WebApp"
CATEGORIES="Office;Calendar;"

BROWSER_COMMAND="chromium"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

PROFILE_PATH="$HOME/.local/share/webapps/${WEBAPP_NAME}/chromium-profile"
DESKTOP_FILE_NAME="${WEBAPP_NAME}.desktop"
ICON_FILE_NAME="${WEBAPP_NAME}.svg"

echo "==> Installing ${APP_NAME}..."

if [[ -z "$WEBAPP_NAME" || -z "$APP_NAME" || -z "$WEBAPP_URL" || -z "$CATEGORIES" ]]; then
    echo "✗ WEBAPP_NAME, APP_NAME, WEBAPP_URL and CATEGORIES must be set."
    exit 1
fi

if [[ -z "$APP_COMMENT" ]]; then
    APP_COMMENT="$APP_NAME"
fi


if ! command -v "$BROWSER_COMMAND" >/dev/null 2>&1; then
    echo "✗ Chromium is not installed or command '${BROWSER_COMMAND}' was not found."
    exit 1
fi

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$PROFILE_PATH"

echo "==> Installing desktop entry..."

sed \
    -e "s|__APP_NAME__|$APP_NAME|g" \
    -e "s|__APP_COMMENT__|$APP_COMMENT|g" \
    -e "s|__WEBAPP_NAME__|$WEBAPP_NAME|g" \
    -e "s|__WEBAPP_URL__|$WEBAPP_URL|g" \
    -e "s|__BROWSER_COMMAND__|$BROWSER_COMMAND|g" \
    -e "s|__PROFILE_PATH__|$PROFILE_PATH|g" \
    -e "s|__CATEGORIES__|$CATEGORIES|g" \
    "$SCRIPT_DIR/${WEBAPP_NAME}.desktop" \
    > "$DESKTOP_DIR/${DESKTOP_FILE_NAME}"

echo "==> Installing icon..."

cp \
    "$SCRIPT_DIR/${WEBAPP_NAME}.svg" \
    "$ICON_DIR/${ICON_FILE_NAME}"

update-desktop-database "$DESKTOP_DIR" || true

echo "✓ ${APP_NAME} installed successfully."