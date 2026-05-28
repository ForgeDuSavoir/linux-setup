#!/usr/bin/env bash

set -euo pipefail

echo "==> Launching OBS..."

obs \
    --collection "Gaming" \
    >/dev/null 2>&1 &