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

echo "==> Joining ZeroTier network..."

sudo zerotier-cli join "$ZEROTIER_NETWORK_ID"

echo
echo "✓ ${APP_NAME} configured successfully."
echo
echo "Current networks:"
zerotier-cli listnetworks
