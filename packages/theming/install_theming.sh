#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Optional applications"
read -r -p "Do you want to install themes? [y/N]: " answer

case "${answer}" in
    y|Y|yes|YES)
        echo "==> Installing theming..."

        "$SCRIPT_DIR/fonts/install_fonts.sh"
        "$SCRIPT_DIR/theme/install_theme.sh"
        "$SCRIPT_DIR/qt6ct/install_qt6ct.sh"
        "$SCRIPT_DIR/starship/install_starship.sh"

        echo ""
        echo "✓ Optional themes installed."
        ;;
    *)
        echo "↪ Skipping optional themes."
        ;;
esac

exit 0
