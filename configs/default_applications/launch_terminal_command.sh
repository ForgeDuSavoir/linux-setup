#!/usr/bin/env bash

set -euo pipefail

if (($# < 2)); then
    echo "Usage: $(basename "$0") <working-directory> <command> [arguments...]" >&2
    exit 1
fi

working_directory="$1"
shift

if [[ ! -d "${working_directory}" ]]; then
    echo "Working directory not found: ${working_directory}" >&2
    exit 1
fi

cd -- "${working_directory}"

if command -v xdg-terminal-exec >/dev/null 2>&1; then
    exec xdg-terminal-exec "$@"
fi

if command -v x-terminal-emulator >/dev/null 2>&1; then
    exec x-terminal-emulator -e "$@"
fi

if [[ -n "${TERMINAL:-}" ]]; then
    read -r -a terminal_command <<< "${TERMINAL}"

    if command -v "${terminal_command[0]}" >/dev/null 2>&1; then
        exec "${terminal_command[@]}" -e "$@"
    fi
fi

echo "Unable to find the default terminal." >&2
echo "Set TERMINAL, configure x-terminal-emulator, or install xdg-terminal-exec." >&2
exit 1
