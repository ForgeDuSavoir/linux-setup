#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET_DIR="${HOME}/.local/bin"

for script_name in dictation-start dictation-stop dictation-toggle text-insert clipboard-menu; do
    source_file="${SCRIPT_DIR}/${script_name}.sh"
    target_file="${TARGET_DIR}/${script_name}"

    if [[ ! -f "${source_file}" ]]; then
        echo "✗ Missing source file: ${source_file}"
        exit 1
    fi

    mkdir -p "${TARGET_DIR}"
    install -m 0755 "${source_file}" "${target_file}"
done

echo "✓ Text tools scripts installed successfully."
