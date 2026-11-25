#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "${1:-}" == --sleep-key-only && "$#" == 1 ]]; then
    exec sudo bash "${SCRIPT_DIR}/configure_sleep_key.sh"
elif [[ "$#" != 0 ]]; then
    echo "Usage: $0 [--sleep-key-only]" >&2; exit 2
fi
TARGET_FILE="/etc/systemd/logind.conf.d/ignore-lid.conf"
TEMP_FILE="$(mktemp)"
trap 'rm -f "$TEMP_FILE"' EXIT

cat > "$TEMP_FILE" <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
EOF

if [[ -f "$TARGET_FILE" ]] && cmp -s "$TEMP_FILE" "$TARGET_FILE"; then
    echo "✓ Lid switch is already configured to be ignored."
else
    echo "==> Configuring logind to ignore the lid switch..."
    sudo install -d -m 755 /etc/systemd/logind.conf.d
    sudo install -m 644 "$TEMP_FILE" "$TARGET_FILE"
    echo "✓ Lid switch configured to be ignored."
fi

sudo bash "${SCRIPT_DIR}/configure_sleep_key.sh"
