#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/syncthing/install_syncthing.sh"
"$SCRIPT_DIR/zerotier-one/install_zerotier-one.sh"
"$SCRIPT_DIR/nordvpn/install_nordvpn.sh"
