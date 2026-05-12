#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/flatpak/install_flatpak.sh"
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

