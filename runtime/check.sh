#!/usr/bin/env bash
# Development validation only: never installs or executes a live desktop action.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
export CARGO_TARGET_DIR="$ROOT/target"
export PYTHONDONTWRITEBYTECODE=1
cargo +1.96.1 fmt --check
cargo +1.96.1 test --offline --locked
cargo +1.96.1 clippy --offline --locked --all-targets -- -D warnings
cargo +1.96.1 build --offline --locked --release --bins --examples
python3 tests/test_workspace_parity.py
python3 tests/test_workspace_cli.py
python3 tests/test_desktop_parity.py
python3 tests/test_desktop_cli.py
python3 tests/test_desktop_private_core.py
python3 tests/test_startup_parity.py
python3 tests/test_startup_cli.py
python3 tests/test_startup_private_core.py
python3 tests/test_desktop_cohort.py
python3 tests/test_desktop_cohort_modes.py
python3 tests/test_notify_parity.py
python3 tests/test_notify_install.py
python3 tests/test_single_restore.py
python3 tests/test_session_files.py
python3 tests/test_session_files_private_core.py
python3 tests/test_cohort_files_expansion.py
python3 ../configs/default_applications/test_file_manager.py
python3 ../configs/session-manager/test-session-pi.py
python3 tests/test_pi_private_core.py
python3 tests/test_pi_install.py
python3 tests/test_thumbnail_parity.py
python3 tests/test_thumbnail_install.py
python3 tests/test_filmcraft_parity.py
python3 tests/test_filmcraft_faults.py
python3 tests/test_filmcraft_cli.py
python3 tests/test_filmcraft_real.py
python3 tests/test_filmcraft_install.py
bash ../scripts/photocraft-thumbnail/test_photocraft-thumbnail.sh
python3 ../configs/session-manager/test-agora-workflow-config.py
python3 ../configs/session-manager/test-agora-notify.py
python3 ../configs/pi/session-notifications/test-install.py
node --experimental-strip-types --test ../configs/pi/session-notifications/test.mjs
node ../configs/session-manager/test-notification-policy.js
python3 ../configs/session-manager/test-notification-store.py
