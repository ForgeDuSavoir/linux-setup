# SUPER+Shift+Y / SUPER+Shift+O — same-owner fresh workspace

Installed 2026-11-25. Adds two closed targets to the existing optimized
`workspace-controller open-new` workflow, no Control Center change:
- `youtube`: shared contextual launcher with `--youtube --expected-workspace ID OWNER`.
- `obsidian`: prepare the existing helper's readonly `--print-uri`, then call its
  new internal `--expected-workspace ID OWNER --expected-uri URI` mode.

Always allocate after the current workspace, even when empty; retain exact UUID
owner or unowned scope, guarded focus/empty confirmation, release lock, then final
fresh expected-context validation. No sleep/timer, new session, window transfer,
statistics event or old `HL_INITIAL_WORKSPACE_TOKEN` inherited by application.

YouTube retains project override/otherwise contextual Firefox URI, now combining
its existing mode with expected-workspace selection guards. No history/Rofi work.
Its `[expected-youtube-v1]` capability is required before workspace mutation.
Obsidian's `[expected-vault-v1]` capability and a valid registered URI are required
before creation; the child re-resolves its normal project-vault/Agora route and
rejects changed URI/context before invoking the absolute graphical Obsidian.
Explicit ordinary URI/file openings and normal O behavior are unchanged.

Application-level reuse remains possible: Obsidian may activate an existing vault
window, and a web app/browser may reuse one. This is a launch request from the new
workspace, not guaranteed GUI mapping or automatic reassignment of existing windows.
Cancel/failure/context change leaves the new workspace; no rollback/focus repair.

## Tests / installation

- 52 private real-controller/launcher cases (formerly 40), all seven targets across
  occupied/empty/unowned/project sources, stale token removal, lock release, no
  statistics, capability/missing-vault failures and changed context guards.
  Obsidian GUI is represented by a fake helper; no real vault window is opened.
- Full runtime suite/113 Rust/strict Clippy/fmt pass; existing real-private-core,
  Obsidian registry/route/installer and current YouTube GIO/profile tests pass.
  Real guarded Obsidian CLI invalid/missing/unavailable context probes fail before
  GUI, with private HOME/all XDG. Lua syntax/qmllint pass.
- Matching launcher + guarded Obsidian helper + movement-only cohort installed.
  Generation `ea19456a46f5456b98b69ab8`; complete cohort backup
  `desktop-cohort/20261125T104842-9ccpdt4s`, launcher
  `app-launcher-upgrades/20261125T094841-tADqLjPp`, Obsidian
  `obsidian-upgrades/20261125T104842-p7n5crs0` (private state/linux-setup root).
- Unique live Shift+Y/O and helper capabilities verified; exact core/desktop/state/
  marker/PIDs/index, existing Obsidian desktop and live QML preserved. No actual
  apps/vaults/profiles/workspaces opened to test. No Quickshell reload/history loss.
- Help row added in source, alongside the previous O/Y/Sleep source update; live
  help still awaits a separately approved full QML deployment. GUI acceptance of
  new-window creation/reuse remains normal user activity.
