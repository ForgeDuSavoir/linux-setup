#!/usr/bin/env bash
# Source before any client/QML installation. Never replace a v2 stack piecemeal.
session_manager_require_v3() {
    local binary="${HOME}/.local/bin/session-manager" version pid
    if [[ ! -x "${binary}" ]] || ! version="$("${binary}" --version)" || [[ "${version}" != *' (protocol 3)' ]]; then
        echo 'Session clients require protocol 3. Prepare the coordinated offline upgrade; no files installed.' >&2
        return 1
    fi
    if [[ -n "${XDG_RUNTIME_DIR:-}" ]] && [[ -e "${XDG_RUNTIME_DIR}/session-manager/ipc-v2.sock" || -L "${XDG_RUNTIME_DIR}/session-manager/ipc-v2.sock" ]]; then
        echo 'A v2 socket remains. Stop the known owner or inspect a stale socket before upgrading clients.' >&2
        return 1
    fi
    if [[ -e "${HOME}/.config/systemd/user/session-manager.service" ]] || { [[ -n "${XDG_RUNTIME_DIR:-}" ]] && [[ -e "${XDG_RUNTIME_DIR}/session-manager/ipc-v3.sock" ]]; }; then
        if ! pid="$(systemctl --user show session-manager.service -p MainPID --value 2>/dev/null)"; then
            echo 'Cannot inspect the known service; refusing a partial client upgrade.' >&2
            return 1
        fi
        if [[ ! "${pid}" =~ ^[0-9]+$ ]]; then
            echo 'Invalid service PID response; refusing a partial client upgrade.' >&2
            return 1
        fi
        if [[ "${pid}" =~ ^[1-9][0-9]*$ ]] && [[ ! "${binary}" -ef "/proc/${pid}/exe" ]]; then
            echo 'The known service still runs a different executable. Stop it explicitly before upgrading clients.' >&2
            return 1
        fi
    fi
}
