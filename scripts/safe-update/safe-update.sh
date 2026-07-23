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
done 2>/dev/null &
SUDO_KEEPALIVE_PID=$!
trap stop_sudo_keepalive EXIT

notify "Safe update" "Creating Btrfs snapshot..."

{
    echo "==> Safe system update"
    echo "==> Creating Btrfs snapshot..."

    sudo snapper create \
        --description "$SNAPSHOT_DESC" \
        --type single

    echo "✓ Snapshot created."

    notify "Safe update" "Snapshot created. Starting updates..."

    echo
    echo "==> Running topgrade..."

	if topgrade; then
	    notify "Safe update completed" "Updates finished successfully."
	else
	    notify-send \
	      -u critical \
	      "Safe update failed" \
	      "Check logs for details."

	    echo
	    echo "✗ Topgrade failed."
	fi

    if [[ -f /var/run/reboot-required ]]; then
        echo
        echo "⚠ Reboot is recommended."
        notify "Safe update completed" "Updates finished. Reboot is recommended."
    else
        echo
        echo "✓ No reboot-required file found."
        notify "Safe update completed" "Updates finished successfully."
    fi

    echo
    echo "Available snapshots:"
    sudo snapper list

} 2>&1 | tee "$LOG_FILE"

echo
read -r -p "Press Enter to close..."
