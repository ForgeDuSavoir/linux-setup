#!/usr/bin/env bash

set -euo pipefail

if (( $# != 0 )); then
    echo "Usage: text-insert < text" >&2
    exit 1
fi

if ! command -v wtype >/dev/null 2>&1; then
    echo "✗ wtype is required." >&2
    exit 1
fi

input_file="$(mktemp)"
trap 'rm -f "${input_file}"' EXIT

cat > "${input_file}"

if [[ ! -s "${input_file}" ]]; then
    echo "✗ No text provided on standard input." >&2
    exit 1
fi

if ! wtype - < "${input_file}"; then
    echo "✗ Unable to insert text into the active window." >&2
    exit 1
fi

notify-send "Texte" "Texte inséré." >/dev/null 2>&1 || true
