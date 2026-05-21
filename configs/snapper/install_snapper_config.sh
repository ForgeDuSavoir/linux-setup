#!/usr/bin/env bash

set -euo pipefail

CONFIG_NAME="root"

echo "==> Configuring Snapper..."

if ! command -v snapper >/dev/null 2>&1; then
    echo "✗ snapper is not installed."
    exit 1
fi

if ! findmnt -no FSTYPE / | grep -q "^btrfs$"; then
    echo "✗ Root filesystem is not Btrfs."
    exit 1
fi

if sudo snapper list-configs | awk '{print $1}' | grep -qx "$CONFIG_NAME"; then
    echo "✓ Snapper config '$CONFIG_NAME' already exists."
else
    echo "==> Creating Snapper config '$CONFIG_NAME'..."
    sudo snapper -c "$CONFIG_NAME" create-config /
fi

echo "==> Applying Snapper settings..."

sudo sed -i \
    -e 's/^TIMELINE_CREATE=.*/TIMELINE_CREATE="yes"/' \
    -e 's/^TIMELINE_CLEANUP=.*/TIMELINE_CLEANUP="yes"/' \
    -e 's/^NUMBER_CLEANUP=.*/NUMBER_CLEANUP="yes"/' \
    -e 's/^NUMBER_MIN_AGE=.*/NUMBER_MIN_AGE="1800"/' \
    -e 's/^NUMBER_LIMIT=.*/NUMBER_LIMIT="10"/' \
    -e 's/^NUMBER_LIMIT_IMPORTANT=.*/NUMBER_LIMIT_IMPORTANT="5"/' \
    "/etc/snapper/configs/${CONFIG_NAME}"

echo "==> Enabling Snapper timers..."

sudo systemctl enable --now snapper-timeline.timer
sudo systemctl enable --now snapper-cleanup.timer

echo "✓ Snapper configured successfully."