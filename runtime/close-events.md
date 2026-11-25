# CLOSE-WAIT-001 — address settlement outside the desktop lock

## Current behavior — installed 2026-11-25

The close callback passes `closed-event WS ADDRESS EPOCH` (validated positive ID,
hex address, integer epoch). It copies scalar values only, not a retained native
window object. The exact installed Hyprland commit
`efb50993780079460b0cbed1363e2166a2de1d9f` wires Lua window.close to the event bus
in LuaEventHandler.cpp; Window.cpp emits close around line 2575, before clearing
m_isMapped around line 2644. No assumption that callback-time clients are settled.

The worker captures owner metadata briefly under the common lock, then releases
it. Bounded readonly queries wait only for the **captured address** to disappear,
never for unrelated windows. Another window on that workspace returns immediately.
A moved closing address returns without action. A remaining address is sampled
at 25 ms intervals with a two-second budget; each subprocess deadline uses the
remaining budget, and direct children are killed/reaped by the existing transport.
These waits/child deadlines never hold the shared desktop lock.

After settlement, reacquire the lock and revalidate owner, address absence and live
clients. The locked closed handler performs a single fresh occupied-workspace
snapshot, with **no sleep/polling**. Existing previous/same-owner occupied fallback
and metadata cleanup remain; no core session lifecycle action or owner transfer.
Legacy `closed WS` remains a nonwaiting single-snapshot compatibility command.

A compositor-local navigation epoch increments on every workspace.active and each
config reload. Old/duplicate workers are rejected, including navigation away and
back to the same workspace. Final focus Lua atomically checks epoch, active source,
no special workspace, single monitor, empty source and existing occupied target.
Preferred metadata is updated only after a successful guarded focus. No focus retry,
rollback, global event daemon or persistent project/session registry is added.
Uncertain native publication still requires inspection, never automatic replay.

## Validation

`tests/test_close_event.py`: actual Rust CLI, fake native executable, private HOME/
all XDG roots/metadata flock. Other-window return ~64–90 ms with Python fixture
startup overhead, instead of historical 2000 ms requested sleeping. Delayed close
allows a second real snapshot command while still pending; parent also acquires
the common lock nonblocking during settlement. Navigation away/back, duplicate
notification and changed owner cannot focus. Timeout and a slow child finish around
2.05–2.07 s **without monopolizing the lock**. These are synthetic command timings
and lock-availability checks, not a production lock-hold percentile or GUI benchmark.
Exact generated final Lua also executes against epoch/source/count/target/special
race fixtures. Frozen R0 evidence remains unchanged: one differential case now
explicitly expects zero sleeps rather than the old forty; other outcomes match.
Full runtime suite passes (113 Rust), strict Clippy/fmt/release and Lua syntax pass.

## Deployment

Generation `22114c17a7f57d39e58d5bd2`, complete movement-only backup
`desktop-cohort/20261125T095150-5z_u3pbq`. Installed helper/hook bytes verified and
readonly live eval confirms the epoch is visible in the evaluator. Exact core/
desktop/ownership/marker, index/keybinds/QML/ordinary helpers and shell/core PIDs
unchanged. Hyprland reload only; no Quickshell restart/notification loss, real
window close, workspace switch, session action or initializer used for testing.
User acceptance: repeat SUPER+Q and SUPER+S after closing, both with another window
remaining and after closing the last window. Other short IPC/lock costs can remain;
this fixes the specific workspace-empty wait under the common lock.
