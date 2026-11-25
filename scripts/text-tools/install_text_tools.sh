#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET_DIR="${HOME}/.local/bin"

scripts=(dictation-start dictation-stop dictation-toggle text-insert clipboard-menu)
if [[ $# -eq 1 && "$1" == --dictation-stop-only ]]; then
    scripts=(dictation-stop)
elif [[ $# -ne 0 ]]; then
    echo "Usage: $0 [--dictation-stop-only]" >&2
    exit 2
fi

for script_name in "${scripts[@]}"; do
    source_file="${SCRIPT_DIR}/${script_name}.sh"
    target_file="${TARGET_DIR}/${script_name}"

    if [[ ! -f "${source_file}" ]]; then
        echo "✗ Missing source file: ${source_file}"
        exit 1
    fi

    mkdir -p "${TARGET_DIR}"
    [[ ! -L "${target_file}" ]] || { echo "Refusing symlinked target: ${target_file}" >&2; exit 1; }
    temporary="$(mktemp "${TARGET_DIR}/.${script_name}.XXXXXXXX")"
    trap 'rm -f -- "${temporary}"' EXIT
    install -m 0755 "${source_file}" "${temporary}"
    mv -f -- "${temporary}" "${target_file}"
    trap - EXIT
done

echo "✓ Text tools scripts installed successfully."
