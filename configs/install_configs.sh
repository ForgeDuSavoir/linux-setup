#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/git/configure_git.sh"
"$SCRIPT_DIR/hosts/install_hosts.sh"
"$SCRIPT_DIR/logind/configure_logind.sh"
"$SCRIPT_DIR/hypr/install_hyprland_config.sh"
"$SCRIPT_DIR/quickshell/install_quickshell_config.sh"
"$SCRIPT_DIR/quickshell/install_notification_server.sh"
"$SCRIPT_DIR/starship/install_starship_config.sh"
"$SCRIPT_DIR/yazi/install_yazi_config.sh"
"$SCRIPT_DIR/theme/apply_theme.sh"
"$SCRIPT_DIR/thunar/configure_thunar.sh"
"$SCRIPT_DIR/zerotier/configure_zerotier.sh"

"$SCRIPT_DIR/snapper/configure_snapper.sh"
"$SCRIPT_DIR/topgrade/configure_topgrade.sh"

"$SCRIPT_DIR/obs/configure_obs.sh"
#"$SCRIPT_DIR/kdenlive/configure_kdenlive.sh" #Not yet working

echo
echo "✓ All configurations installed successfully."
echo "⚠ A restart is required for systemd-logind to apply the lid-switch configuration."
