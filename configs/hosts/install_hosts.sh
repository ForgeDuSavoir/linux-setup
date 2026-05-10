#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE_HOSTS_FILE="$SCRIPT_DIR/hosts.private"
MARKER_START="# linux-setup hosts start"
MARKER_END="# linux-setup hosts end"

echo "==> Configuring /etc/hosts..."

if [[ ! -f "$PRIVATE_HOSTS_FILE" ]]; then
    echo "✗ Missing private hosts file:"
    echo "  $PRIVATE_HOSTS_FILE"
    echo
    echo "Create it from:"
    echo "  $SCRIPT_DIR/hosts.private.example"
    exit 1
fi

sudo sed -i "/$MARKER_START/,/$MARKER_END/d" /etc/hosts

{
    echo "$MARKER_START"
    cat "$PRIVATE_HOSTS_FILE"
    echo "$MARKER_END"
} | sudo tee -a /etc/hosts >/dev/null

echo "✓ /etc/hosts configured successfully."
