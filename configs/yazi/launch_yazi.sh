#!/usr/bin/env bash

set -euo pipefail

cwd_file="$(mktemp "${XDG_RUNTIME_DIR:-/tmp}/yazi-cwd.XXXXXX")"

cleanup() {
    rm -f -- "${cwd_file}"
}
trap cleanup EXIT

if yazi --cwd-file "${cwd_file}" "$@"; then
    yazi_status=0
else
    yazi_status=$?
fi

if [[ -s "${cwd_file}" ]]; then
    working_directory="$(<"${cwd_file}")"
    if [[ -d "${working_directory}" ]]; then
        cd -- "${working_directory}"
    fi

    shell="${SHELL:-/bin/sh}"
    if [[ ! -x "${shell}" ]]; then
        shell="/bin/sh"
    fi

    exec "${shell}"
fi

exit "${yazi_status}"
