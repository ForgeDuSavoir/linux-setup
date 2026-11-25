#!/usr/bin/env bash
# Pi must wait for this editor, not hand the temporary file to an existing server.
set -euo pipefail
if [[ $# -ne 1 ]]; then
    echo "Usage: $(basename "$0") <file>" >&2
    exit 2
fi
command -v mousepad >/dev/null || { echo 'Mousepad is required to edit Pi messages.' >&2; exit 1; }
exec mousepad --disable-server --opening-mode=window -- "$1"
