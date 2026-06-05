#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/beeper/install_beeper.sh"
"$SCRIPT_DIR/smile/install_smile.sh"
