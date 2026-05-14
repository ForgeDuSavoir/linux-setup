#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Installing custom scripts..."

bash "${SCRIPT_DIR}/git-push/install_git-push.sh"

echo "✓ Custom scripts installed successfully."