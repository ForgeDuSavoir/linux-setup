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
python3 tests/test_shift_s.py
python3 tests/test_retired_shortcuts.py
python3 tests/test_close_event.py
python3 tests/test_workspace_cli.py
# SUPER+Tab pairs the controller with the guarded native application launcher.
cargo +1.96.1 build --offline --locked --release --manifest-path ../configs/session-manager/app-launcher/Cargo.toml --target-dir ../configs/session-manager/app-launcher/target
python3 tests/test_tab_launcher.py
python3 tests/test_new_workspace.py
python3 tests/test_desktop_parity.py
python3 tests/test_desktop_cli.py
python3 tests/test_desktop_private_core.py
python3 tests/test_empty_replacement.py
python3 tests/test_context_animations.py
python3 tests/test_scratchpad_animation.py
python3 tests/test_window_animation.py
python3 tests/test_startup_parity.py
python3 tests/test_startup_cli.py
python3 tests/test_startup_readiness.py
python3 tests/test_startup_private_core.py
python3 tests/test_desktop_cohort.py
python3 tests/test_desktop_cohort_modes.py
python3 tests/test_visuals_mode.py
python3 tests/test_notify_parity.py
python3 tests/test_notify_install.py
python3 tests/test_single_restore.py
python3 ../configs/obs/test_project_launchers.py
python3 ../configs/obs/test_project_launchers_core.py
python3 tests/test_obsidian.py
python3 tests/test_obsidian_private_core.py
python3 tests/test_obsidian_install.py
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
node ../configs/session-manager/test-session-menu-keyboard.js
python3 ../configs/session-manager/test-startup-menu-qml.py
node ../configs/session-manager/test-session-service.js
node ../configs/session-manager/test-session-attention.js
python3 ../configs/session-manager/test-session-attention-qml.py
node ../configs/session-manager/test-notification-policy.js
python3 ../configs/session-manager/test-notification-store.py
