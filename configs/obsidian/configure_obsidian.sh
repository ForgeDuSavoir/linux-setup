#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
python3 "${SCRIPT_DIR}/../../runtime/install_obsidian.py" --apply
