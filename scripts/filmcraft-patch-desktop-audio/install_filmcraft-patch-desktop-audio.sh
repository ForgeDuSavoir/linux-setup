#!/usr/bin/env bash
# Compatibility setup entry: no arguments still applies; Python is installer-only.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ $# == 0 ]]; then set -- --apply; fi
exec python3 "$SCRIPT_DIR/../../runtime/install_filmcraft_audio.py" "$@"
