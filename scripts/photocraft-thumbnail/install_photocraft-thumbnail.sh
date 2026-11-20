#!/usr/bin/env bash
# Existing no-argument setup entry point still applies; Python is installer-only.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ $# == 0 ]]; then set -- --apply; fi
exec python3 "$SCRIPT_DIR/../../runtime/install_thumbnail.py" "$@"
