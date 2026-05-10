#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="${1:-}"

if [[ -z "$WEBAPP_NAME" ]]; then
    echo "Usage:"
    echo "  create_firefox_profile.sh <webapp-name>"
    exit 1
fi

PROFILE_DIR="$HOME/.local/share/webapps/${WEBAPP_NAME}/firefox-profile"

echo "==> Creating Firefox profile for ${WEBAPP_NAME}..."

if ! command -v firefox >/dev/null 2>&1; then
    echo "✗ Firefox is not installed."
    exit 1
fi

if [[ -d "$PROFILE_DIR" ]]; then
    echo "✓ Firefox profile already exists:"
    echo "  $PROFILE_DIR"
    exit 0
fi

mkdir -p "$PROFILE_DIR"

firefox \
    -CreateProfile "${WEBAPP_NAME} ${PROFILE_DIR}"

rm -f "$PROFILE_DIR/xulstore.json"

echo "✓ Firefox profile created successfully."
echo "  $PROFILE_DIR"
