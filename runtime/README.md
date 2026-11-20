# Agora runtime — R1–R7 installed

R1, [R2 desktop/SUPER+Q](R2-desktop.md) and [R3 startup/admin](R3-startup.md)
implemented on 2026-11-19;
initially tested in isolation; [R8 activated the coherent native cohort](R8-deployment.md)
after explicit QML/history-reset approval on 2026-11-20. Public controller/desktop/startup/admin
are now native managed links. No QML/hook/shortcut changes are
part of R1. [R4 notifications](R4-notify.md) is independently implemented and
installed as the Rust helper only; both Pi and normal configuration installers
preserve that migration. [R5 Pi launcher](R5-pi.md) is also independently installed;
routing and capture origin are native Rust with literal terminal env argv. No live core daemon, desktop runtime state or personal
project data was changed. [R6 thumbnail](R6-thumbnail.md) is an independently
installed media member; generated-fixture headless CLI tests never touch the active
document or personal images. [R7 audio](R7-filmcraft.md) is also independently
installed: exact rational timing and explicit safe partial-publication states,
never a live-project/recording fixture.

## Build and test

Rust 1.96.1 / edition 2024, exact libc/serde/serde_json/toml pins and workspace
Cargo.lock. R0's reviewed dependencies are reused. The desktop member owns desktop
commands; separate thumbnail and FilmCraft-audio members own their ZIP/rational/WAV
dependencies, without Gio or a neighbouring core checkout. From the repository root:

```sh
bash runtime/check.sh
PYTHONDONTWRITEBYTECODE=1 python3 runtime/tests/benchmark_workspace.py
runtime/target/release/workspace-controller --version
```

`check.sh` runs fmt, **87 Rust tests** total (57 desktop, 14 thumbnail, 16 audio), strict Clippy, locked offline release
build, R1 **61 differential scenarios / 19 CLI tests**, R2 **52 scenarios / 12 CLI
tests**, R3 **23 startup scenarios / 11 CLI-admin tests**, and private-core scenarios
for R2 and R3. R4 adds **75 CLI differential cases**, a frozen-context switch
case, wrapper/installer tests, Pi's **11 extension cases**, policy regression and
the actual Quickshell/Notify lifecycle on a private D-Bus. R5 adds **60 differential
CLI cases**, strict-v3/resource refusals, private actual core/R4/R2 with stub terminal
server reuse, standalone/Pi installer and workflow-config tests. See [R5 contracts
and deployment](R5-pi.md). R6 adds **73 differential scenarios**, five ZIP codecs,
private installer/restore tests and real headless FFmpeg/PhotoCraft on generated
images. See [R6 contracts, explicit differences and separate measurements](R6-thumbnail.md).
R8 adds private cohort first-handoff/partial-failure/explicit-restore tests, installed
new/same-login acceptance, reduced updates and R4/R5 pinned-hash restore. See
[R8 deployment and remaining consent/acceptance](R8-deployment.md).
R7 adds **57 differential scenarios**, private syscall faults/races and harness
timeouts, native generated-media/auto-editor/headless FilmCraft parity, installer/
restore and CLI guards. [R7 contract, recovery table and deployment](R7-filmcraft.md). The private core tests
require the installed protocol-v3 binary, never the live service. See [R2 evidence](R2-desktop.md) and [R3 evidence](R3-startup.md). All native actions in these suites use memory adapters,
private HOME/runtime and fake hyprctl; generated Lua guards also execute against
a fake hl table. The Python tests are test harnesses, never runtime dependencies
of the binary. Build artifacts stay in ignored `runtime/target/`.

The direct CLI accepts:
`cycle|create-empty|isolate-or-previous|move-next|cleanup|snapshot|migrate`,
`closed ID`, `focus-workspace ID`, plus a side-effect-free `--version`.
**Do not run mutating commands against the live desktop as a development test.**
The binary currently resolves native `hyprctl` from PATH just like Python;
tests replace it with strict fixtures.

## Contextual file manager

[session-files](session-files.md) adds SUPER+E project-or-HOME routing through the
standard opener, with no menu/MIME change. It is included as a fifth managed native
entry; original four-command generations and backups remain compatible. Eight new
unit tests bring the workspace total to 95; CLI/private-core/expansion-restore tests
are included in `check.sh`.

## Library boundary

- `files.rs` / `bin/session-files.rs`: confirmed project root or HOME, readonly
  bounded probes, final context/directory recheck, one literal standard opener.
  Shared catalogue lookup/transport resides in `core.rs`; menu entries unchanged.
- `pi.rs` / `bin/session-pi.rs`: public-v3 routing, native TOML configuration,
  fresh 2 s capture with stale inheritance removed, literal env argv, no core
  mutation/stats. `install_pi.py --apply` deploys the launcher only.

- `state.rs`: typed desktop v3, pure legacy v2 projection, validation, unknown
  v3 extension-field preservation, retired origins, opaque IDs/order/owners.
- `native.rs`: direct argv native calls, zero-exit error-text handling and Lua
  builders. Fresh focus/move guard and dispatch are one eval, no animation change.
