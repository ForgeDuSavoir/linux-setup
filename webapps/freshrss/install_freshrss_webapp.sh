#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="freshrss"
APP_NAME="FreshRSS WebApp"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="$SCRIPT_DIR/.env"

DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
PROFILE_PATH="$HOME/.local/share/webapps/${WEBAPP_NAME}/firefox-profile"

DESKTOP_FILE_NAME="${WEBAPP_NAME}.desktop"
ICON_FILE_NAME="${WEBAPP_NAME}.svg"

echo "==> Installing ${APP_NAME}..."

if ! command -v firefox >/dev/null 2>&1; then
    echo "✗ Firefox is not installed."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✗ Missing .env file:"
    echo "  $ENV_FILE"
    echo
    echo "Create it from:"
    echo "  $SCRIPT_DIR/.env.example"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -z "${FRESHRSS_URL:-}" ]]; then
    echo "✗ FRESHRSS_URL is missing in .env"
    exit 1
fi

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

echo "==> Creating isolated Firefox profile..."

"$WEBAPPS_DIR/create_firefox_profile.sh" "$WEBAPP_NAME"

echo "==> Installing desktop entry..."

sed \
    -e "s|__PROFILE_PATH__|$PROFILE_PATH|g" \
    -e "s|__FRESHRSS_URL__|$FRESHRSS_URL|g" \
    "$SCRIPT_DIR/freshrss.desktop" \
    > "$DESKTOP_DIR/$DESKTOP_FILE_NAME"

echo "==> Installing icon..."

cp "$SCRIPT_DIR/${WEBAPP_NAME}.svg" "$ICON_DIR/$ICON_FILE_NAME"

update-desktop-database "$DESKTOP_DIR" || true

echo "✓ ${APP_NAME} installed successfully."
