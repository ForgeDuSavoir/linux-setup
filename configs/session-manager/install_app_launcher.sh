#!/usr/bin/env bash
# Targeted build/install (or explicit restore); never reload the desktop or launch an app.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "${SCRIPT_DIR}/require_protocol_v3.sh"
session_manager_require_v3
MODE="${1:-}"
if [[ "${MODE}" != --apply && "${MODE}" != --restore ]]; then
    echo "Usage: $0 --apply | --restore BACKUP_FILE" >&2
    exit 2
fi
if [[ "${MODE}" == --apply && "$#" != 1 || "${MODE}" == --restore && "$#" != 2 ]]; then exit 2; fi
TARGET="${HOME}/.local/bin/session-app-launcher"
BASE="${XDG_STATE_HOME:-${HOME}/.local/state}/linux-setup/app-launcher-upgrades"
if [[ "${BASE}" != /* || -L "${TARGET}" || ( -e "${TARGET}" && ! -f "${TARGET}" ) ]]; then
    echo 'Unsafe launcher/backup target.' >&2; exit 1
fi
# Refuse redirected installation/backup ancestors, not just the final file.
for location in "$(dirname -- "${TARGET}")" "${BASE}"; do
    while [[ "${location}" != / ]]; do
        if [[ -L "${location}" ]]; then echo 'Symlinked installation/backup directory.' >&2; exit 1; fi
        location="$(dirname -- "${location}")"
    done
done
if [[ "${MODE}" == --apply ]]; then
    command -v cargo >/dev/null
    command -v pkg-config >/dev/null
    pkg-config --exists gio-2.0
    # Explicit toolchain even when invoked from another working directory.
    cargo +1.96.1 build --release --locked --manifest-path "${SCRIPT_DIR}/app-launcher/Cargo.toml" \
        --target-dir "${SCRIPT_DIR}/app-launcher/target"
    SOURCE="${SCRIPT_DIR}/app-launcher/target/release/session-app-launcher"
    "${SOURCE}" --version
else
    SOURCE="$(realpath -e -- "$2")"
    if [[ "${SOURCE}" != "${BASE}"/*/session-app-launcher || ! -f "${SOURCE}" || -L "$2" || "$(stat -c %u -- "${SOURCE}")" != "$(id -u)" ]]; then
        echo 'Restore requires an owned backup from this installer.' >&2; exit 1
    fi
fi
mkdir -p -- "$(dirname -- "${TARGET}")" "${BASE}"
umask 077
BACKUP="$(mktemp -d "${BASE}/$(date -u +%Y%m%dT%H%M%S)-XXXXXXXX")"
if [[ -e "${TARGET}" ]]; then cp -p -- "${TARGET}" "${BACKUP}/session-app-launcher"; fi
printf 'Mode: %s\nTarget: %s\nRestore explicitly with: bash %q --restore %q\n' \
    "${MODE}" "${TARGET}" "$0" "${BACKUP}/session-app-launcher" > "${BACKUP}/installation.txt"
TEMPORARY="$(mktemp "${TARGET}.tmp.XXXXXXXX")"
trap 'rm -f -- "${TEMPORARY}"' EXIT
install -m 0755 -- "${SOURCE}" "${TEMPORARY}"
mv -f -- "${TEMPORARY}" "${TARGET}"
echo "Private launcher backup: ${BACKUP}"
echo 'Installed launcher only; core, Quickshell, windows and usage files untouched.'
