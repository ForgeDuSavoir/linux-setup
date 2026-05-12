#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/meld/install_meld.sh"
"$SCRIPT_DIR/adb/install_adb.sh"
"$SCRIPT_DIR/scrcpy/install_scrcpy.sh"
"$SCRIPT_DIR/build-tools/install_build-tools.sh"
"$SCRIPT_DIR/vscodium/install_vscodium.sh"

