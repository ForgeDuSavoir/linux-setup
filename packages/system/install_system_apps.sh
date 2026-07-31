#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/flatpak/install_flatpak.sh"
"$SCRIPT_DIR/curl/install_curl.sh"
"$SCRIPT_DIR/ripgrep/install_ripgrep.sh"
"$SCRIPT_DIR/fd/install_fd.sh"
"$SCRIPT_DIR/fzf/install_fzf.sh"
"$SCRIPT_DIR/yazi/install_yazi.sh"
"$SCRIPT_DIR/zoxide/install_zoxide.sh"
"$SCRIPT_DIR/pipx/install_pipx.sh"
"$SCRIPT_DIR/qt-wayland/install_qt-wayland.sh"
"$SCRIPT_DIR/flatseal/install_flatseal.sh"
"$SCRIPT_DIR/snap-pac/install_snap-pac.sh"
"$SCRIPT_DIR/alacritty/install_alacritty.sh"
"$SCRIPT_DIR/xdg-desktop-portal-gtk/install_xdg-desktop-portal-gtk.sh"
"$SCRIPT_DIR/xdg-user-dirs/install_xdg-user-dirs.sh"
"$SCRIPT_DIR/gnome-disks/install_gnome-disks.sh"
"$SCRIPT_DIR/filesystem-interop/install_filesystem-interop.sh"
"$SCRIPT_DIR/bluetooth/install_bluetooth.sh"
"$SCRIPT_DIR/wev/install_wev.sh"
"$SCRIPT_DIR/gnome-keyring/install_gnome-keyring.sh"
