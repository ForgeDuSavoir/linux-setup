# R2 — graphical adapter and guarded SUPER+Q

Implemented and isolated-tested on 2026-11-19. **Not installed or activated.**
R3 startup and R8 installer/QML cohort remain pending. The core repository and
its CLI/API, installed Python helpers, native windows and Quickshell are unchanged.

## Implementation

`desktop-tools/src/desktop.rs` reuses the R1 `Controller`/`LockedStore` for every
state operation. The CLI opens the existing workspace lock exactly once, then
calls library functions; it never spawns workspace-controller or takes another
workspace lock. `status` reads raw v2/v3 ownership without projecting/saving it,
including minimal legacy metadata. Missing/corrupt/unknown metadata and ambiguous
native context never trigger initialization, repair or a synthetic Neutral UUID.
As before, status may create/open the runtime directory and lock.

Commands: `start --neutral`, `start --project NAME`, `switch UUID`, `deactivate`,
`stop UUID`, `status`, `close [WORKSPACE_ID]`, plus read-only `--version`.
Arguments are parsed before lock/native/core IO; commands print one JSON reply
and errors use stderr/nonzero status. The version path needs no HOME/runtime.

`core.rs` invokes public `session-manager --json session ...` via literal argv,
respecting `SESSION_MANAGER_BIN` or the existing HOME default. Typed envelopes
cover nonempty session identities, membership/duplicates, closed launch sources,
active selection and session acknowledgements. Desktop `Owner` distinguishes
legacy Unowned, UUID-backed Session (including Neutral source) and Unknown. No
new registry, protocol, UUID allocation or core lifecycle policy is added.

`process.rs` adapts the already deployed launcher's direct-child IO pattern;
there is no crate/runtime dependency on its Gio/history/Git logic. Each core
request retains the **35 s** deadline; no mutating request is retried, including
lost/invalid JSON/acknowledgement or deadline expiry. Only the direct CLI helper
is killed/reaped on failure; no process-group or daemon kill. R1 native/lock waits
remain unchanged, and CLOSE-WAIT-001 is not fixed by R2.

Explicit fail-closed strengthening relative to Python:

- Core list must have a valid active field, distinct nonempty IDs and valid v3
  sources. Rows without source, unknown/extra source fields and empty project
  names fail before desktop mutation instead of relying on untyped partial data.
- Capture is bounded to **4 MiB per stdout/stderr stream**, matching the reviewed
  launcher transport pattern. Python capture had no bound. Limit failure is an
  uncertain result, not permission to retry. This is a local safety limit, not
  an upstream protocol/schema change.
- R1 filesystem protections remain in use. SessionId is a typed nonempty wire
  identity/membership check, not a replacement for core UUID generation or a
  security/authentication boundary. Unknown core response fields are retained
  in the JSON forwarded to clients; known source shapes are closed.

`SESSION_COLUMNS_SCRIPT` is deliberately no longer imported by the Rust adapter;
it was Python module-injection plumbing, not a runtime executable contract.
Native/core process injection remains possible via the existing PATH and
SESSION_MANAGER_BIN interfaces in private tests.

## Preserved policies

- Fresh session starts get a new empty UUID-owned workspace, never adopt windows;
  switch chooses preferred/existing owned workspace or allocates fresh if absent.
  Empty-workspace cleanup does not stop the logical instance. Explicit deactivate
  selects the legacy unowned space without stopping instances.
- Graphical mutations still require one monitor; status can select the focused
  monitor (or the sole monitor fallback), checks native/logical owner and known
  session IDs, and conservatively marks ambiguous/stale scope unconfirmed.
- Menu stop rejects the last open session before hiding/saving, guards normal and
  all five scoped scratchpad windows, selects the next survivor in opening order
  with wrap **before** stop, confirms switch/focus and rechecks source windows.
  Inactive stop leaves selection unchanged. Failed/uncertain fallback or stop
  does not authorize ownership deletion/replay/automatic rollback.
- Q uses the keypress workspace ID. Close is **explicitly addressed** and guarded
  by current workspace, special workspace, active address, mapped/visible flags
  and target workspace in one native Lua evaluation. An empty workspace with
  other owned/scoped windows cannot stop the session. An empty unowned desktop
  is a no-op; global/scoped scratchpads close only their confirmed visible target.
- Raw JSON status fields used by SessionService are retained, with the same
  displayed_context/context_confirmed fields. Installed Lua bindings still pass
  the frozen Q workspace, so a queued second Q cannot act on the survivor.

General start/switch/deactivate semantics are the frozen Python policy; R2 does
not claim a cross-core/native atomic transaction or redesign all acknowledgement
rules. Fallback switch and stop acknowledgements are strictly checked before
continuing; an uncertain result may leave logical/native context mismatched for
manual recovery, never silently repaired.

## Evidence

From repository root:

```sh
bash runtime/check.sh
```

This now includes:

- **33 Rust tests total** (21 R1 + process transport + v3/owner/argument tests):
  closed Source shape (including extra fields on Neutral), identities, bad acks,
  literal project names, preserved default deadline, bounded output and actual
  direct-child timeout/reap/no replay. All pass with fmt/Clippy strict/release
  locked offline; no additional Cargo dependency was required.
- **52 R2 real-CLI differential scenarios** vs frozen R0 Python: the 18 prior stop
  behavior areas, close behavior areas from the 15-case suite, start/switch/
  deactivate, status v2/v3/missing/unknown/focused-monitor/scratchpad variants,
  last/inactive guards, failures, silent focus, late windows, external selection,
  invalid acks and lost stop replies. Each uses its own private HOME, metadata,
  strict fake native/core executable and result/event/ownership comparison.
- **12 R2 CLI tests**: invalid syntax before IO, no-resource version, status shape,
  minimal/missing/unknown metadata without save, actual Python flock blocking a
  Rust process before native/core requests, unavailable/malformed/missing-source
  core data without fallback, literal argv, old module override not imported,
  corrupt/symlinked state refusal and actual Lua Q-binding keypress freeze.
- Window-close guard code from **both** implementations executes with actual Lua
  against fake hl getters/dispatchers: address/workspace/visibility races refuse,
  visible ordinary/scoped/global windows issue exactly one addressed close.
- **Actual installed protocol-v3 core binary, private daemon/HOME/socket**:
  two Neutral UUIDs on fresh fake workspaces, empty-session Q fallback, last-session
  refusal without metadata/revision change, inactive normal-window guard, project
  source lifecycle, addressed close without logical stop and explicit unowned
  deactivate. Fake hyprctl/Lua only; no real window, terminal/model/app or live
  core session was touched. The test daemon is terminated/reaped in finally.
- R1 **61 differential + 19 actual-CLI cases** remain green. Existing Python stop
  **18**, close **15**, desktop/status regressions and SessionService JS tests also
  pass. Their success alone is not presented as Rust parity.

The private-core test uses the installed binary, not a development checkout or a
new daemon on the user's socket. It writes only its temporary root. The normal
check script therefore requires an already available protocol-v3 binary at the
usual installed path; it never builds/upgrades/starts the real service.

## No activation in R2

The installed Python startup still imports session-desktop as Python; Quickshell
still invokes the controller with python3; installers still copy/import Python.
[R3](R3-startup.md) now provides the Rust startup and pure admin ABI in isolation.
Do not replace those files or invoke a migration/reset to validate R2/R3; R8 must
prove the compatible cohort and installer-admin/caller changes. A watched-QML reload
or login transition remains separately user-controlled with history implications.
No such approval is inferred from implementing R2.
