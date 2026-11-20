# Single-workspace navigation

## Status

Approved replacement for the two-row column model, deployed on 2026-11-17 through the coordinated installer after explicit approval of the Quickshell restart/notification-history reset. Exact before/after comparison preserved real windows, workspace IDs and visible monitor contexts. No live workspace was created, moved, renamed or closed as a test. The core service PID and complete session projection remained unchanged.

The navigation model itself is entirely downstream desktop policy. The Session Manager core API/runtime schema, existing session identities and application resolution do not change. The separate [new-login initialization policy](../session-manager/session-startup.md) now explicitly replaces old open instances with one Neutral-1 at the next graphical connection; it is not a navigation cleanup or daemon-restart action.

## User behavior

- **SUPER+S:** cycle the ordinary workspaces of the displayed session, in list order, wrapping at the end. Never enter another session's workspace.
- **SUPER+Tab:** if the current workspace is occupied, create/focus a fresh empty workspace immediately after it, inheriting its UUID owner but no windows. If it is empty, return to the preceding existing workspace of the same owner and forget the empty source. No wrapping: without a predecessor, leave the current empty workspace displayed and allocate nothing.
- **SUPER+Shift+Tab:** with several windows, isolate the active one in a fresh workspace immediately after the current one and follow it. If it is already alone, join the nearest preceding occupied workspace of the same owner, without wrapping; with no such predecessor, do nothing. This naturally undoes isolation without recording provenance.
- **SUPER+Shift+S:** move/follow the active window to the next existing workspace of the same owner, wrapping to the first. Never create a workspace; with no other workspace, do nothing. Leaving a sole-window source removes its now-empty workspace. The second row and temporary vertical animation overrides remain removed; ordinary compositor animations are unchanged.
- With a visible scratchpad on the focused monitor, S/Tab/bar navigation first hides that scratchpad and consumes the command. Another press performs navigation/insertion. Navigation never closes scratchpad windows; explicit SUPER+Q closure is described below. Shift window-move shortcuts retain their behavior.
- A departed empty workspace is forgotten. Closing its last window selects the previous occupied workspace of the same owner, otherwise the next, and drops the empty one. If the last workspace of a context is still visible, it must remain as one empty workspace: never jump to another session merely to eliminate it. It is dropped when that context is left, and selecting that still-open logical session later creates a new empty workspace as needed.
- Five UUID-scoped scratchpads, the shared global scratchpad, legacy unowned desktop and window guards remain intact; graphical stop follows the survivor policy below. Empty-workspace cleanup never stops a logical session.

## Graphical session stop (2026-11-18)

- Refuse to stop the last open session, even if explicitly deselected. Return an error before metadata writes, hiding a scratchpad or core mutation; starting another session remains an explicit user action.
- Stopping the active session selects the next survivor in the shared opening order, wrapping to the first. Switch the logical role, focus its remembered workspace (or allocate a fresh UUID-owned empty one), and confirm focus/core selection **before** stopping the original session. Never fall back to the unowned desktop or create a logical session.
- Preserve the original workspace ownership during this transition and check its ordinary/scoped-scratchpad windows again before stop. A late window blocks deletion. Existing window guards still apply before switching.
- Stopping an inactive session leaves the active context unchanged. Refuse a retry that would stop the physically displayed session while another session is logically active: select a confirmed context first.
- These are graphical-client policies under the shared desktop lock. Direct core CLI/API stop and explicit **Deselect session** remain unchanged. Core switch/stop are separate requests, not an atomic transaction against independent direct clients. If focus/stop fails after switching, selection may already have changed; the original is not deliberately stopped until fallback succeeds. Lost/invalid acknowledgements are not replayed or presented as rollback. Concurrent core-selection changes are reported rather than silently repaired.

Deployed using the movement-only installer, without replacing QML or restarting Quickshell/core. Exact desktop/core projection and both PIDs stayed unchanged; no live session lifecycle/navigation test was performed and notification history was preserved.

## Stable IDs and explicit order

The existing script/metadata filenames (`workspace-columns.py`, `workspace-columns.json`) are retained to avoid unrelated path changes, but there are no columns in the new model.

