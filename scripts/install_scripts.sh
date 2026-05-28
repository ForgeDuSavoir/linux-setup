#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Installing custom scripts..."

bash "${SCRIPT_DIR}/git-push/install_git-push.sh"

bash "${SCRIPT_DIR}/safe-update/install_safe-update.sh"
bash "${SCRIPT_DIR}/rollback-snapshot/install_rollback-snapshot.sh"

bash "${SCRIPT_DIR}/run-obs-fds/install_run-obs-fds.sh"
bash "${SCRIPT_DIR}/run-obs-gaming/install_run-obs-gaming.sh"

bash "${SCRIPT_DIR}/concat-mp4/install_concat-mp4.sh"
bash "${SCRIPT_DIR}/pre-edit/install_pre-edit.sh"

echo "✓ Custom scripts installed successfully."