#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Optional applications"
read -r -p "Do you want to install optional applications? [y/N]: " answer

case "${answer}" in
    y|Y|yes|YES)
        echo "==> Installing optional applications..."

        "$SCRIPT_DIR/nwg-displays/install_nwg-displays.sh"
        "$SCRIPT_DIR/power-profiles-daemon/install_power-profiles-daemon.sh"

        echo ""
        echo "✓ Optional applications installed."
        ;;
    *)
        echo "↪ Skipping optional applications."
        ;;
esac

exit 0
