#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PI_ROOT="$(npm root -g)/@earendil-works/pi-coding-agent"
ESBUILD="${PI_ROOT}/node_modules/.bin/esbuild"
BUNDLE="$(mktemp --suffix=.mjs)"

cleanup() {
    rm -f -- "$BUNDLE"
}
trap cleanup EXIT

if [[ ! -x "$ESBUILD" ]]; then
    echo "Pi's bundled esbuild was not found: $ESBUILD" >&2
    exit 1
fi

export NODE_PATH="${PI_ROOT}/node_modules"
"$ESBUILD" "${SCRIPT_DIR}/conversation_navigation.test.ts" \
    --bundle \
    --platform=node \
    --format=esm \
    --outfile="$BUNDLE" \
    >/dev/null
node --test "$BUNDLE"
