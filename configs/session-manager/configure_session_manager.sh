#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_SOURCE="${SESSION_MANAGER_PROJECT_SOURCE:-${HOME}/Obsidian/Agora/2 Projects}"
CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/session-manager"
CONFIG_FILE="${CONFIG_DIR}/config-v2.toml"
UNIT_SOURCE="${SCRIPT_DIR}/session-manager.service"
LAUNCHER_SOURCE="${SCRIPT_DIR}/session-app-launcher.py"
LAUNCHER_TARGET="${HOME}/.local/bin/session-app-launcher"
DESKTOP_SOURCE="${SCRIPT_DIR}/session-desktop.py"
DESKTOP_TARGET="${HOME}/.local/bin/session-desktop"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/session-manager.service"

if [[ ! -d "${PROJECT_SOURCE}" ]]; then
    echo "✗ Create the project source before configuring Session Manager: ${PROJECT_SOURCE}" >&2
    exit 1
fi
if [[ ! -x "${HOME}/.local/bin/session-manager" ]]; then
    echo '✗ Install Session Manager before configuring it.' >&2
    exit 1
fi
for source in "${UNIT_SOURCE}" "${LAUNCHER_SOURCE}" "${DESKTOP_SOURCE}"; do
    if [[ ! -f "${source}" ]]; then
        echo "✗ Missing Session Manager integration: ${source}" >&2
        exit 1
    fi
done
if ! command -v python3 >/dev/null 2>&1 || ! command -v systemctl >/dev/null 2>&1; then
    echo '✗ python3 and systemctl are required.' >&2
    exit 1
fi

mkdir -p "${CONFIG_DIR}" "${UNIT_DIR}"
if [[ -L "${CONFIG_FILE}" || -L "${UNIT_FILE}" || -L "${LAUNCHER_TARGET}" || -L "${DESKTOP_TARGET}" ]]; then
    echo '✗ Refusing a symlinked Session Manager configuration or service unit.' >&2
    exit 1
fi
if [[ ! -e "${CONFIG_FILE}" ]]; then
    # JSON string quoting is also valid TOML basic-string quoting for this absolute path.
    python3 - "${CONFIG_FILE}" "${PROJECT_SOURCE}" <<'PY'
import json
import os
import sys

path, source = sys.argv[1:]
value = json.dumps(source, ensure_ascii=False)
content = f"schema_version = 2\nproject_source = {value}\n"
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
fd = os.open(path, flags, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as file:
    file.write(content)
PY
    echo "✓ Created ${CONFIG_FILE}"
else
    echo "==> Preserving existing ${CONFIG_FILE}; verify its project_source before enabling the service."
fi

if [[ -e "${UNIT_FILE}" ]] && ! cmp -s "${UNIT_SOURCE}" "${UNIT_FILE}"; then
    BACKUP="$(mktemp "${UNIT_FILE}.bak.XXXXXXXX")"
    cp -p -- "${UNIT_FILE}" "${BACKUP}"
    echo "==> Saved existing unit to ${BACKUP}"
fi
install -m 0644 "${UNIT_SOURCE}" "${UNIT_FILE}"
install -m 0755 "${LAUNCHER_SOURCE}" "${LAUNCHER_TARGET}"
install -m 0755 "${DESKTOP_SOURCE}" "${DESKTOP_TARGET}"
systemctl --user daemon-reload
systemctl --user enable session-manager.service
bash "${SCRIPT_DIR}/install_desktop_integration.sh"

echo '✓ Session Manager enabled for the next user login.'
echo '  No daemon was started and no Hyprland/Quickshell process was reloaded by this script.'
