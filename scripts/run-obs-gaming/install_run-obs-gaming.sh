#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# Publish only a project override, never a global profile-specific desktop entry.
exec python3 "${SCRIPT_DIR}/../../configs/obs/install_project_launchers.py" --apply --only qmk "$@"