- `storage.rs`: owning `LockedStore`, existing stable flock once at the CLI
  boundary; directory-relative exclusive temporaries, file fsync/rename and
  directory fsync, private state permissions. Inner functions never relock.
- `workspace.rs`: generic Controller over Native/Store adapters. Runtime uses
  the owning locked file store; memory stores are injectable test adapters.
  R2 uses this controller/library without subprocess lock recursion; R3 can reuse it.
- `bin/workspace-controller.rs`: parse before any runtime/native access, acquire
  lock, run policy, print snapshot JSON only. No core API or Python invocation.

All reference commands and semantics are implemented: stable monotone allocation,
cleanup without logical-session stop, same-owner ordering, Tab create/return,
Shift isolation/previous/no-wrap, existing-next/wrap/no-allocation, current empty
retention, other-monitor visible-empty retention, hide-first focused scratchpad,
native race refusal and provisional-owner removal on uncertain fresh focus/move.
An uncertain result is never replayed or repaired by moving/adopting windows.

Snapshot never publishes/initializes metadata, including legacy state. As in
Python it may create/open the runtime directory and lock file. Unowned native
workspaces discovered during state load stay unowned, not adopted by the active
UUID. The legacy desktop sentinel remains distinct from any real Neutral UUID.

## Compatibility and explicit hardening

For valid documented metadata and native responses, differential tests compare
state, saved state, native worlds/events, snapshot and failures. The 36 original
controller behavior areas are represented, with added malformed state,
read/write failure, uncertain move, command/scratchpad and guard cases. Original
Python controller/navigation/routing regressions also pass; their success alone
is not used as evidence for Rust.

These narrow fail-closed filesystem/shape differences are intentional and
tested, not a schema migration:

- Refuse symlink/nonregular/multiply-linked/foreign state or lock files, using
  O_NOFOLLOW/O_NONBLOCK and fd metadata so FIFO input cannot hang. Reject a
  symlinked final runtime directory. No claim of full ancestor-path sandboxing.
- Enforce integer schema/IDs and documented legacy row 1/2; malformed float
  versions, overflow or invalid row shapes are refused instead of accepting
  Python equality/coercion accidents or panicking. CLI IDs are ASCII decimal
  within i64; out-of-range arguments fail rather than silently doing nothing.
- Temp state remains 0600; existing lock file inode/permissions are not replaced.
  Directory fsync is added after publication. Post-rename fsync failure reports
  uncertain persistence, without rollback/retry. A private test seam injects a
  failure after temporary write/fsync and before rename: previous JSON and
  unrelated temporaries remain intact.
- Native waits, lock waits and the historical 40 × 50 ms closed handler are
  **not given new deadlines**. Simulated native timeout/error replies fail
  without replay. Timeout policy and CLOSE-WAIT-001 remain separate changes.

The lock is interoperable with Python flock: an actual CLI process remains
blocked on a private Python-held lock, does no native IO before acquisition and
retains the inode across save. Interrupted-before-publication, corruption,
symlink/hardlink/FIFO, unknown schema and bad native JSON/error streams are tested.
No production environment variable or public CLI flag enables injected faults.

## Measurements (same R0 synthetic world)

See `tests/benchmark-results.json`. Warm wall times, 31 samples, median/p95 ms:

| Operation | Median | p95 |
| --- | ---: | ---: |
| Python process (-c pass) | 15.664 | 18.664 |
| Rust process (--version) | 0.683 | 1.118 |
| Python snapshot CLI, identical fake native helper | 199.999 | 218.452 |
| Rust snapshot CLI, identical fake native helper | 153.430 | 164.122 |

The fake hyprctl is a Python executable launched for each native request, so its
startup/JSON/IO dominates both snapshot totals. These are **not real Hyprland
latency or a promised user-visible speedup**. R0 measured real read-only native
and core command cost separately; those samples are not summed into estimates.
The same R0 two-owner create fixture produces active ID 3, order [1,3,2] and one
guarded native dispatch in Rust. Allocation outcomes are compared, not a
misleading memory-only Rust time against Python filesystem fsync time.

The unfixed closed handler still retains its reference polling/sleep semantics;
the parity fixture records virtual sleeps rather than burning two seconds per
test. A future reviewed CLOSE-WAIT-001 fix must update that expectation explicitly,
not demand the defect be permanent.

## R8 activated with separate consent — user acceptance still open

`install_desktop.py` now owns coherent generation staging, first-handoff journal,
managed entry points, pure admin validation/defer and explicit restore. Normal
installers/callers are converted and privately tested; no production route copies
Python over the ELF. QML/Lua source uses the native workspace-controller entry.

After separate explicit consent, the native generation and matching Lua/QML were
activated and known Quickshell restarted with its authorized RAM-history reset.
Immediate coordinator snapshots matched; current native context is confirmed.
Subsequent observed state changes are recorded without assuming their origin.
R4–R7 remain native; R4/R5 restore-capable installer updates applied validated ELF
refreshes without capture/send/reload. [Exact state, backup paths, recovery gates
and unfinished user acceptance](R8-deployment.md). No login reset, application
restore, window/session mutation or core restart is used to validate deployment.
