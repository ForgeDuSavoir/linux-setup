#!/usr/bin/env bash

set -euo pipefail

WEBAPP_NAME="freshrss"
APP_NAME="FreshRSS WebApp"

RUN_SCRIPT="${HOME}/.local/bin/run_freshrss"
DESKTOP_FILE="${HOME}/.local/share/applications/${WEBAPP_NAME}.desktop"
ICON_FILE="${HOME}/.local/share/icons/hicolor/scalable/apps/${WEBAPP_NAME}.svg"
PROFILE_DIR="${HOME}/.local/share/webapps/${WEBAPP_NAME}"

echo "==> Uninstalling ${APP_NAME}..."

rm -f "${RUN_SCRIPT}"
rm -f "${DESKTOP_FILE}"
rm -f "${ICON_FILE}"

if [[ -d "${PROFILE_DIR}" ]]; then
    read -r -p "Remove Firefox profile/data for ${APP_NAME}? [y/N]: " answer

    case "${answer}" in
        y|Y|yes|YES)
            rm -rf "${PROFILE_DIR}"
            echo "✓ Removed profile/data."
            ;;
        *)
            echo "↪ Keeping profile/data."
            ;;
    esac
fi

update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true

echo "✓ ${APP_NAME} uninstalled successfully."