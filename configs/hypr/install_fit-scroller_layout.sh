#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Fit Scroller"
VERSION="v0.1.1"
ARCHIVE="fit-scroller-layout-${VERSION}.tar.gz"
ARCHIVE_URL="https://github.com/ForgeDuSavoir/fit-scroller-layout/releases/download/${VERSION}/${ARCHIVE}"
ARCHIVE_SHA256="834d5369b528ae831c101d14d5279c84a216411ca787b6048b3f99fd7d5d0d9a"
TARGET_DIR="${HOME}/.config/hypr/layouts"
INSTALL_DIR="${TARGET_DIR}/fit-scroller"

echo "==> Installing ${APP_NAME} ${VERSION} layout..."

if [[ -f "${INSTALL_DIR}/.release-version" && -f "${INSTALL_DIR}/init.lua" \
    && -f "${INSTALL_DIR}/order_drop.lua" ]] \
    && [[ "$(< "${INSTALL_DIR}/.release-version")" == "${VERSION}" ]]; then
    echo "✓ ${APP_NAME} ${VERSION} is already installed."
    exit 0
fi

for tool in curl tar sha256sum; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        echo "✗ ${tool} is required to install ${APP_NAME}." >&2
        exit 1
    fi
done

mkdir -p "${TARGET_DIR}"
TMP_DIR="$(mktemp -d "${TARGET_DIR}/.fit-scroller-install.XXXXXX")"
trap 'rm -rf -- "${TMP_DIR}"' EXIT

curl -fsSL "${ARCHIVE_URL}" -o "${TMP_DIR}/${ARCHIVE}"
printf '%s  %s\n' "${ARCHIVE_SHA256}" "${TMP_DIR}/${ARCHIVE}" | sha256sum --check --status
tar -C "${TMP_DIR}" -xzf "${TMP_DIR}/${ARCHIVE}"

STAGED_DIR="${TMP_DIR}/fit-scroller"
if [[ ! -f "${STAGED_DIR}/init.lua" || ! -f "${STAGED_DIR}/order_drop.lua" ]]; then
    echo "✗ ${APP_NAME} release is missing required runtime files." >&2
    exit 1
fi
printf '%s\n' "${VERSION}" > "${STAGED_DIR}/.release-version"

BACKUP_DIR=""
if [[ -e "${INSTALL_DIR}" || -L "${INSTALL_DIR}" ]]; then
    BACKUP_DIR="$(mktemp -d "${TARGET_DIR}/fit-scroller-backup.XXXXXX")"
    mv -T -- "${INSTALL_DIR}" "${BACKUP_DIR}/fit-scroller"
fi

if ! mv -T -- "${STAGED_DIR}" "${INSTALL_DIR}"; then
    if [[ -n "${BACKUP_DIR}" ]]; then
        mv -T -- "${BACKUP_DIR}/fit-scroller" "${INSTALL_DIR}"
        rmdir "${BACKUP_DIR}"
    fi
    exit 1
fi

if [[ -n "${BACKUP_DIR}" ]]; then
    echo "Previous layout saved to ${BACKUP_DIR}/fit-scroller."
fi
echo "✓ ${APP_NAME} ${VERSION} installed successfully."
