#!/usr/bin/env bash
# Installing watched QML requires the same coherent cohort and explicit approval.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec bash "$SCRIPT_DIR/../session-manager/install_desktop_integration.sh" "$@"
