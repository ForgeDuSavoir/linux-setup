#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${XDG_CONFIG_HOME:-${HOME}/.config}/text-tools/config.sh"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "✗ Text tools config not found: ${CONFIG_FILE}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

PID_FILE="${TEXT_TOOLS_RUNTIME_DIR}/dictation.pid"

is_dictation_running() {
    local pid
    local command_line

    [[ -f "${PID_FILE}" ]] || return 1
    read -r pid < "${PID_FILE}" || return 1
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
    kill -0 "${pid}" >/dev/null 2>&1 || return 1

    command_line="$(tr '\0' ' ' < "/proc/${pid}/cmdline")"
    [[ "${command_line}" == *"pw-record"* ]]
}

if is_dictation_running; then
    dictation-stop | text-insert
else
    dictation-start
fi
