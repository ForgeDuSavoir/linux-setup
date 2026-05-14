#!/usr/bin/env bash

set -euo pipefail

APP_NAME="ZeroTier One"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="$SCRIPT_DIR/.env"

echo "==> Configuring ${APP_NAME}..."

if ! command -v zerotier-cli >/dev/null 2>&1; then
    echo "✗ ZeroTier One is not installed."
    echo "Install it before running this script."
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

# Load environment variables
set -a
source "$ENV_FILE"
set +a

if [[ -z "${ZEROTIER_NETWORK_ID:-}" ]]; then
    echo "✗ ZEROTIER_NETWORK_ID is missing in .env"
    exit 1
fi

echo "==> Ensuring zerotier-one service is running..."

sudo systemctl enable --now zerotier-one.service

echo "==> Checking ZeroTier network..."

if sudo zerotier-cli listnetworks | grep -q "$ZEROTIER_NETWORK_ID"; then
    echo "✓ Already joined ZeroTier network."
else
    echo "==> Joining ZeroTier network..."
    sudo zerotier-cli join "$ZEROTIER_NETWORK_ID"

    echo
    echo "==> Action required:"
    echo "Go to https://www.zerotier.com/"
    echo "Then:"
    echo "  1. Log in"
    echo "  2. Open your network"
    echo "  3. Find the unknown/new device"
    echo "  4. Check 'Authorized'"
    echo "  5. Set a name and description"
    echo "  6. Save"
    echo
    read -r -p "Press Enter once this device has been authorized in ZeroTier Central..."
fi

echo
echo "Current networks:"
sudo zerotier-cli listnetworks

echo
echo "✓ ${APP_NAME} configured successfully."
echo
