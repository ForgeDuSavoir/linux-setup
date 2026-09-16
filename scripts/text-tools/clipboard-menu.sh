#!/usr/bin/env bash

set -euo pipefail

for command in cliphist rofi wl-copy wtype; do
    if ! command -v "${command}" >/dev/null 2>&1; then
        printf '✗ %s is required.\n' "${command}" >&2
        exit 1
    fi
done

set +e
entry="$(cliphist list | rofi -dmenu -i -p "Clipboard" \
    -theme "${HOME}/.config/rofi/project-launcher.rasi" \
    -kb-accept-alt "" \
    -kb-custom-1 "Shift+Return")"
rofi_status=$?
set -e

case "${rofi_status}" in
    0)
        paste_without_formatting=false
        ;;
    10)
        paste_without_formatting=true
        ;;
    *)
        exit 0
        ;;
esac

[[ -n "${entry}" ]] || exit 0

cliphist decode <<< "${entry}" | wl-copy --type text/plain

# Let Rofi restore focus to the previously active application before pasting.
sleep 0.1

if "${paste_without_formatting}"; then
    wtype -M ctrl -M shift -k v -m shift -m ctrl
else
    wtype -M ctrl -k v -m ctrl
fi
