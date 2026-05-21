#!/usr/bin/env bash

set -euo pipefail

CONFIG_DIR="${HOME}/.config"
CONFIG_FILE="${CONFIG_DIR}/topgrade.toml"

echo "==> Configuring Topgrade..."

if ! command -v topgrade >/dev/null 2>&1; then
    echo "✗ topgrade is not installed."
    exit 1
fi

mkdir -p "${CONFIG_DIR}"

cat > "${CONFIG_FILE}" <<'EOF'
[misc]
assume_yes = true
disable = [
    "firmware",
    "config_update"
]
EOF

echo "✓ Topgrade configured successfully:"
echo "  ${CONFIG_FILE}"