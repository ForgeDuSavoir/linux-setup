#!/usr/bin/env bash

set -euo pipefail

REVISION="bff500ff52a0fd57f68a938e4610dfe7e47009e1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PATCH_FILES=(
    "${SCRIPT_DIR}/hidden-entries-without-exec.patch"
    "${SCRIPT_DIR}/deactivate-session.patch"
)
SOURCE_URL="https://github.com/ForgeDuSavoir/session-manager.git"
SOURCE_DIR="${HOME}/.cache/linux-setup/session-manager"
BIN_DIR="${HOME}/.local/bin"
TARGET="${BIN_DIR}/session-manager"

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

for patch_file in "${PATCH_FILES[@]}"; do
    if [[ ! -s "${patch_file}" ]]; then
        echo "✗ Missing reviewed Session Manager patch: ${patch_file}" >&2
        exit 1
    fi
done
# Build the pinned GitHub tree with the reviewed downstream fix in an owned temporary
# directory. The Git cache stays pristine, and rerunning the installer is safe.
BUILD_DIR="$(mktemp -d "${HOME}/.cache/linux-setup/session-manager-build.XXXXXXXX")"
trap 'rm -rf -- "${BUILD_DIR}"; if [[ -n "${TEMP_TARGET:-}" ]]; then rm -f -- "${TEMP_TARGET}"; fi' EXIT
git -C "${SOURCE_DIR}" archive "${REVISION}" | tar -x -C "${BUILD_DIR}"
for patch_file in "${PATCH_FILES[@]}"; do
    git -C "${BUILD_DIR}" apply --check "${patch_file}"
    git -C "${BUILD_DIR}" apply "${patch_file}"
done
(cd -- "${BUILD_DIR}" && RUSTUP_TOOLCHAIN=1.96.1 RUSTUP_AUTO_INSTALL=0 CARGO_NET_OFFLINE=true cargo build --release --offline --locked)

mkdir -p "${BIN_DIR}"
TEMP_TARGET="$(mktemp "${BIN_DIR}/.session-manager.XXXXXXXX")"
install -m 0755 "${BUILD_DIR}/target/release/session-manager" "${TEMP_TARGET}"
"${TEMP_TARGET}" --version
mv -f -- "${TEMP_TARGET}" "${TARGET}"
TEMP_TARGET=""

echo "✓ Session Manager ${REVISION} with reviewed hidden-entry and deactivate patches installed at ${TARGET}."
echo '  No daemon, project configuration, or desktop integration has been started.'
