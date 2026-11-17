# Multiple neutral sessions: downstream v3 transition

## Status

**Deployed on 2026-11-17 after explicit approval.** The core and clients now run v3 together. The offline migration preserved all existing logical sessions, identities, opening order, active role and revision. No session was created/stopped or application launched as a live test; windows, workspace ownership and focused workspace/special context were unchanged. Quickshell was restarted as approved, resetting its RAM notification history.

The core wire/storage authority is the separate [Session Manager v3 contract](../../../session-manager/docs/neutral-sessions-v3-contract.md); this document owns only downstream behavior, checks and deployment coordination. Core acceptance is recorded in its [stage N review](../../../session-manager/docs/reviews/n-neutral-sessions-acceptance.md).

The production installer pins published core revision `9032a6aceffbe53053968dfa918371851e866fcd`, built from GitHub with vendored dependencies and no downstream patches. The previous patches are retired because their fixes are upstream. Do not apply v2 patches to v3, bypass the pin with a neighbouring development checkout, or mix daemon/client versions.

## Implemented clients

- `SessionMenu.qml` consumes `source list`, not a synthetic `project list`. The built-in Neutral source is an ordinary first row in the start list. Project search filters only project rows; Neutral remains available. A real project named Neutral is visibly marked as a project, distinct from the built-in row. Source type selects literal `start --neutral` or `start --project NAME` arguments. Open instances of both kinds appear in one opening-order list with the existing keyboard navigation and guarded stop.
- `SessionService.qml` accepts the closed typed `source` projection, preserves generation/confirmation rules, and compares source identity when retaining stable delegates. Old top-level project-name projections are not treated as v3.
- `SessionStrip.qml` shows only actual UUID-backed sessions. Neutral instances have `N<number>` labels, normal selection/click behavior and their own notification attention. There is no fabricated singleton Neutral case. The empty list is genuinely empty. The menu's explicitly named **Deselect session** action remains available for returning to the legacy unowned desktop without creating/stopping any instance.
- `session-desktop` accepts the two typed CLI start forms and allocates a fresh empty column to each new UUID. Existing UUID ownership, preferred column, compaction, stop guards and scratchpad routing are source-independent and reused. The downstream workspace metadata stays at **version 2**: it is a separate schema from the core runtime and needs no format conversion.
- `session-pi` uses the configured `agora_root` for either an active neutral instance or no selected session, without looking up projects. Project instances still use their recorded name's current directory and fail if unavailable. The application/browser bridge reads `source.project_name` only for project sources. Neutral application resolution stays installed-only; the existing installed Firefox/default-profile behavior is preserved, not silently replaced with newly created per-neutral browser profiles.
- Notification contexts for real neutral instances are `session:<UUID>`, exactly like projects. No source-name/application heuristic or shared Neutral bucket was introduced. The old bare `neutral` hint still denotes only the legacy unowned/no-active desktop and is labeled accordingly in history; it must not acknowledge or mark every neutral instance. Global/Beeper behavior, the 100-entry RAM history and replacement/expiry policies are unchanged.

## Preserve the old unowned desktop

The internal owner token `neutral`, old `special:session-*` scratchpads and existing unowned columns retain their historical meaning: **no selected core session**. They are not a first-class neutral session and are never renamed/adopted as one. Real instances own columns and `special:sm-<UUID>-<slot>` scratchpads by UUID; `special:global` stays shared.

Fresh starts allocate empty columns even when existing unowned windows are present. Deactivation and an active instance's guarded stop return to the retained unowned space. Direct core stop is still logical-only; graphical stop checks normal windows and all five scoped scratchpads first. The existing single-monitor restriction and context-confirmation requirements remain in place.

## Installation safety

`require_protocol_v3.sh` is sourced before writes by:

- `configure_session_manager.sh`;
- `install_desktop_integration.sh`;
- `../quickshell/install_quickshell_config.sh`.

It checks the installed executable's offline `--version`, refuses a remaining v2 socket, and verifies that a known running user service has the same executable inode. If a known service cannot be inspected, refuse rather than assume it is stopped. It never starts/stops services, removes a socket, or changes focus. The targeted installer was exercised against the real current v2 installation: it refused before writing, and hashes of the installed desktop helper/menu stayed identical.

The real installers also ran successfully in an owned temporary HOME with a v3 build, private XDG roots, fake systemctl and no live shell. Staged helper/QML bytes matched the sources. Refusal against v2 and a mismatched running-service executable is covered by the same test. This isolated evidence preceded and is distinct from the controlled live deployment below.

## Isolated evidence

All of the following passed:

