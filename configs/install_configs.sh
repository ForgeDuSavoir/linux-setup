#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/hosts/install_hosts.sh"
"$SCRIPT_DIR/noctalia/install_noctalia_config.sh"
"$SCRIPT_DIR/starship/install_starship_config.sh"
"$SCRIPT_DIR/zerotier/configure_zerotier.sh"

echo
echo "✓ All configurations installed successfully."
