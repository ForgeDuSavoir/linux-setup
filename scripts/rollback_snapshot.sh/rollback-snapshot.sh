#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="root"

echo "==> Available Snapper snapshots:"
sudo snapper -c "$CONFIG_NAME" list

echo
read -r -p "Enter snapshot ID to rollback to: " SNAPSHOT_ID

if [[ -z "$SNAPSHOT_ID" ]]; then
    echo "✗ Snapshot ID cannot be empty."
    exit 1
fi

echo
echo "⚠ You are about to rollback to snapshot: $SNAPSHOT_ID"
read -r -p "Continue? [y/N]: " confirm

case "$confirm" in
    y|Y|yes|YES)
        sudo snapper -c "$CONFIG_NAME" rollback "$SNAPSHOT_ID"
        echo
        echo "✓ Rollback prepared."
        echo "Reboot now with:"
        echo "  sudo reboot"
        ;;
    *)
        echo "Rollback cancelled."
        ;;
esac