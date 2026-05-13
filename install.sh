#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "==> Starting linux-setup installation..."

echo "==> Making shell scripts executable..."
find "${REPO_DIR}" -type f -name "*.sh" -exec chmod +x {} \;

echo ""
echo "==> Installing packages..."
bash "${REPO_DIR}/packages/install_packages.sh"

echo ""
echo "==> Installing configs..."
bash "${REPO_DIR}/configs/install_configs.sh"

echo ""
echo "✓ linux-setup installation completed successfully."
