# R3 — per-compositor startup and pure installer administration

Implemented and isolated-tested on 2026-11-19. **No live installation/activation,
logout, core reset or real bar launch.** The three Rust runtime components are
now implemented; R8 must still convert the actual installers/callers and activate
a compatible cohort with explicit Quickshell/history consent.

## Runtime lifecycle

`startup.rs` uses the R2 Desktop/R1 Controller library and the same owning
LockedStore. No Python imports, nested controller process or nested flock.
`session-startup` accepts no operational CLI arguments; `--version` is read-only.
The hook must remain `hyprland.start`, not config/core/Quickshell reload.

- Require nonempty HYPRLAND_INSTANCE_SIGNATURE, at most 512 Unicode characters.
- Marker remains `session-startup.json` schema 1: instance, phase and optional
  extra fields such as session_id. Ready/deferred in the same instance returns
  immediately without native/core queries or another bar. Initializing/failed
  in the same instance returns an AlreadyAttempted failure; never replay reset.
- For a new instance, durably write initializing **before** effects. Require
  exactly the matching compositor, one monitor, and no scoped scratchpad window.
  Existing normal windows are retained; global scratchpad can be hidden, not closed.
- Read-only core availability probes retain 2 s individual deadlines, approximately
  10 s overall wait and 100 ms intervals. Only transport.unavailable and probe
  timeout are retryable; upgrade/recovery/invalid response errors fail immediately.
  An in-flight last probe can extend the overall budget, matching Python.
- Archive raw previous ownership bytes and core-before JSON in a new private
  session-startup-backup-* directory, then project currently existing native IDs
  to unowned state. Ignore old ownership/allocator across compositors; never
  adopt newly appeared normal windows into a logical session.
- Stop the captured old open instances through the core public API, intentionally
  bypassing the **UI** last-session/window guards for this new-login policy.
  Require empty logical state before starting one Neutral UUID, allocate/focus
  a fresh guarded workspace, and confirm that sole session is Neutral-1 and the
  expected ordinary workspace is displayed without special workspace.
- Write ready with session_id. Stop/start calls retain 35 s per-request deadline;
  no mutation replay, no automatic rollback/ownership/window repair after uncertainty.
- On first-attempt failure after initializing, record failed and log once before
  exposing the bar for manual menu recovery. Failed/initializing reentry never
  launches another bar. On success exec the bar only after initialization;
  owning lock/fds are dropped before exec. Ready/deferred reentry launches none.

Malformed/unreadable markers are not overwritten to "repair" them; no core reset
is authorized. As in Python, an error before a valid attempt can be recorded may
still expose the recovery bar on each manual invocation. Exactly-once recovery
bar behavior is claimed for **valid persisted phases**, not arbitrary corruption,
missing permissions, loss of runtime storage or failure of the bar itself.

## IO and failure boundaries

R1's directory-relative storage is reused for marker publication (0600 temporary,
file fsync, atomic rename, directory fsync). Refuse symlink/nonregular/linked/
foreign marker/state files; do not follow a redirected backup source. Backups are
0700, snapshot files 0600, exclusive creation, synced before reset. Leave partial
private backup evidence on failure rather than deleting recovery material.

State backup copies original bytes (even an obsolete state layout); it is not a
migration or a read-only projection that accidentally saves over old ownership.
The deliberate new-login state reset happens only after the marker/instance/
monitor/scratchpad/core guards. Marker schema does not change.

The 4 MiB core transport bound from R2 applies; native/lock waits and the known
CLOSE-WAIT-001 handler remain unchanged. If failed cannot be persisted after an
error, report both failures; an already-published initializing marker still
blocks an ordinary retry. No cross-process/core/native atomic transaction is
claimed, and external clients can still race outside the common desktop lock.

## Pure administration ABI — protocol 1

`agora-desktop-admin` reads JSON stdin and emits one JSON value; no HOME/runtime
lookup, native/core calls, file writes or lock acquisition. Capabilities needs no
stdin, and `--version` is side-effect free. Other inputs are bounded at 4 MiB.

| Operation | Input | Output |
| --- | --- | --- |
| capabilities | none | version 1, runtime_version, core_protocol 3, desktop_schema 3, marker_schema 1, operation names |
| project-state | `{raw,existing_ids}` | validated v3 projection; existing_ids must be unique ordinary IDs |
| validate-state | `{state}` | original validated JSON, without writing/repairing it |
| defer-marker | `{instance,previous}` | `{changed,marker}`: same valid instance preserves its phase/extra fields exactly; missing/different instance proposes schema-1 deferred |

A failed/initializing same-instance marker is never hidden by installer defer.
Python installers retain the outer flock, read their files/native snapshot,
request these pure transformations and publish the returned values themselves.
This removes runtime imports without invoking a reset while already holding the
lock. No unsafe generic already-locked flag is introduced.

**Actual existing installers still select Python until R8.** R3 supplies and
validates the admin ABI and a private temporary ELF-cohort/admin flow; it does
not silently rewire the production configure/navigation/startup installers.

## Evidence and commands

```sh
bash runtime/check.sh
```

- **41 Rust tests total**: previous 33 plus marker shape/phases, same-instance
  preservation, signature bounds, pure admin validation, retryable reads vs
  nontransport failure and exhausted availability budget with virtual/no sleep.
- **23 real-CLI / frozen Python startup scenarios**: first/repeated/new login,
  deferred/failed/initializing markers, compositor/monitor/scoped guards, global
  hide, read retries, permanent error, lost stop/no replay, focus failure/unconfirmed
  focus, concurrent logical creation, bad marker/signature, first-failure recovery
  bar, bar-after-ready and fresh native target race. Whole results, events,
  marker, ownership and archive contents are compared, not just exit status.
- **11 R3 CLI/admin tests**: side-effect-free version/capabilities, pure transforms
  with no HOME/PATH tools, invalid inputs, helper called under a private Python
  flock without deadlock, same failed marker preserved, two competing real Rust
  initializers serialized to one generation/one fake bar, private backups/raw-byte
  preservation, lost stop then blocked retry, symlink marker refusal and temporary
  four-ELF cohort installation with Python admin defer then simulated next login.
  Fake bar asserts the lock is released and observes ready/failed only at exec.
- **Real installed protocol-v3 core in a private HOME/socket**: initial old project
  and Neutral sessions forgotten, new Neutral-1/fresh UUID; same-login repeated
  startup preserves a subsequently user-created logical session and metadata;
  next compositor resets again without inherited UUID owners. Normal windows
  remain unchanged/unowned, two archives and two fake bar launches verified.
- Existing Python **22 startup cases**, temporary startup installer and fake Lua
  hook registration regressions pass. Timeout-budget and real-concurrency tests
  complement differential scenarios rather than claiming every old test maps
  one-to-one to a wire case. R1/R2 suites remain required by check.sh.

Every daemon in these tests is on a private socket and terminated/reaped in
finally. Quickshell/logger/hyprctl are strict private fakes. No actual app/model,
window/session mutation, notification bus or personal profile is used.

R1–R3 runtime ELF cohort is ready for further R8 installation work, **not yet
installed**. User-controlled next connection or approved QML reload/history reset
is still a deployment decision, not inferred from implementing R3.
