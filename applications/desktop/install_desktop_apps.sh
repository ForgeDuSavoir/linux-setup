#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/grim/install_grim.sh"
"$SCRIPT_DIR/slurp/install_slurp.sh"
"$SCRIPT_DIR/wl-clipboard/install_wl-clipboard.sh"
"$SCRIPT_DIR/swappy/install_swappy.sh"
"$SCRIPT_DIR/satty/install_satty.sh"
"$SCRIPT_DIR/topgrade/install_topgrade.sh"
"$SCRIPT_DIR/wlsunset/install_wlsunset.sh"
"$SCRIPT_DIR/brave-origin/install_brave-origin.sh"
"$SCRIPT_DIR/easyeffects/install_easyeffects.sh"
"$SCRIPT_DIR/lsp-plugins/install_lsp-plugins.sh"
