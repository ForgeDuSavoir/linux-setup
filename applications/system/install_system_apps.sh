#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/flatpak/install_flatpak.sh"
"$SCRIPT_DIR/pipx/install_pipx.sh"
"$SCRIPT_DIR/qt-wayland/install_qt-wayland.sh"
"$SCRIPT_DIR/flatseal/install_flatseal.sh"
"$SCRIPT_DIR/snap-pac/install_snap-pac.sh"
