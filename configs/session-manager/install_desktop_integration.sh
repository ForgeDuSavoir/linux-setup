#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
CONFIGS_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

# An old running daemon cannot serve session.deactivate. Do not expose the
# UUID scratchpad routing before the neutral menu works in the same login.
if command -v systemctl >/dev/null 2>&1; then
    daemon_pid="$(systemctl --user show -p MainPID --value session-manager.service 2>/dev/null || :)"
    if [[ "${daemon_pid}" =~ ^[1-9][0-9]*$ ]] &&
       [[ -e "/proc/${daemon_pid}/exe" ]] &&
       [[ -e "${HOME}/.local/bin/session-manager" ]] &&
       [[ "$(stat -Lc '%d:%i' "/proc/${daemon_pid}/exe")" != "$(stat -Lc '%d:%i' "${HOME}/.local/bin/session-manager")" ]]; then
        echo '✗ Session Manager daemon still uses an older executable; postpone desktop integration until a controlled daemon restart.' >&2
        exit 1
    fi
fi

# Apply only the files needed for the Session Manager UI, workspace controller
# and scratchpads. Never reload Hyprland, kill Quickshell or move a window here.
for mapping in \
    "hypr/files/keybinds.lua|${HOME}/.config/hypr/keybinds.lua" \
    "hypr/files/Scripts/workspace-columns.py|${HOME}/.config/hypr/Scripts/workspace-columns.py" \
    "hypr/files/Scripts/scratchpad.sh|${HOME}/.config/hypr/Scripts/scratchpad.sh" \
    "quickshell/files/shell.qml|${HOME}/.config/quickshell/shell.qml" \
    "quickshell/files/SessionMenu.qml|${HOME}/.config/quickshell/SessionMenu.qml"; do
    relative="${mapping%%|*}"
    target="${mapping#*|}"
    source="${CONFIGS_DIR}/${relative}"
    if [[ ! -f "${source}" || ! -d "$(dirname -- "${target}")" || -L "${target}" ]]; then
        echo "✗ Missing source/target directory or symlinked target: ${target}" >&2
        exit 1
    fi
    if [[ -f "${target}" ]] && cmp -s "${source}" "${target}"; then
        continue
    fi
    if [[ -e "${target}" ]]; then
        backup="$(mktemp "${target}.bak.XXXXXXXX")"
        cp -p -- "${target}" "${backup}"
        echo "==> Backed up ${target} to ${backup}"
    fi
    temporary="$(mktemp "${target}.tmp.XXXXXXXX")"
    case "${target}" in
        */Scripts/*) mode=0755 ;;
        *) mode=0644 ;;
    esac
    install -m "${mode}" "${source}" "${temporary}"
    mv -f -- "${temporary}" "${target}"
done

echo '✓ Session Manager Hyprland and Quickshell files installed.'
echo '  Shortcuts and menu are available after the compositor/shell reload or next login.'
