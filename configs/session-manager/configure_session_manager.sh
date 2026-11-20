#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "${SCRIPT_DIR}/require_protocol_v3.sh"
session_manager_require_v3
PROJECT_SOURCE="${SESSION_MANAGER_PROJECT_SOURCE:-${HOME}/Obsidian/Agora/2 Projects}"
INSTALL_DESKTOP="${SESSION_MANAGER_INSTALL_DESKTOP:-1}"
if [[ "${INSTALL_DESKTOP}" != 0 && "${INSTALL_DESKTOP}" != 1 ]]; then
    echo '✗ SESSION_MANAGER_INSTALL_DESKTOP must be 0 or 1.' >&2
    exit 1
fi
if [[ "${INSTALL_DESKTOP}" == 1 ]]; then
    bash "${SCRIPT_DIR}/install_desktop_integration.sh" --preflight
fi
CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/session-manager"
CONFIG_FILE="${CONFIG_DIR}/config-v2.toml"
UNIT_SOURCE="${SCRIPT_DIR}/session-manager.service"
LAUNCHER_INSTALLER="${SCRIPT_DIR}/install_app_launcher.sh"
LAUNCHER_TARGET="${HOME}/.local/bin/session-app-launcher"
DESKTOP_INSTALLER="${SCRIPT_DIR}/../../runtime/install_desktop.py"
DESKTOP_TARGET="${HOME}/.local/bin/session-desktop"
FIREFOX_SOURCE="${SCRIPT_DIR}/agora-project-firefox.sh"
FIREFOX_TARGET="${HOME}/.local/bin/agora-project-firefox"
PI_INSTALLER="${SCRIPT_DIR}/../../runtime/install_pi.py"
PI_TARGET="${HOME}/.local/bin/session-pi"
NOTIFY_INSTALLER="${SCRIPT_DIR}/../../runtime/install_notify.py"
NOTIFY_TARGET="${HOME}/.local/bin/agora-notify"
PI_DESKTOP_SOURCE="${SCRIPT_DIR}/session-pi.desktop"
PI_DESKTOP_TARGET="${XDG_DATA_HOME:-${HOME}/.local/share}/applications/session-pi.desktop"
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
for source in "${UNIT_SOURCE}" "${LAUNCHER_INSTALLER}" "${DESKTOP_INSTALLER}" "${FIREFOX_SOURCE}" "${PI_INSTALLER}" "${PI_DESKTOP_SOURCE}" "${NOTIFY_INSTALLER}"; do
    if [[ ! -f "${source}" ]]; then
        echo "✗ Missing Session Manager integration: ${source}" >&2
        exit 1
    fi
done
if ! command -v python3 >/dev/null 2>&1 || ! command -v systemctl >/dev/null 2>&1; then
    echo '✗ python3 and systemctl are required.' >&2
    exit 1
fi

# The integration's neutral directory is user-owned configuration, not a
# location embedded in the Pi launcher or inferred from project_source.
python3 "${SCRIPT_DIR}/configure_agora_workflow.py"

mkdir -p "${CONFIG_DIR}" "${UNIT_DIR}"
if [[ -L "${CONFIG_FILE}" || -L "${UNIT_FILE}" || -L "${LAUNCHER_TARGET}" || -L "${FIREFOX_TARGET}" || -L "${PI_TARGET}" || -L "${PI_DESKTOP_TARGET}" || -L "${NOTIFY_TARGET}" ]]; then
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
bash "${LAUNCHER_INSTALLER}" --apply
# Never replace a cohort entry point independently, including in clients-only mode.
# The coordinator below owns desktop/controller/startup/admin and all dependent config.
install -m 0755 "${FIREFOX_SOURCE}" "${FIREFOX_TARGET}"
python3 "${PI_INSTALLER}" --apply
python3 "${NOTIFY_INSTALLER}" --apply
install -Dm0644 "${PI_DESKTOP_SOURCE}" "${PI_DESKTOP_TARGET}"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname -- "${PI_DESKTOP_TARGET}")"
fi
systemctl --user daemon-reload
systemctl --user enable session-manager.service
if [[ "${INSTALL_DESKTOP}" == 1 ]]; then
    bash "${SCRIPT_DIR}/install_desktop_integration.sh"
else
    echo '==> Desktop cohort deferred; preserving all existing helpers, QML and notification history.'
fi

echo '✓ Session Manager enabled for the next user login.'
echo '  No daemon was started and no Hyprland/Quickshell process was reloaded by this script.'
