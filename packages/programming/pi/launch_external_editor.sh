#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $(basename "$0") <file>" >&2
    exit 2
fi

if ! command -v nvim >/dev/null 2>&1; then
    echo "Neovim is required to edit Pi messages." >&2
    exit 1
fi

if command -v xdg-terminal-exec >/dev/null 2>&1; then
    exec xdg-terminal-exec nvim "$1"
fi

if [[ -n "${TERMINAL:-}" ]]; then
    read -r -a terminal_command <<< "$TERMINAL"

    if command -v "${terminal_command[0]}" >/dev/null 2>&1; then
        exec "${terminal_command[@]}" -e nvim "$1"
    fi
fi

echo "Unable to find the default terminal." >&2
echo "Set the TERMINAL environment variable or install xdg-terminal-exec." >&2
exit 1
