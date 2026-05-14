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

CURRENT_HOSTS="$(mktemp)"
NEW_HOSTS="$(mktemp)"

trap 'rm -f "$CURRENT_HOSTS" "$NEW_HOSTS"' EXIT

sudo cp /etc/hosts "$CURRENT_HOSTS"

sed "/$MARKER_START/,/$MARKER_END/d" "$CURRENT_HOSTS" > "$NEW_HOSTS"

{
    echo "$MARKER_START"
    cat "$PRIVATE_HOSTS_FILE"
    echo "$MARKER_END"
} >> "$NEW_HOSTS"

if cmp -s "$CURRENT_HOSTS" "$NEW_HOSTS"; then
    echo "✓ /etc/hosts is already up to date."
    exit 0
fi

sudo cp "$NEW_HOSTS" /etc/hosts

echo "✓ /etc/hosts configured successfully."