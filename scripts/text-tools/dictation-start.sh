#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${XDG_CONFIG_HOME:-${HOME}/.config}/text-tools/config.sh"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "✗ Text tools config not found: ${CONFIG_FILE}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

RUNTIME_DIR="${TEXT_TOOLS_RUNTIME_DIR}"
PID_FILE="${RUNTIME_DIR}/dictation.pid"
AUDIO_FILE="${RUNTIME_DIR}/dictation.wav"
LOG_FILE="${RUNTIME_DIR}/dictation.log"
STATE_FILE="${RUNTIME_DIR}/dictation.state"

set_state() {
    local state="$1"
    local temporary_file

    temporary_file="$(mktemp "${RUNTIME_DIR}/.dictation.state.XXXXXX")"
    printf '%s\n' "${state}" > "${temporary_file}"
    mv -f "${temporary_file}" "${STATE_FILE}"
}

notify() {
    notify-send "Dictée" "$1" >/dev/null 2>&1 || true
}

if ! command -v pw-record >/dev/null 2>&1; then
    echo "✗ pw-record is required." >&2
    notify "pw-record est introuvable."
    exit 1
fi

mkdir -p -m 700 "${RUNTIME_DIR}"
chmod 700 "${RUNTIME_DIR}"

if [[ -f "${PID_FILE}" ]]; then
    read -r pid < "${PID_FILE}"
    if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" >/dev/null 2>&1; then
        command_line="$(tr '\0' ' ' < "/proc/${pid}/cmdline")"
        if [[ "${command_line}" == *"pw-record"* ]]; then
            echo "✗ A dictation is already in progress." >&2
            notify "Une dictée est déjà en cours."
            exit 1
        fi
    fi

    rm -f "${PID_FILE}"
fi

set_state "idle"
rm -f "${AUDIO_FILE}" "${LOG_FILE}"

pw-record \
    --rate 16000 \
    --channels 1 \
    --format s16 \
    --container wav \
    "${AUDIO_FILE}" >"${LOG_FILE}" 2>&1 &
pid=$!

printf '%s\n' "${pid}" > "${PID_FILE}"

sleep 0.1
if ! kill -0 "${pid}" >/dev/null 2>&1; then
    rm -f "${PID_FILE}"
    set_state "idle"
    echo "✗ Unable to start audio recording. See ${LOG_FILE}." >&2
    notify "Impossible de démarrer l'enregistrement."
    exit 1
fi

if ! set_state "recording"; then
    kill -INT "${pid}" || true
    rm -f "${PID_FILE}"
    echo "✗ Unable to publish the recording state." >&2
    notify "Impossible d'indiquer l'état de l'enregistrement."
    exit 1
fi

notify "Enregistrement en cours."
