# Empty session state and chooser at Hyprland login

## Current policy — installed 2026-11-21

Each new compositor instance (boot or graphical logout/login) forgets the previous
open logical sessions through the public core API, verifies zero sessions and no
active UUID, and starts Quickshell with a one-shot request to show the chooser.
**No automatic Neutral-1, project, app, focus switch or extra workspace is created.**
The user may select a project, deliberately start Neutral, or close the menu and
remain on the unowned desktop. Existing ordinary windows remain unowned; they
are not closed/moved/adopted.

The core's persistence/API is unchanged. This is downstream new-login policy,
not an ExecStartPost action: core/bar/config reload never authorizes another reset.
The `hyprland.start` hook and missing-helper plain Quickshell fallback remain.

## Initialization and readiness

The existing bounded readonly registration/IPC/core readiness checks, exactly-one
compositor/monitor guard, scoped-scratchpad refusal, private raw state/core backup,
desktop lock and guarded stop acknowledgements remain. The previous owners/
allocator are not inherited across compositor signatures. Current ordinary IDs
are projected as unowned; the active ordinary workspace stays unchanged.

After stopping only the captured old instances, require an empty/no-active core
reply and unchanged ordinary workspace/no visible special workspace. Unexpected
concurrent state is reported, never repaired or deleted. No mutating call is
retried after an uncertain acknowledgement. Failed initialization still exposes
the recovery bar once; manual SUPER+ESC remains available.

The earlier late-registration `hyprctl instances -j` malformed-JSON fix remains:
[R3 readiness diagnosis/tests](../../runtime/R3-startup.md).

## Once-per-instance marker and menu handoff

`${XDG_RUNTIME_DIR}/hyprland/session-startup.json` remains schema 1, protected by
the existing workspace lock:
- Write `initializing` before the attempt; successful empty startup writes
  `ready` with **`startup_menu: "pending"`**, not a session UUID.
- Ready/deferred same-login startup reentry does nothing and starts no extra bar.
  Failed/initializing reentry remains blocked. Different signature permits a new
  startup. Installers preserve existing same-signature markers, including failure.
- Quickshell's actual SessionMenu component starts a Process invoking
  **`session-startup --claim-menu`**. This mode only validates/claims the marker:
  no initializer, native/core queries, workspace changes, backup or bar launch.
- Only a matching-instance ready/pending request becomes `consumed`, durably
  under the lock, before returning `{"show":true}`. Missing/legacy/deferred/
  failed/initializing/wrong-instance/consumed markers return false unchanged.
  Malformed requests or failed publication return errors, never authorization.
- After a true reply, the menu discards in-flight old status and waits for a fresh
  confirmed empty/unowned snapshot. It calls its own `showMenu()` directly, with
  project search focused. No startup IPC availability race or fixed-delay timer.
  A manually opened menu or user-created session takes precedence.
- Closing/Escape and later polls/reloads/restarts do not reopen the request.
  SUPER+ESC is always an explicit manual alternative.

This is **at-most-once automatic presentation**, not a transaction with GUI
mapping. A crash after durable consumption but before showing can lose the
automatic opening; no potentially destructive initialization is replayed to fix
that. Startup errors do not manufacture ready menu requests.

## Deployment and compatibility

Use the full coordinated deployment to publish matching startup ELF and QML:
```sh
python3 runtime/install_desktop.py --apply --allow-notification-history-reset
```
The explicit flag requires user consent to Quickshell restart/RAM notification
history loss. Reduced/helper-only deployment does not activate the UI integration.
The normal configuration route uses the same coordinator; do not manually copy
QML or run the initializer to test this on current sessions.

Activated with explicit approval, generation `999b39e6c553b811c08c6944`, backup
`~/.local/state/linux-setup/desktop-cohort/20261121T104428-_1kqq1qj`, complete journal.
The current login had an older **ready** marker with no menu request (the earlier
readiness fix had succeeded). It was retained byte-for-byte. Exact current
core/desktop/ownership snapshots, personal desktop entries/history, index and core
PID were verified unchanged; only Quickshell PID changed as authorized. No live
initializer, session switch or artificial menu request was used for verification.
The changed startup policy takes effect at the next genuine graphical login.

## Validation

Complete runtime suite passes: **110 Rust tests** (80 desktop), strict fmt/Clippy/
offline release, existing navigation/notification/installer regressions.
- 12 unchanged refusal/deferred cases still match frozen R0; 11 current successful
  empty-start/new-login/reentry scenarios check no implicit start/focus/default
  workspace and one pending request. Historical Python/oracles remain unchanged.
- 13 CLI/admin cases include two simultaneous real claims (one true), old/wrong/
  failed/deferred/missing markers unchanged and no init/bar side effects.
- Real private v3 daemon/new-login/cohort tests verify zero sessions, no active UUID,
  unowned windows, same-login preservation and another empty state on new login.
- Exact menu-method tests cover fresh status/search, close/no reopen, manual use,
  user sessions and errors. Genuine QML menu/service plus the actual Rust claimant
  run on private D-Bus and temporary HOME/XDG paths. Only the native PanelWindow
  container is replaced by an offscreen Qt Window; real controls/Process/Connections/
  IPC remain, proving initial chooser, explicit project selection, Escape/restart
  and legacy-marker protection without using the live desktop.

Actual cold-login visuals remain normal user acceptance. The original 2026-11-18
Neutral-1 policy and original Python-only tests are historical, not the current
production bootstrap target.
