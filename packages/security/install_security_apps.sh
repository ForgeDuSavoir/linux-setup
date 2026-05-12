#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/keepass/install_keepass.sh"
"$SCRIPT_DIR/snapper/install_snapper.sh"
