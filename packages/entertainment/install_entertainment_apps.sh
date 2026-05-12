#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/vlc/install_vlc.sh"
"$SCRIPT_DIR/steam/install_steam.sh"
