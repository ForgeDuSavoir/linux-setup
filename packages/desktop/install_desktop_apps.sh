#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/brave-origin/install_brave-origin.sh"
"$SCRIPT_DIR/easyeffects/install_easyeffects.sh"
"$SCRIPT_DIR/grim/install_grim.sh"
"$SCRIPT_DIR/hypridle/install_hypridle.sh"
"$SCRIPT_DIR/hyprpolkitagent/install_hyprpolkitagent.sh"
"$SCRIPT_DIR/hyprlock/install_hyprlock.sh"
"$SCRIPT_DIR/loupe/install_loupe.sh"
"$SCRIPT_DIR/lsp-plugins/install_lsp-plugins-lv2.sh"
"$SCRIPT_DIR/mission-center/install_mission-center.sh"
"$SCRIPT_DIR/mousepad/install_mousepad.sh"
"$SCRIPT_DIR/noctalia/install_noctalia.sh"
"$SCRIPT_DIR/nwg-look/install_nwg-look.sh"
"$SCRIPT_DIR/pavucontrol/install_pavucontrol.sh"
"$SCRIPT_DIR/playerctl/install_playerctl.sh"
"$SCRIPT_DIR/satty/install_satty.sh"
"$SCRIPT_DIR/slurp/install_slurp.sh"
"$SCRIPT_DIR/thunar/install_thunar.sh"
"$SCRIPT_DIR/topgrade/install_topgrade.sh"
"$SCRIPT_DIR/wl-clipboard/install_wl-clipboard.sh"
"$SCRIPT_DIR/wlsunset/install_wlsunset.sh"

