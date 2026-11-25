# Workspace / session / scratchpad animations

Installed 2026-11-25:
- ordinary workspace changes within the same owner: **slidevert**;
- session/context transitions: **slidefade** (horizontal slide + fade);
- special workspace show/hide (scoped/global scratchpads): **slidefadevert**.
Ordinary/session duration and curve remain 5/wind. Scratchpad opening and closing
were subsequently tuned to 3/scratchpadEase (about 300 ms), entering from above
(`slidefadevert top`) and retracting upward (`slidefadevert bottom` on exit).
Distance remains unchanged; control points (0.16,1)/(0.3,1) provide ease-out without
overshoot. Explicit specialWorkspaceIn/Out override the old parent 6/default.

`visuals.lua` defines the ordinary baseline once as
`_G.__workflow_workspace_animation` and applies it with hl.animation. Session focus
uses Controller::select_session and native::session_focus, not shortcut-specific
wrappers. It preserves reservation/collision/owner/store/failure behavior and runs
one Lua evaluation: protected temporary slidefade -> synchronous focus dispatch ->
restore baseline -> propagate errors. Baseline speed/curve/enabled are read from
the shared table, not duplicated per action. A 5/wind/slidevert fallback only
supports older configs lacking the table. No timers, animation-completion waits,
background restoring process or extra config IPC under the metadata lock.

Affected semantic routes: desktop Start/Switch/Deactivate (including menu, strip
and F1) and active-session stop survivor selection. Inactive stop does not focus.
Ordinary cycle/new-workspace/move/fallback-after-window-close retain default
slidevert. Special hide before switching uses its independent style. No session
lifecycle/notification/workspace ownership policy changed.

Exact installed Hyprland commit efb50993780079460b0cbed1363e2166a2de1d9f,
`src/animation/WorkspaceAnimationController.cpp`: startAnimation copies ANIMSTYLE
and initializes offset/alpha values/goals synchronously. Restoring only style
immediately after dispatch does not re-run initialization or replace those goals;
this is not a completion timer. Interactive/swipe behavior outside our desktop
session actions continues to use the default style, not inferred session ownership.

## Scratchpad tuning — installed 2026-11-25

Generation `8a76fb69f70923a4ff2188eb`, complete visuals-only backup
`desktop-cohort/20261125T114743-pi_wfqn8`. Lua recorder test executes the actual
visuals file, checks both leaf styles/speeds, monotonic bounded curve and unchanged
workspace baseline. Session override/restore tests and private visuals apply/restore
pass. Live animation/curve query confirms only specialWorkspaceIn/Out and the new
curve differ; exact state/PIDs/QML/index/bindings preserved. No actual scratchpad
opening/closing used to test; visual feel remains normal user acceptance.

## Initial context-policy validation / deployment

- Actual desktop CLI generates the animation Lua for start/switch/survivor/
  deactivate; tests execute that exact code with synthetic dispatch success,
  failure and fresh-target collision. Slidefade is observed at dispatch, baseline
  restored before exit, including custom baseline speed/curve. No real focus.
- Full runtime suite/113 Rust, strict fmt/Clippy/release and Lua syntax pass.
- Visuals-only coordinated activation, generation `2ee81a6a07762970dc5df9e4`, complete
  backup `desktop-cohort/20261125T113717-z5b0j7en`. Session helper and visuals bytes
  match source. Actual animation map differs only in workspaces.style and
  specialWorkspace.style. A live Lua animation-API error/restore probe (no focus
  dispatch) verifies the baseline is present/restored; other settings unchanged.
- Exact core/desktop/ownership/marker, core/shell PIDs, index/QML/keybinds/ordinary
  helpers preserved. No Quickshell restart or real window/session switch used to
  test. Visual appearance of all three routes remains user acceptance.

Apply source/native pairing with:
`python3 runtime/install_desktop.py --apply --visuals-only`.