Desktop metadata **version 3** has `order` (unique positive real workspace IDs), `owners` (ID to UUID or legacy `neutral`), `preferred` (owner to real ID), `next_id` (monotonic allocation cursor). This is independent of the core runtime's version number. It is protected by the existing shared `workspace-columns.lock`.

IDs are opaque identities, not positions. Insertion uses a fresh ID and inserts it into `order`; it does not renumber any existing workspace or move its windows. Cleanup compacts the list only. The bar consumes the controller's read-only `snapshot` and displays positions 1..n for the focused context, including its currently empty workspace; clicks carry real IDs. Logical session order in the session strip is unaffected.

Allocation advances `next_id` even after a failed native acknowledgement to avoid reusing an ID while old close events may still be queued. Fresh focus/isolation dispatches use a compositor-side guard (`hl.get_workspace`) and dispatch in one Lua evaluation: a target that already exists is rejected rather than silently joining/adopting it. No animation setting is changed by that evaluation. Failed/uncertain fresh dispatch removes the provisional ownership reservation without attempting to move windows back or claiming that an unconfirmed workspace belongs to the session.

Native workspace-active/removed hooks request serialized metadata-only cleanup, including mouse, session-menu and external switches. A visible empty workspace on another monitor is not deleted. The existing single-monitor restriction for logical context switches remains unchanged.

## Guarded SUPER+Q (2026-11-19)

The binding freezes the current ordinary workspace ID at keypress and invokes
`session-desktop close ID` under the shared workspace lock. A queued second Q
cannot act on the newly selected survivor of the first Q.

- A confirmed active window on the displayed ordinary workspace or visible
  allowed scratchpad is closed by **explicit address**. Native workspace,
  special workspace, active address, mapped/visible flags and window workspace
  are rechecked in the same Lua evaluation as dispatch. Never use an implicit
  last-focused-window target that might belong to a hidden session.
- If no visible target exists and the **entire current UUID session is empty**,
  use the existing menu stop policy: next survivor in opening order with wrap,
  confirmed switch/focus before stopping. Preserve refusal of the last session,
  failed-focus safety and uncertain-result/no-replay behavior.
- A blank workspace does not authorize stopping a session with windows on
  another owned workspace or any of its scoped scratchpads. An unowned desktop
  is not a logical Neutral instance and empty Q there is a no-op.
- Logical/native mismatch, foreign/unconfirmed special workspace or context
  changes refuse the action rather than closing a different window/session.

The installed compositor's `LuaBindingsInternal.cpp::pushWindowUpval` and
`LuaBindingsDispatchers.cpp::hlWindowClose` were read at its exact upstream
revision: the explicit selector is the table field `{ window = "address:..." }`.
Constructing a string argument is accepted but does **not** select that address.
No real close dispatcher was executed as a probe.

`test-session-close.py`: **15 isolated tests**, including execution of the
generated guard and actual keybinding in Lua with fake `hl`, residual foreign
focus, visible/scoped/global windows, blank-but-nonempty sessions, last/unowned
session, queued Q, native address/workspace/visibility races, core revision
changes and failed survivor focus. The 18 existing menu-stop tests, 36 workspace
tests, status/controller/install tests and private real-core regressions pass.
Install via `--apply --movement-only`; no actual window/session close or switch
is an installation test. QML shortcut-help source is updated but copying it
remains deferred until an explicitly approved shell reload/history reset.

## Metadata-only upgrade

The v2 projection splits each old column into its actual ordinary workspace IDs, mapping both occupied rows to the old UUID owner. Order follows old column/row order, preferences follow the remembered row when present, while old isolation origins are discarded. A missing empty anchor is represented once until normal cleanup; it is not a reason to keep departed empty workspaces forever.

No workspace ID, window destination, focus, scratchpad name or core state is altered by this projection. Existing old scratchpad windows are never adopted or migrated. Read-only status/bar calls can project legacy metadata in memory without writing it. The coordinated installer explicitly saves the new metadata under the shared lock. A fresh missing file only registers currently existing workspaces as unowned; the historical physical workspace/scratchpad migration has been removed.

## Movement-only revision (2026-11-17)

The revised Shift actions and the later Tab create/return behavior are deployed through the movement-only installer. Their behavior depends solely on the current ordered workspace list: the old origin/address map and origin-driven next-target algorithm have been removed. Legacy `origins` fields are ignored by the pure projection and discarded on the next metadata write, without changing metadata version, existing IDs, owners or core sessions.

