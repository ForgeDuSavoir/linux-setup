#!/usr/bin/env bash

set -euo pipefail

LOCK_FILE="/tmp/safe-update.lock"

exec 200>"$LOCK_FILE"

if ! flock -n 200; then
    notify-send \
      -u normal \
      "Safe update" \
      "An update is already running."

    echo "✗ Another safe-update instance is already running."
    exit 1
fi

SNAPSHOT_DESC="Before system update $(date '+%Y-%m-%d %H:%M:%S')"
LOG_DIR="${HOME}/.local/state/linux-setup/logs"
LOG_FILE="${LOG_DIR}/safe-update-$(date '+%Y%m%d-%H%M%S').log"

mkdir -p "$LOG_DIR"

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "$1" "$2"
    fi
}

stop_sudo_keepalive() {
    kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    wait "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
}

echo "==> Safe system update"
echo "Log: $LOG_FILE"

echo "==> Requesting sudo access..."
sudo -v
echo "✓ Sudo access granted."

while true; do
    sudo -n -v
    sleep 60
done 200>&- 2>/dev/null &
SUDO_KEEPALIVE_PID=$!
trap stop_sudo_keepalive EXIT

notify "Safe update" "Creating Btrfs snapshot..."

run_update() {
    local failed=0

    echo "==> Safe system update"
    echo "==> Creating Btrfs snapshot..."
    if ! sudo snapper create --description "$SNAPSHOT_DESC" --type single; then
        echo "✗ Snapshot creation failed; no updates were started."
        notify "Safe update failed" "Snapshot creation failed; check the log."
        return 1
    fi
    echo "✓ Snapshot created."
    notify "Safe update" "Snapshot created. Starting updates..."

    echo
    echo "==> Running topgrade..."
    if ! topgrade; then
        echo "✗ Topgrade failed."
        failed=1
    fi

    echo
    echo "==> Synchronizing ArtCraft releases..."
    if ! command -v sync-artcraft-releases >/dev/null 2>&1; then
        echo "✗ sync-artcraft-releases is missing; ArtCraft packages were not updated."
        failed=1
    elif ! sync-artcraft-releases; then
        echo "✗ ArtCraft release synchronization failed; skipping package installation."
        failed=1
    elif ! command -v install-artcraft-releases >/dev/null 2>&1; then
        echo "✗ install-artcraft-releases is missing; ArtCraft packages were not updated."
        failed=1
    else
        echo
        echo "==> Installing ArtCraft Arch packages..."
        if ! install-artcraft-releases; then
            echo "✗ ArtCraft package installation failed."
            failed=1
        fi
    fi

    if [[ -f /var/run/reboot-required ]]; then
        echo
        echo "⚠ Reboot is recommended."
    else
        echo
        echo "✓ No reboot-required file found."
    fi

    echo
    echo "Available snapshots:"
    if ! sudo snapper list; then
        echo "✗ Could not list snapshots."
        failed=1
    fi

    if (( failed )); then
        if command -v notify-send >/dev/null 2>&1; then
            notify-send -u critical "Safe update failed" "Some updates failed; check $LOG_FILE."
        fi
        return 1
    fi
    notify "Safe update completed" "Updates finished successfully."
}

update_status=0
run_update 2>&1 | tee "$LOG_FILE" || update_status=1

echo
read -r -p "Press Enter to close..." || true
exit "$update_status"
