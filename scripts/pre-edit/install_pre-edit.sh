#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="pre-edit"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_FILE="${SCRIPT_DIR}/${SCRIPT_NAME}.sh"
TARGET_DIR="${HOME}/.local/bin"
TARGET_FILE="${TARGET_DIR}/${SCRIPT_NAME}"

echo "==> Installing ${SCRIPT_NAME}..."

if [[ ! -f "${SOURCE_FILE}" ]]; then
    echo "✗ Missing source file: ${SOURCE_FILE}"
    exit 1
fi

# Preserve running script descriptors and refuse linked targets/backup ancestry.
validate_path() {
    local path="$1"
    [[ "$path" == /* ]] || { echo 'Absolute install/backup path required.' >&2; exit 1; }
    while [[ "$path" != / ]]; do
        [[ ! -L "$path" ]] || { echo 'Refusing symlinked install/backup path.' >&2; exit 1; }
        path="${path%/*}"; [[ -n "$path" ]] || path=/
    done
}
validate_path "$TARGET_FILE"
[[ ! -e "$TARGET_FILE" || -f "$TARGET_FILE" ]] || { echo 'Nonregular pre-edit target.' >&2; exit 1; }
if [[ -f "$TARGET_FILE" ]] && cmp -s "$SOURCE_FILE" "$TARGET_FILE" && [[ "$(stat -c %a "$TARGET_FILE")" == 755 ]]; then
    echo '✓ pre-edit already current.'; exit 0
fi
umask 077
if [[ -f "$TARGET_FILE" ]]; then
    BASE="${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/pre-edit-upgrades"
    validate_path "$BASE"; mkdir -p "$BASE"
    BACKUP="$(mktemp -d "$BASE/XXXXXXXX")"
    cp -p -- "$TARGET_FILE" "$BACKUP/pre-edit"
    echo "Private pre-edit backup: $BACKUP"
fi
mkdir -p "$TARGET_DIR"
TEMP="$(mktemp "$TARGET_DIR/pre-edit.tmp.XXXXXXXX")"
trap 'rm -f -- "$TEMP"' EXIT
install -m 0755 "$SOURCE_FILE" "$TEMP"
mv -T -- "$TEMP" "$TARGET_FILE"

echo "✓ ${SCRIPT_NAME} installed to ${TARGET_FILE}"