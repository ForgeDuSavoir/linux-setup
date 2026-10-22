#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
mkdir -p "$TEMP_DIR/bin" "$TEMP_DIR/home"

cat > "$TEMP_DIR/bin/sudo" <<'EOF'
#!/usr/bin/env bash
[[ "$*" != *'snapper create'* || "${TEST_SNAPSHOT_FAIL:-0}" == 0 ]]
EOF
cat > "$TEMP_DIR/bin/topgrade" <<'EOF'
#!/usr/bin/env bash
[[ "${TEST_TOPGRADE_FAIL:-0}" == 0 ]]
EOF
cat > "$TEMP_DIR/bin/sync-artcraft-releases" <<'EOF'
#!/usr/bin/env bash
echo sync >> "$TEST_CALLS"
[[ "${TEST_SYNC_FAIL:-0}" == 0 ]]
EOF
cat > "$TEMP_DIR/bin/install-artcraft-releases" <<'EOF'
#!/usr/bin/env bash
echo install >> "$TEST_CALLS"
[[ "${TEST_INSTALL_FAIL:-0}" == 0 ]]
EOF
cat > "$TEMP_DIR/bin/notify-send" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$TEMP_DIR/bin/"*
export PATH="$TEMP_DIR/bin:$PATH" HOME="$TEMP_DIR/home" TEST_CALLS="$TEMP_DIR/calls"

run() {
    printf '\n' | bash "$SCRIPT_DIR/safe-update.sh" > "$TEMP_DIR/output" 2>&1
}
check_failure() {
    if run; then
        echo "Unexpected success: $*" >&2
        exit 1
    fi
}

if ! run; then
    echo 'Unexpected failure in success case:' >&2
    head -40 "$TEMP_DIR/output" >&2
    exit 1
fi
[[ "$(tr '\n' ' ' < "$TEST_CALLS")" == 'sync install ' ]]
[[ -s "$(find "$TEMP_DIR/home/.local/state/linux-setup/logs" -name 'safe-update-*.log' -print -quit)" ]]
rm "$TEST_CALLS"

export TEST_SYNC_FAIL=1
check_failure sync
[[ "$(tr '\n' ' ' < "$TEST_CALLS")" == 'sync ' ]]
grep -q 'skipping package installation' "$TEMP_DIR/output"
unset TEST_SYNC_FAIL
rm "$TEST_CALLS"

export TEST_INSTALL_FAIL=1
check_failure install
[[ "$(tr '\n' ' ' < "$TEST_CALLS")" == 'sync install ' ]]
unset TEST_INSTALL_FAIL
rm "$TEST_CALLS"

export TEST_TOPGRADE_FAIL=1
check_failure topgrade
unset TEST_TOPGRADE_FAIL
rm "$TEST_CALLS"

export TEST_SNAPSHOT_FAIL=1
check_failure snapshot
[[ ! -e "$TEST_CALLS" ]]

echo '✓ safe-update integration tests passed (success, sync/install/topgrade/snapshot failure).'
