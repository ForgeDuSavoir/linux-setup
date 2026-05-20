#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="youtube-fds"
APP_NAME="YouTube (Forge du Savoir)"
APP_COMMENT="YouTube Webapp for Forge du Savoir account"
CATEGORIES="Network;Media;"
WEBAPP_URL="https://www.youtube.com/"
ICON_EXTENSION="svg"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

PROFILE_PATH="$HOME/.local/share/webapps/${WEBAPP_NAME}/firefox-profile"

DESKTOP_FILE_NAME="${WEBAPP_NAME}.desktop"
ICON_FILE_NAME="${WEBAPP_NAME}.${ICON_EXTENSION}"

FIREFOX_COMMAND="firefox --no-remote --profile \"$PROFILE_PATH\" --new-window \"$WEBAPP_URL\""

echo "==> Installing ${APP_NAME}..."

if [[ -z "$WEBAPP_NAME" || -z "$APP_NAME" || -z "$WEBAPP_URL" || -z "$CATEGORIES" ]]; then
    echo "✗ WEBAPP_NAME, APP_NAME, WEBAPP_URL and CATEGORIES must be set."
    exit 1
fi

if [[ -z "$APP_COMMENT" ]]; then
    APP_COMMENT="$APP_NAME"
fi

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$PROFILE_PATH"

echo "==> Installing desktop entry..."

sed \
    -e "s|__APP_NAME__|$APP_NAME|g" \
    -e "s|__APP_COMMENT__|$APP_COMMENT|g" \
    -e "s|__WEBAPP_NAME__|$WEBAPP_NAME|g" \
    -e "s|__FIREFOX_COMMAND__|$FIREFOX_COMMAND|g" \
    -e "s|__CATEGORIES__|$CATEGORIES|g" \
    "$SCRIPT_DIR/${WEBAPP_NAME}.desktop" \
    > "$DESKTOP_DIR/${DESKTOP_FILE_NAME}"

echo "==> Installing icon..."

cp \
    "$SCRIPT_DIR/${WEBAPP_NAME}.${ICON_EXTENSION}" \
    "$ICON_DIR/${ICON_FILE_NAME}"

update-desktop-database "$DESKTOP_DIR" || true

echo "==> Creating isolated Firefox profile..."

"$WEBAPPS_DIR/create_firefox_profile.sh" "$WEBAPP_NAME"

echo "==> Applying Firefox profile preferences..."

cat > "$PROFILE_PATH/user.js" <<'EOF'
user_pref("browser.startup.page", 3);
EOF

echo "==> Installing Firefox addons..."

if [[ -d "$SCRIPT_DIR/extensions" ]]; then
    mkdir -p "$PROFILE_PATH/extensions"

    cp -r "$SCRIPT_DIR/extensions/." \
          "$PROFILE_PATH/extensions/"
fi

echo "✓ ${APP_NAME} installed successfully."