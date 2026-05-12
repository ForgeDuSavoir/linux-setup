#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/system/install_system_apps.sh"

"$SCRIPT_DIR/desktop/install_desktop_apps.sh"
"$SCRIPT_DIR/communication/install_communication_apps.sh"
"$SCRIPT_DIR/entertainment/install_entertainment_apps.sh"
"$SCRIPT_DIR/media/install_media_apps.sh"
"$SCRIPT_DIR/networking/install_networking_apps.sh"
"$SCRIPT_DIR/office/install_office_apps.sh"
"$SCRIPT_DIR/productivity/install_productivity_apps.sh"
"$SCRIPT_DIR/programming/install_programming_apps.sh"
"$SCRIPT_DIR/security/install_security_apps.sh"
"$SCRIPT_DIR/theming/install_theming.sh"
"$SCRIPT_DIR/optionals/install_optionals.sh"

echo
echo "✓ All application categories installed successfully."
