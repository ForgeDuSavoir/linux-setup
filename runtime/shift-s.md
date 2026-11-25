# SUPER+Shift+S — next workspace or tail split/wrap

Installed stage 2, 2026-11-23. Existing `move-next` command/keybind retained.
Only the same owner's explicit metadata order matters (UUID or unowned `neutral`),
not numeric IDs, other sessions' workspaces or window origins.

- A next workspace exists: move the captured focused window there and follow,
  preserving previous behavior.
- Source is the owner's last workspace and contains more than one window:
  allocate a fresh workspace immediately after it, same owner, move/follow there.
- Last workspace contains exactly one window: move/follow to the owner's first
  workspace; existing cleanup drops the emptied source. If first == last, no-op.
- No ordinary focused window / special-workspace window: no-op as before.

Tail branch revalidates source workspace, captured window still in that source,
active workspace and shared/singleton count in the same Lua eval as movement.
Fresh target collision and existing target disappearance are refused. No sleep,
new daemon, core session lifecycle change, owner transfer or mutation retry.
Existing reservation/error handling is retained; a lost native acknowledgement
may have committed movement, is never replayed and does not authorize repair.

SUPER+Tab and SUPER+Shift+Tab were subsequently unbound in stage 3; this does
not alter the Shift+S policy above. Legacy CLI helpers remain compatible.

## Validation/deployment

- Eight current-policy scenarios using the real Rust controller with in-memory
  compositor: shared/singleton tail, single-workspace variants, normal successor,
  explicit reordered/interleaved owners, rejection and uncertain acknowledgement.
- Actual generated Lua executed against synthetic source/count/window/target races.
- 61 frozen historical differential cases still pass (none covers the newly added
  shared-tail split); frozen oracles untouched. Full runtime suite passes, 113
  Rust tests plus current policy/native/CLI/core/cohort/notification regressions.
- Active generation `edda5c9ff56e730dd0a893d9`, complete movement-only backup
  `desktop-cohort/20261123T092015-pvdb36hb`. Exact core/desktop/ownership/marker,
  index/keybinds/QML/ordinary helpers and shell/core PIDs unchanged. No real window
  transfer, workspace creation, app, initializer or Quickshell reload used to test.
  Normal visual acceptance remains user-driven.
