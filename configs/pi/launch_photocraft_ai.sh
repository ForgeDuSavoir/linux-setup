#!/usr/bin/env bash

set -euo pipefail

WORKSPACE="${HOME}/Pictures/PhotoCraft-AI"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/photocraft"
TOKEN_FILE="${STATE_DIR}/control.token"

if ! command -v photocraft >/dev/null 2>&1; then
    echo '✗ PhotoCraft is not installed.' >&2
    exit 1
fi

umask 077
mkdir -p "$WORKSPACE" "$STATE_DIR"
chmod 700 "$STATE_DIR"
# PhotoCraft generates a 0600 token if the file does not exist; never print it.
exec photocraft --control 7878 --control-token-file "$TOKEN_FILE" \
    --automation-read-root "$WORKSPACE" --automation-write-root "$WORKSPACE" "$@"
