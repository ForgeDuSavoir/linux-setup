#!/usr/bin/env bash

set -euo pipefail

REVISION="9032a6aceffbe53053968dfa918371851e866fcd"


SOURCE_URL="https://github.com/ForgeDuSavoir/session-manager.git"
SOURCE_DIR="${HOME}/.cache/linux-setup/session-manager"
BIN_DIR="${HOME}/.local/bin"
TARGET="${BIN_DIR}/session-manager"

# Binary replacement is an explicit offline upgrade, never a hot daemon update.
if [[ -e "${HOME}/.config/systemd/user/session-manager.service" ]]; then
    if ! pid="$(systemctl --user show session-manager.service -p MainPID --value 2>/dev/null)" || [[ ! "${pid}" =~ ^[0-9]+$ ]]; then
        echo 'Cannot inspect the known service; refusing binary replacement.' >&2
        exit 1
    fi
    if [[ "${pid}" != 0 ]]; then
        echo 'Stop the known Session Manager service explicitly before installing protocol 3.' >&2
        exit 1
    fi
fi
for tool in git cargo rustup install tar; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        echo "✗ ${tool} is required to install Session Manager." >&2
        exit 1
    fi
done

if ! rustup toolchain list | grep -Eq '^1\.96\.1(-|[[:space:]])'; then
    echo '✗ Rust 1.96.1 is required. Install it explicitly with: rustup toolchain install 1.96.1' >&2
    exit 1
fi

if [[ ! -e "${SOURCE_DIR}" ]]; then
    mkdir -p "$(dirname -- "${SOURCE_DIR}")"
    git clone "${SOURCE_URL}" "${SOURCE_DIR}"
fi
if [[ ! -d "${SOURCE_DIR}/.git" ]] || [[ "$(git -C "${SOURCE_DIR}" remote get-url origin 2>/dev/null)" != "${SOURCE_URL}" ]]; then
    echo "✗ Refusing an unexpected source checkout: ${SOURCE_DIR}" >&2
    exit 1
fi
if [[ -n "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=normal)" ]]; then
    echo "✗ Source checkout contains uncommitted changes: ${SOURCE_DIR}" >&2
    exit 1
fi
if ! git -C "${SOURCE_DIR}" cat-file -e "${REVISION}^{commit}" 2>/dev/null; then
    git -C "${SOURCE_DIR}" fetch origin
fi
if ! git -C "${SOURCE_DIR}" cat-file -e "${REVISION}^{commit}" 2>/dev/null; then
    echo "✗ Pinned revision is unavailable from ${SOURCE_URL}: ${REVISION}" >&2
    exit 1
fi
if [[ "$(git -C "${SOURCE_DIR}" rev-parse HEAD)" != "${REVISION}" ]]; then
    git -C "${SOURCE_DIR}" checkout --detach "${REVISION}"
fi

# Build only the immutable published tree; all previous downstream patches are upstream.
BUILD_DIR="$(mktemp -d "${HOME}/.cache/linux-setup/session-manager-build.XXXXXXXX")"
trap 'rm -rf -- "${BUILD_DIR}"; if [[ -n "${TEMP_TARGET:-}" ]]; then rm -f -- "${TEMP_TARGET}"; fi' EXIT
git -C "${SOURCE_DIR}" archive "${REVISION}" | tar -x -C "${BUILD_DIR}"

(cd -- "${BUILD_DIR}" && RUSTUP_TOOLCHAIN=1.96.1 RUSTUP_AUTO_INSTALL=0 CARGO_NET_OFFLINE=true cargo build --release --offline --locked)

mkdir -p "${BIN_DIR}"
TEMP_TARGET="$(mktemp "${BIN_DIR}/.session-manager.XXXXXXXX")"
install -m 0755 "${BUILD_DIR}/target/release/session-manager" "${TEMP_TARGET}"
version="$("${TEMP_TARGET}" --version)"
[[ "${version}" == *' (protocol 3)' ]] || { echo 'Pinned binary is not protocol 3' >&2; exit 1; }
printf '%s\n' "${version}"
mv -f -- "${TEMP_TARGET}" "${TARGET}"
TEMP_TARGET=""

echo "✓ Session Manager ${REVISION} (protocol 3, no downstream patches) installed at ${TARGET}."
echo '  No daemon, project configuration, or desktop integration has been started.'