The coordinator can now update only bindings/controller/desktop helper and reload Hyprland. It never queries/restarts Quickshell or replaces any QML file in this mode; the installed shortcut-help text is intentionally left until a separately approved full QML installation/reload. Functional Shift bindings are active immediately and notification history is preserved. Movement-only mode requires the single-list model already installed; it cannot partially migrate an old two-row bar.

```sh
python3 configs/hypr/install_workspace_navigation.py --apply --movement-only
```

## Installation

Inspect the plan without changing anything:

```sh
python3 configs/hypr/install_workspace_navigation.py
```

After explicit approval of the RAM notification-history reset:

```sh
python3 configs/hypr/install_workspace_navigation.py \
  --apply --allow-notification-history-reset
```

The coordinator verifies protocol compatibility, selects only the known Quickshell instance by configuration path/executable/UID, makes a private backup, and holds the shared desktop lock. It stops only that shell, applies the versioned targeted installer (controller, bindings, cleanup hooks, desktop helper and shell), saves the metadata-only projection, reloads Hyprland and restarts that known shell. It compares window/workspace and monitor context snapshots before/after. It never restarts the core service, starts/stops a core session, launches an application or repairs a mismatch by moving windows. Failures require inspection of the backup; no automatic rollback or false success.

Backups and native snapshots are private under `${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/workspace-navigation/`; none belong in Git. The explicit approval gate runs before any live action. An absent shell is not started just for installation.

## Deployment evidence (2026-11-17)

The real coordinated installer completed with a private backup. Installed controller, bindings, cleanup hooks, desktop helper and shell bytes match their sources. The desktop state is version 3; read-only status confirms the same logical/graphical context, and the ordered snapshot includes the current workspace even if empty. Native binding inspection shows the new S/Tab bindings, retains Shift+Tab and contained no Shift+S binding at that initial deployment. The later movement revision adds Shift+S for existing-workspace movement. Hyprland reports no configuration errors; Quickshell loaded with only the already known PopupWindow deprecation warnings.

The core was not restarted or mutated: its PID, session projection, revision and active role match the pre-install snapshot. Window/workspace and monitor active/special context snapshots match exactly. Quickshell restart and its RAM history reset were explicitly approved. Visual interaction acceptance remains manual; none of these checks creates a real workspace or launches an application.

## Isolated evidence

- `configs/hypr/tests/workspace_columns_test.py`: **36 tests** for pure v2 projection, stable ID/order insertion, create/return toggling on repeated Tab, scoped cycling, active/inactive close, final-empty/other-monitor retention, isolation/previous and existing-next/wrap behavior, retired origin metadata, native target races, uncertain acknowledgements, ID limits, removed row commands and Lua guard execution against a fake `hl` object.
- `navigation_scratchpad_test.py` and `scratchpad_session_test.py`: hide-first navigation/insertion and UUID/legacy/global routing remain isolated.
- `workspace_install_test.py`: real targeted scripts in temporary HOME/XDG roots with fake native tools; dry run, full-reload approval rejection, private backup, metadata-only upgrade, unchanged windows and no dispatcher calls; movement-only mode succeeds without any Quickshell call or QML replacement.
- `test-session-desktop.py`, `test-session-status.py`, `test-neutral-v3.py`: logical sessions survive removal of departed empty workspaces, later selection creates fresh empty workspaces, normal/special window stop guards and shared lock remain intact, and status is read-only for both metadata versions.
- `test-session-stop.py`: **18 fake core/desktop cases** for next/wrap, fresh UUID-owned fallback, last-session refusal without effects, inactive stop, ordinary/special window guards, failed/uncertain requests, late windows and external core-selection races. `test-neutral-v3.py` additionally exercises fallback and revision-stable last-session refusal against a real private v3 daemon.
- Existing offscreen QML, session-service/menu and private D-Bus notification regressions pass. Qt 6 lint and Lua syntax checks pass without a live desktop interaction.

Visual acceptance of the actual key sequences is manual after the approved deployment. The shortcuts are installed; no automated claim of real key-sequence interaction is made.
