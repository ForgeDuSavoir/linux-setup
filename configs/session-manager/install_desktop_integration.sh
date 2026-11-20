#!/usr/bin/env bash
# One coordinator owns all runtime/config publications; never copy Python over ELF.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ARGS=(--apply)
if [[ "${AGORA_DESKTOP_OFFLINE:-0}" == 1 ]]; then ARGS+=(--offline); fi
if [[ "${AGORA_ALLOW_NOTIFICATION_HISTORY_RESET:-0}" == 1 ]]; then ARGS+=(--allow-notification-history-reset); fi
exec python3 "$SCRIPT_DIR/../../runtime/install_desktop.py" "${ARGS[@]}" "$@"
