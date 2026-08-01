#!/usr/bin/env bash

set -euo pipefail

if (($# == 0)); then
    exec launch-terminal-command "$PWD" nvim
fi

files=("$@")
working_directory="$(dirname -- "${files[0]}")"

if [[ ! -d "$working_directory" ]]; then
    echo "Unable to determine the directory of: ${files[0]}" >&2
    exit 1
fi

exec launch-terminal-command "$working_directory" nvim "${files[@]}"
