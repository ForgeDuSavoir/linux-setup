# Replace the empty current session when starting another

Installed desktop policy, 2026-11-24. Applies to `session-desktop start --neutral`
and `start --project NAME` (the menu's existing start path), not direct core API,
Switch, explicit Deactivate, arbitrary inactive sessions or new-workspace shortcuts.
The core remains independent and unchanged. No QML change/reload is required.

1. Capture the active UUID from the initial session list, only if the displayed
   ordinary workspace belongs to it. Preserve the original ownership snapshot;
   empty-workspace cleanup must not conceal windows arriving in an old workspace.
2. Start the requested session through the public API, validate acknowledgement,
   allocate/select its workspace as before. No old-session emptiness probe yet.
3. For distinct old/new UUIDs, confirm target workspace active, no visible special,
   and fresh core list contains/activates the acknowledged new UUID.
4. If the old UUID remains open, perform **one** session-emptiness check via the
   same shared helper as guarded manual stop: no clients in *any* original owned
   ordinary workspace or UUID-scoped special slot, including hidden scratchpads.
   Occupied -> retain without error. No previous active UUID -> no auto-stop.
5. If empty, stop only that old UUID once; verify stop acknowledgement and fresh
   core outcome (old absent, new still active), remove obsolete ownership/preference
   metadata using the existing cleanup. Return the original new-session reply.

A failed/uncertain start or unsuccessful desktop confirmation never authorizes
old-session stop. A window arriving before the post-focus check preserves the old
session, including in another previously empty workspace. Switching to an already
open session does not retire anything. No window move/adoption, old workspace
reuse, persistent history/profile deletion, background sweep or new daemon.
A stop rejection/unknown acknowledgement is an action error, not an undo of the
already opened session; no retry or automatic rollback. The GUI/client APIs do not
provide a transaction locking window arrival together with logical stop: a later
arrival after the final emptiness sample remains a concurrency limitation.
Normal manual stop retains its existing survivor/last-session policy.

## Validation and installation

- Full runtime suite/strict Clippy/fmt/offline release: 113 Rust tests and existing
  CLI/core/cohort/navigation/notifications pass.
- 16 dedicated real-desktop-CLI cases, fake native/core in private HOME/XDG only:
  Neutral/project replacement; ordinary/other-workspace/hidden scoped/late windows
  (also late in another cleaned empty workspace); unowned/mismatched display,
  Switch, failed/silent focus, changed selection, rejected/uncertain stop and
  post-stop race. Only original UUID stop, after focus, no mutation replay.
- Real private v3 daemon verifies replacement removes an empty UUID, but a window
  keeps the prior session; existing fallback/last-session/close guards still pass.
- Frozen oracle unchanged: 50 unchanged cases compared; two start cases explicitly
  check the new empty-replacement outcome instead of pretending old parity.
- Generation `297e10c961c723147660d3b1`; complete movement-only backup
  `desktop-cohort/20261124T185405-mu4ahg_b`. Exact live core/desktop/ownership/marker,
  core/shell PIDs, index/keybinds/QML and ordinary helpers preserved. No real session
  start/stop/switch or initializer used to validate. User GUI acceptance remains open.
