# SUPER+F1 — attention-first session navigation

## Status

Implemented, tested and **activated on 2026-11-20** after explicit user approval
of the Quickshell restart and notification RAM-history reset.
Active generation: `a3c8cad3a5fab1959be14a9f`.
Earlier staging preserved live files; activation then published the intended
SessionService.qml, SessionMenu.qml, shell.qml and F1 binding changes.

## Selection policy

`SUPER+F1 → quickshell ipc call sessions nextAttention`.

Use exactly `SessionService.sessions`, the ordered array displayed by
SessionStrip, not alphabetical order or notification arrival order:
1. First row with `NotificationStore.hasUnread(row.id) === true`.
2. Otherwise successor of active session, wrapping to the first row.
3. No active session: first row. Zero rows or only the current row: no switch.

Neutral UUID sessions participate normally. Global, unknown, unowned-desktop
and orphan notifications do not create arbitrary session targets.

## Architecture and sequencing

The existing sessions IPC handler forwards to SessionService; shell.qml wires
the existing NotificationService as its notification state. No second store,
new daemon/project registry or core protocol change.

Service navigation phases:
- `idle`: accept a shortcut unless another action is running.
- `choose`: invalidate the old generation and request fresh desktop status;
  wait for an older read to finish if necessary, never use its obsolete reply.
  Refuse unconfirmed/unavailable state. Reconcile notification policy against
  the confirmed current context, then select one target.
- `confirm`: use the existing serialized `session-desktop switch UUID` path;
  remain busy through action exit **and** its immediately requested status read.
  A confirmed displayed UUID completes the request; no further automatic switch.

Additional shortcuts/manual actions are ignored while busy, not queued against
old unread flags. Existing two-second status polling remains; the shortcut and
post-action refresh do not wait for it. No timer, sleep or retry loop is added.
Qt.callLater only schedules the refresh on the event loop.

NotificationStore alone acknowledges actual confirmed visibility through its
existing policy. The shortcut never clears unread flags optimistically. Backend
failure or a successful hide-first action that did not reach the target does not
acknowledge that target or auto-replay the switch. Missing/unconfirmed snapshots
release busy with an error. Later normal status reads may naturally acknowledge
a context that is actually confirmed, including after an uncertain action reply.

Desktop switching continues to own workspace selection and existing safeguards;
no window adoption/movement policy is introduced. Attention is evaluated once
at selection time; new notifications do not continuously retarget an in-flight
switch. There is no atomic transaction across notification receipt, backend
actions and independent compositor changes.

## Validation

Complete `bash runtime/check.sh` passes, including existing runtime/media/
notification suites and the corrected isolated SUPER+Tab tests.
- `test-session-service.js`: existing ordered/status/generation regressions.
- `test-session-attention.js`: exact QML methods with real notification policy,
  non-alphabetic bar order, priority, wrap, repeated presses, busy until confirmed,
  errors, old read generations, orphan/current/Neutral/unowned/empty/single cases.
- `test-session-attention-qml.py`: actual service, real IPC forwarding function
  and NotificationStore/server on a **private D-Bus** with fully temporary HOME,
  XDG data/config/cache/state/runtime and fake desktop backend. Real synthetic
  D-Bus notifications verify acknowledgement, coalescing, failure/hide-first,
  reordered rows, global/unowned exclusion and invalid/unconfirmed snapshots.
- Qt6 qmllint succeeds with existing type/unqualified-access warnings.

No personal notification bus/content, history/usage file, session or window was
used as a test target. No live shortcut or switch was invoked as a test;
the later authorized deployment restarted Quickshell.

## Coordinated activation

```sh
python3 runtime/install_desktop.py --apply --allow-notification-history-reset
```

Use the full coordinated path, not movement-only or manual QML copies: F1 and
its IPC handler must be deployed together. The normal installer stages the same
assets. The coordinator provides private backups/journal and immediate logical/
desktop/state comparisons. Existing notification RAM is not persisted or exported
as a workaround. Explicit restore also requires the appropriate reload consent.

Activation completed with backup
`~/.local/state/linux-setup/desktop-cohort/20261120T150245-r2l_slj8`, journal
`complete`. Coordinator-persisted before/after snapshots are identical; a later
readonly check also matched the current core/desktop and exact workspace state/
startup marker to those originals. Active generation, installed source bytes,
one F1 binding, empty Hyprland config-error list and running Quickshell verified.
`quickshell ipc show` confirms `sessions.nextAttention(): void` is available,
without invoking it. The extra manual baseline attempt failed on a PID-helper
signature before saving; verification instead uses the coordinator's actual
persisted baseline, not an invented manual one. No separate pre/post PID or
personal-file hash comparison is claimed from that failed capture.

Normal user acceptance should cover leftmost pending selection,
successor/wrap, repeated presses and a failed/unconfirmed navigation. No implicit
personal-session test or synthetic notification on the real bus is permitted.
