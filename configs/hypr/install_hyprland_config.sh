#!/usr/bin/env bash
# Preserve personal extra files. Publish native helpers/Lua/QML through one coordinator.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bash "$SCRIPT_DIR/../session-manager/install_desktop_integration.sh" --preflight "$@"
bash "$SCRIPT_DIR/install_fit-scroller_layout.sh"
bash "$SCRIPT_DIR/../session-manager/install_desktop_integration.sh" "$@"
