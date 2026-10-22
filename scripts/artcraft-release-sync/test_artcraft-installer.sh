#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
INSTALLER="${SCRIPT_DIR}/../../packages/artcraft/install_artcraft_apps.sh"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
mkdir -p "$TEMP_DIR/bin" "$TEMP_DIR/archive"

cat > "$TEMP_DIR/bin/bsdtar" <<'EOF'
#!/usr/bin/env bash
app=${2##*/}; app=${app%%-*}
printf 'pkgname = ai.storyteller.%s\npkgver = 1.0.0-1\n' "$app"
EOF
cat > "$TEMP_DIR/bin/pacman" <<'EOF'
#!/usr/bin/env bash
[[ "$1" == -Q ]] || exit 2
app=${2##*.}
if [[ "$app" == photocraft ]]; then
    case "${TEST_MODE:-current}" in
        missing) exit 1 ;;
        old) echo "$2 0.9.0-1"; exit 0 ;;
        newer) echo "$2 2.0.0-1"; exit 0 ;;
    esac
fi
echo "$2 1.0.0-1"
EOF
cat > "$TEMP_DIR/bin/sudo" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$TEST_CALLS"
[[ "${TEST_SUDO_FAIL:-0}" == 0 ]]
EOF
chmod +x "$TEMP_DIR/bin/"*

while IFS= read -r app; do
    dir="$TEMP_DIR/archive/$app/current"
    mkdir -p "$dir"
    pkg="$dir/$app-1.0.0-linux-x86_64.pkg.tar.zst"
    printf '%s\n' "$app" > "$pkg"
    (cd "$dir"; sha256sum "${pkg##*/}" > SHA256SUMS.txt)
done < "${SCRIPT_DIR}/artcraft-apps.list"

export PATH="$TEMP_DIR/bin:$PATH" ARTCRAFT_RELEASES_DIR="$TEMP_DIR/archive" TEST_CALLS="$TEMP_DIR/calls"
check_ok() { "$INSTALLER" "$@" > "$TEMP_DIR/output" 2>&1 || { printf 'Unexpected failure:\n'; head -20 "$TEMP_DIR/output"; exit 1; }; }
check_fail() { if "$INSTALLER" "$@" > "$TEMP_DIR/output" 2>&1; then echo "Expected failure: $*" >&2; exit 1; fi; }

export TEST_MODE=current
check_ok
[[ ! -e "$TEST_CALLS" ]] # No-op: do not invoke sudo.

export TEST_MODE=old
check_ok --check
[[ ! -e "$TEST_CALLS" ]] # Dry run.
check_ok
[[ $(wc -l < "$TEST_CALLS") == 1 ]]
[[ $(grep -o -- '-linux-x86_64.pkg.tar.zst' "$TEST_CALLS" | wc -l) == 1 ]]
rm -f "$TEST_CALLS"

export TEST_MODE=missing
check_ok
[[ -f "$TEST_CALLS" ]] # First install.
rm -f "$TEST_CALLS"

export TEST_MODE=newer
check_fail
[[ ! -e "$TEST_CALLS" ]] # Never downgrade.

export TEST_MODE=old
rm "$TEMP_DIR/archive/figcraft/current/figcraft-1.0.0-linux-x86_64.pkg.tar.zst"
check_fail
[[ ! -e "$TEST_CALLS" ]] # Missing archive: no partial transaction.
printf 'figcraft\n' > "$TEMP_DIR/archive/figcraft/current/figcraft-1.0.0-linux-x86_64.pkg.tar.zst"
printf 'tampered\n' >> "$TEMP_DIR/archive/figcraft/current/figcraft-1.0.0-linux-x86_64.pkg.tar.zst"
check_fail
[[ ! -e "$TEST_CALLS" ]] # Checksum failure.
printf 'figcraft\n' > "$TEMP_DIR/archive/figcraft/current/figcraft-1.0.0-linux-x86_64.pkg.tar.zst"
export TEST_SUDO_FAIL=1
check_fail
[[ -f "$TEST_CALLS" ]] # Propagate pacman/sudo failure.

echo '✓ ArtCraft installer tests passed (no-op, upgrade, first install, missing archive, checksum, downgrade, install failure).'
