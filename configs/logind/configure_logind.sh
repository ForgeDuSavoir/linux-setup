#!/usr/bin/env bash

set -euo pipefail

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

echo "⚠ A restart is required for systemd-logind to apply this configuration."
