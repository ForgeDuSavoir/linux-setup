#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/obsidian/install_obsidian.sh"
"$SCRIPT_DIR/todoist/install_todoist.sh"
