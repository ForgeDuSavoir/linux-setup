#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Installing custom scripts..."

bash "${SCRIPT_DIR}/git-push/install_git-push.sh"
bash "${SCRIPT_DIR}/safe-update/install_safe-update.sh"
bash "${SCRIPT_DIR}/rollback-snapshot/install_rollback-snapshot.sh"

echo "✓ Custom scripts installed successfully."