- Python suites: `test-session-desktop.py`, `test-session-status.py`, `test-session-pi.py`, `test-session-app-launcher.py`, `test-neutral-v3.py`, `test-session-qml.py`, `test-notification-store.py`, `test-agora-notify.py`, `test-project-firefox.py`, `test-agora-workflow-config.py`.
- Node suites: `test-session-service.js`, `test-session-menu-keyboard.js`, `test-notification-policy.js`.
- Hyprland fake-controller suites: `navigation_scratchpad_test.py`, `scratchpad_session_test.py`, `workspace_columns_test.py`.
- Native `tst_session_strip.qml`: **14 Qt tests at each of 100% and 150% scale**, including all lower-half hit coordinates, edges, overflow and pending-selection behavior.
- Qt 6 `qmllint` for the menu/service/strip exited successfully; existing uncreatable-PanelWindow and unqualified-access warnings remain nonfatal. Bash syntax and Git whitespace checks passed.

`test-neutral-v3.py` uses the neighbouring repository's explicitly built `target/debug/session-manager`, never the installed daemon binary. It starts only its own temporary v3 daemon, combines multiple neutral and project instances with a fake compositor, checks empty-column ownership/legacy-window retention and installed-only launchers, captures a neutral notification context by UUID, and exercises installers entirely in its temporary HOME. Notification-store tests use two typed neutral instances on a private D-Bus and an offscreen strip; no personal notifications are inspected. The offscreen layout fixture explicitly shows its private offscreen Window so Qt creates/measures delegates; it does not create a host desktop window.

Example validation commands, from `linux-setup`:

```sh
python3 configs/session-manager/test-neutral-v3.py
python3 configs/session-manager/test-session-qml.py
python3 configs/session-manager/test-notification-store.py
node configs/session-manager/test-session-menu-keyboard.js
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_SCALE_FACTOR=1.5 \
  /usr/lib/qt6/bin/qmltestrunner -input configs/session-manager/tst_session_strip.qml
```

Build the neighbouring v3 core offline first if its test binary is absent. No test step above requires changing the user's actual sessions or focus.

## Controlled deployment record (2026-11-17)

- Published the reviewed core and verified the exact GitHub revision; built/installed it first in an owned temporary HOME, with a clean source cache and no patches.
- Made a private configuration/binary backup and, under the desktop controller lock, stopped only the known Quickshell instance and v2 user service before backing up current/previous v2 state and ownership metadata.
- Installed through the pinned script, explicitly ran `migrate --from-v2`, installed compatible helpers/QML through the targeted scripts, then started the known v3 service and Quickshell. No workspace dispatcher or application-launch test was used.
- Compared complete public session projections against the converted pre-upgrade snapshot: UUIDs, names, numbering, array order, active role and revision match exactly. V2 current/previous bytes remain unchanged and no ordinary v3 previous revision was fabricated.
- Compared window addresses/workspaces, monitor active/special workspace context and the exact workspace-owner metadata bytes: unchanged. Read-only `session-desktop status` confirms logical/spatial agreement; typed source discovery and current application listing succeed. Installed helper/QML bytes match sources and the running service uses the installed executable inode.
- Private evidence/backups live beneath `${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/session-manager-upgrades/`, with a mode-0700 backup directory; no runtime snapshot, UUID list, notification content or backup is committed here. Visual acceptance of user-driven new instances remains pending.

## Coordinated deployment procedure

1. Review/publish the core v3 changes, update the reproducible GitHub pin and retire the old patches only against the matching new revision. Rebuild/test that pinned installer before touching the live stack.
2. Obtain approval for the controlled service interruption and Quickshell reload. The latter resets its in-memory notification history. Back up configuration/private state and record existing identities, opening order, active role and resource ownership without launching applications or moving windows.
3. Stop known request producers and only the known v2 service, install the pinned v3 binary, then explicitly run its offline `migrate --from-v2`. Inspect uncertain results rather than forcing or reimporting. Retain v2 artifacts unchanged.
4. Install the v3 helpers and shell together through the targeted scripts; start the known v3 service and verify logical/spatial confirmation. Preserve the unowned space explicitly. Do not run the old executable against stale v2 state after v3 has advanced.
5. Verify visually that Neutral starts independent empty UUID-backed instances, their menu/bar selection and scratchpads are independent, and contextual attention is acknowledged only on confirmed entry. User-driven launches/window tests remain separate from read-only migration checks.

Client installation itself does not automatically migrate, roll back, adopt windows or launch a browser. The separately approved live procedure above included an explicit migration and shell restart/history reset.
