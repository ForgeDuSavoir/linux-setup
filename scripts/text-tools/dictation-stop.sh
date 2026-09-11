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

    mkdir -p -m 700 "${RUNTIME_DIR}"
    chmod 700 "${RUNTIME_DIR}"
    temporary_file="$(mktemp "${RUNTIME_DIR}/.dictation.state.XXXXXX")"
    printf '%s\n' "${state}" > "${temporary_file}"
    mv -f "${temporary_file}" "${STATE_FILE}"
}

notify() {
    notify-send "Dictée" "$1" >/dev/null 2>&1 || true
}

trap 'set_state "idle" || true' EXIT

if [[ ! -f "${PID_FILE}" ]]; then
    echo "✗ No dictation is in progress." >&2
    notify "Aucune dictée en cours."
    exit 1
fi

read -r pid < "${PID_FILE}"
if [[ ! "${pid}" =~ ^[0-9]+$ ]] || ! kill -0 "${pid}" >/dev/null 2>&1; then
    rm -f "${PID_FILE}"
    echo "✗ The dictation process is no longer running." >&2
    notify "L'enregistrement n'est plus actif."
    exit 1
fi

command_line="$(tr '\0' ' ' < "/proc/${pid}/cmdline")"
if [[ "${command_line}" != *"pw-record"* ]]; then
    echo "✗ Refusing to stop unexpected process ${pid}." >&2
    notify "Le processus d'enregistrement est invalide."
    exit 1
fi

kill -INT "${pid}"
for _ in {1..50}; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "✗ The audio recorder did not stop cleanly." >&2
    notify "L'enregistreur ne s'est pas arrêté."
    exit 1
fi

rm -f "${PID_FILE}"
set_state "transcribing"

if [[ ! -s "${AUDIO_FILE}" ]]; then
    echo "✗ No recorded audio found: ${AUDIO_FILE}" >&2
    notify "Aucun audio à transcrire."
    exit 1
fi

if ! command -v whisper-cli >/dev/null 2>&1; then
    echo "✗ whisper-cli is required." >&2
    notify "whisper-cli est introuvable."
    exit 1
fi

if [[ ! -f "${WHISPER_MODEL}" ]]; then
    echo "✗ Whisper model not found: ${WHISPER_MODEL}" >&2
    notify "Le modèle Whisper est introuvable."
    exit 1
fi

notify "Transcription en cours."

if transcript="$(whisper-cli \
    --model "${WHISPER_MODEL}" \
    --language "${WHISPER_LANGUAGE}" \
    --no-timestamps \
    --no-prints \
    --file "${AUDIO_FILE}" | sed '/^[[:space:]]*\.\.\.[[:space:]]*$/d')"; then
    while [[ "${transcript}" == $'\n'* ]]; do
        transcript="${transcript:1}"
    done

    printf '%s' "${transcript}"
    rm -f "${AUDIO_FILE}" "${LOG_FILE}"
    notify "Transcription terminée."
else
    echo "✗ Transcription failed; audio retained at ${AUDIO_FILE}." >&2
    notify "La transcription a échoué."
    exit 1
fi
