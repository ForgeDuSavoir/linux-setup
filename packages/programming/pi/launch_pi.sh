#!/usr/bin/env bash

set -euo pipefail

if command -v xdg-terminal-exec >/dev/null 2>&1; then
    exec xdg-terminal-exec pi
fi

if [[ -n "${TERMINAL:-}" ]]; then
    read -r -a terminal_command <<< "$TERMINAL"

    if command -v "${terminal_command[0]}" >/dev/null 2>&1; then
        exec "${terminal_command[@]}" -e pi
    fi
fi

echo "Unable to find the default terminal." >&2
echo "Set the TERMINAL environment variable or install xdg-terminal-exec." >&2
exit 1
