# Runtime migration — R0 contracts and reference baseline

Status: R0 preparation completed on 2026-11-19. **No production Rust command,
installer or installed runtime has been replaced.** R1–R8 remain implementation
and deployment work. This directory contains development-only evidence, not a
second production runtime. Python is still the installed implementation.

## 1. Scope and reproducible identity

Seven Python files and the repository's non-personal thumbnail mask are frozen
under `oracles/`, preserving their source-relative layout. `oracles/manifest.json`
records SHA-256 for all eight files and the source repository HEAD. The hashes,
not HEAD alone, identify this uncommitted-worktree baseline. The source includes
the guarded SUPER+Q behavior and the known `closed()` polling defect. Never run
the startup/media oracles against the real desktop/project: use the isolated
harness, which prohibits unmocked external processes.

`fixtures.json` contains only synthetic session UUIDs, workspace addresses, a
startup marker and clip metadata. `test_baseline.py` verifies eight smoke
contracts, including source hashes, read-only snapshot/status, startup marker,
notification literal arguments, Pi routing/tagging, raster-mask metadata and
FilmCraft early validation/signature. These are seeds for parity tests, **not a
claim of full media-pipeline or Rust parity**. R6/R7 must add complete failure and
end-to-end synthetic scenarios.

## 2. CLI / observable contract inventory

All command arguments are literal argv; never evaluate desktop Exec or user text
as shell code. The existing launch-terminal wrapper may invoke a terminal as
before; it is not permission to reinterpret arbitrary argument contents.

### R1: workspace-columns.py

- Current installed path: `~/.config/hypr/Scripts/workspace-columns.py`.
- Commands: `cycle`, `create-empty`, `isolate-or-previous`, `move-next`, `cleanup`,
  `snapshot`, `migrate`, `closed ID`, `focus-workspace ID`. ID is decimal digits;
  ordinary allocation is bounded by 2147483646; `next_id` may reach limit + 1.
- `snapshot` prints JSON `{active_workspace_id, workspaces:[{id,name}]}` with local
  display numbers, not renamed native IDs. Other successful commands are silent.
  Usage/failures return nonzero (currently 1); diagnostics use stderr. Exact
  Python traceback text is not a compatibility requirement.
- Environment: `XDG_RUNTIME_DIR` (legacy fallback `/tmp`), HOME/PATH for native
  calls. Preserve the fallback until a separately reviewed hardening decision.
- State: `<runtime>/hyprland/workspace-columns.json` v3; legacy v2 projection is
  metadata-only. `order`, `owners`, `preferred`, monotone `next_id`; obsolete
  `origins` discarded on write. Stable separate `workspace-columns.lock`,
  blocking exclusive flock. Snapshot still creates/opens runtime/lock, but does
  not save/reinitialize metadata or dispatch. Temp + file fsync + replace;
  current code does not fsync the containing directory.
- External `hyprctl` queries/eval/dispatch have **no current deadline**. Native
  output starting with `error` also fails even on a zero process exit.
- Effects: navigation, same-owner transfers, hide-first scratchpads, guarded fresh
  allocation; metadata cleanup never stops logical sessions. `closed()` may
  sleep 40 × 50 ms under the shared lock; see the separate issue below.

### R2: session-desktop

- CLI: `start --neutral`, `start --project NAME`, `switch UUID`, `deactivate`,
  `stop UUID`, `status`, `close [WORKSPACE_ID]`. Successful actions print one JSON
  reply; close reports `closed_window_requested`, stop reply or `{noop:true}`.
- Environment: `SESSION_MANAGER_BIN` overrides default `~/.local/bin/session-manager`;
  `SESSION_COLUMNS_SCRIPT` currently selects a **Python module**, not a generic
  process runner. This variable is test/import plumbing and must not be silently
  treated as a Rust executable override. R1/R2 should share library code instead;
  retain explicit native-tool/fake-process injection in the future test harness.
- Core calls: `session-manager --json session ...`, timeout 35 s. Invalid JSON,
  nonzero status or invalid acknowledgement fails; no automatic retry of mutating
  requests. `hyprctl`/shared flock currently unbounded as in R1.
- `status`: v2/v3 owner projection, focused-monitor selection, scoped-scratchpad
  consistency, UUID existence and logical/native agreement; adds
  `displayed_context` / `context_confirmed`. No metadata save or dispatch. It can
  create/open the runtime directory/lock; do not promise zero filesystem touches.
- Start/select/stop/close retain the single-monitor mutation policy. Menu stop
  refuses the last session and normal/scoped windows; active stop switches and
  confirms the next opening-order survivor before deletion and checks windows
  again. Deactivate and direct core stop remain distinct.
- Close retains keypress workspace ID and logical owner; only the mapped visible
  active address in the correct workspace/special can close, guarded within the
  same native Lua evaluation. Empty workspace != empty session. No visible
  target on unowned desktop is no-op. Uncertain changes are not replayed.

### R3: session-startup

- No CLI arguments; only the `hyprland.start` hook should execute it. It eventually
  execs `quickshell`; repeated ready/deferred same-instance calls return 0 without
  another bar. Incomplete same-instance attempt returns 1 without retry/bar.
  First-attempt failure marks/logs failure, then still exposes the bar for manual
  recovery. Preserve these differences, not simply "error => exit".
- `HYPRLAND_INSTANCE_SIGNATURE` required, nonempty, <=512 chars. Runtime/lock R1;
  marker `session-startup.json` v1 phases initializing/failed/ready/deferred.
  Symlinked marker refused. Same-instance config/core/shell reload does no reset.
- Startup wait: approximately 10 s budget, 2 s per core probe, 100 ms interval;
  an in-flight final probe can extend the budget. Mutation requests use 35 s;
  logger has 2 s. Native reads/flock currently unbounded.
- A new compositor may intentionally stop previous logical instances through the
  core API (exception to UI last-session/window guards), archive/reset ownership,
  then create and confirm only Neutral-1 on a fresh workspace. No app restoration,
  window adoption or window moves. Scoped scratchpad windows/unknown compositor
  or multiple monitors refuse initialization. Preserve failure marker/no replay.

### R4: agora-notify

- `capture`: validated inherited `AGORA_NOTIFICATION_CONTEXT` wins, including a
  deliberately supplied global; invalid inherited value fails rather than
  silently recapturing. Otherwise execute absolute `session-desktop status`
  with 35 s timeout and require confirmed, consistent displayed context.
- Context values: `global`, legacy unowned `neutral`, `session:<lowercase canonical
  UUID>`. UUID Neutral instance is not legacy `neutral`. Capture prints one line.
- `send [--context VALUE | --global] [-u low|normal|critical] [-a NAME]
  [-t INTEGER] [-r UINT32] SUMMARY [BODY]`; defaults normal, `Agora scripts`,
  empty body. Explicit context/global > inherited > global; no late capture.
- Invoke `notify-send --hint string:x-agora-context:... ... -- SUMMARY BODY`,
  timeout 10 s. Replacement ID must fit u32; expiration is currently a signed
  integer, not restricted to positive values. Success 0, operational failure 1,
  argparse syntax failure 2; no new notification server/history.
- Actual outer budgets matter: OBS capture 2 s, Pi extension capture 2 s/send 3 s,
  Pi launcher capture 2 s. Do not assume the inner 35/10 s will always be reached.

### R5: session-pi

- No args: public core `session list`, optionally `project list` (35 s each), then
  active project directory or explicit Agora root for Neutral/unowned. Missing
  active session/project/daemon is error, not neutral fallback.
- `--agora`: explicit root launch without core routing query. Config is
  `${XDG_CONFIG_HOME:-$HOME/.config}/agora-workflow/config.toml`, absolute
  `agora_root` existing directory required; final working-directory symlink
  refused. Python `tomllib` syntax is TOML 1.0. No implicit path/AGENTS/Yazi.
- New launch strips stale inherited notification tag, captures fresh context
  (2 s), checks against routed owner except `--agora`; inconsistency/unavailability
  conservatively chooses global without blocking an otherwise valid launch.
- Absolute terminal helper receives `[directory, env,
  AGORA_NOTIFICATION_CONTEXT=VALUE, pi]`, same tag in env. Terminal helper wait
  currently unbounded. No response JSON; child IO inherited, success 0/failure 1.

### R6: photocraft-thumbnail

- `DIRECTORY [--top EXACT_FILENAME]`, `~` expansion and directory resolution;
  exactly two supported regular non-symlink PNG/JPEG/WebP/TIFF/BMP image files.
  Output `miniature.pcraft`, refuse preexisting file or symlink before work and
  concurrently created target at publication. Argparse syntax failure 2,
  controlled refusal 1; human progress/success stdout, errors stderr.
- `ffprobe`, FFmpeg, `photocraft-cli` via PATH, **no current subprocess deadlines**.
  Validate width >=1920, exact 16:10 and divisible by 16, center crop integer
  16:9 then scale 1920×1080. Central 32×32 gray mean selects darker image only
  with gap >=15 and darker <=0.75×lighter; otherwise require explicit `--top`.
- CLI creates two layers; archive code copies the exact repository mask into
  top layer, validates format/size/layers, 40 unique tile coordinates and hex
  hash-name syntax, copies matching tile bytes/rejects collisions. This is not
  a demonstrated cryptographic validation of compressed tile payloads.
- Temp directory on target filesystem; check final CLI info/bounds/mask; hardlink
  publication gives no-overwrite. Mask asset adjacent to installed executable.
  ZIP serialization bytes need not match, mask/tile/document semantics must.

### R7: filmcraft-patch-desktop-audio

- `RECORDING PROJECT`, resolved existing paths in the same directory. New closed
  project is a **caller precondition**, not currently verified against an open
  GUI document or an interprocess project lock. Do not claim otherwise.
- `ffprobe`/FFmpeg/`filmcraft-cli` via PATH, no current subprocess deadlines.
  Exactly two stereo streams and aligned initial Audio 1..4 structure required.
  Preserve cuts/video/mic tracks, sourceIn, links, relative WAV path; desktop
  stream is `0:a:1`, not channel 1. Restore linked-selection setting after batch.
- Exact Python Fraction timing: fps num/den, ticks/frame and sourceOut conversion.
  Extract PCM s16le with PTS offset materialized via `aresample=async=1:first_pts=0`;
  shortage >1/5 s refused; smaller shortage padded to required end + one frame
  and validated strictly longer. Formatting to nine fractional seconds occurs
  only at the FFmpeg `-t` boundary.
- Existing `<recording_stem>_bureau.wav` refused initially. WAV is renamed into
  place **before** project operations; project is committed by later replace.
  Cleanup removes owned temporaries/WAV on failure. These are not a two-file
  atomic transaction; initial exists check followed by replace is not a robust
  concurrent no-clobber guarantee. R7 must review race/failure hardening as an
  explicit change, not call the old script perfectly crash/concurrency safe.
- Human stdout/stderr, handled validation/runtime failure 1 (no argparse help);
  source media/project contents are never fixtures in this audit.

## 3. Caller / import graph and cutover gates

`consumers.json` is the reproducible literal-reference scan of 43 repository
files. Regenerate with `python3 tools/runtime-migration/scan_consumers.py`; scan
output deliberately excludes this frozen tree. Dynamic imports were separately
reviewed in the source, including the installed extensionless fallback:

```text
session-desktop.py -> SESSION_COLUMNS_SCRIPT or installed workspace-columns.py
session-startup.py -> sibling session-desktop.py OR installed session-desktop
                  -> that module's columns
install_workspace_navigation.py -> controller source; startup source on full apply
install_session_startup.py -> navigation installer; startup source
```

- `hypr/files/keybinds.lua`: workspace commands, Q with frozen ID, session-pi.
  `hyprland.lua`: close/active/removed hooks. `startup.lua`: session-startup/bar.
- **Quickshell `shell.qml` explicitly runs `python3 ...workspace-columns.py` for
  snapshot and focus-workspace.** Replacing that file with ELF alone cannot
  work. Changing the watched QML/activation requires separate user approval of
  bar reload/RAM-history loss; movement-only cannot silently complete R1–R3.
- `SessionService.qml`: stable absolute `session-desktop` process JSON interface;
  menus/attention depend on its output and confirmation semantics.
- `configure_session_manager.sh`, `install_desktop_integration.sh`, navigation
  coordinator and startup installer must stop copying/importing old Python.
  `configs/pi/session-notifications/install.py` separately reinstalls notify/Pi
  sources today; update it during R4/R5 or later setup would undo the port.
- OBS Lua captures once; OBS shell/pre-edit forward that tag; Pi TS extension
  captures at start and explicitly sends at settlement. `session-pi.desktop`
  and project overrides use stable launcher name. Never rewrite personal entries.
- `scripts/install_scripts.sh` delegates to both media installers; pre-edit calls
  `filmcraft-patch-desktop-audio` before opening the generated project. PhotoCraft
  is an independent helper. Future full configuration must not resurrect Python.
- Tests importing functions: controller/navigation tests, desktop/status/stop/
  close/startup/Pi, `test-neutral-v3.py`, and the desktop-status oracle in
  `test-app-usage.py`. Convert acceptance coverage to executable injection/
  scripted fake processes and Rust unit tests; retaining Python tests is fine,
  exercising only the frozen implementation is not Rust acceptance.

## 4. Retained architecture and locking decision

For R1 onward, use a **new independent** `runtime/` Cargo workspace, not the core
repo and not a refactor of the deployed application launcher:

```text
runtime/
  Cargo.toml, Cargo.lock, rust-toolchain.toml
  desktop-tools/         # shared library + six thin binary entries
  photocraft-thumbnail/  # media dependencies only here
  filmcraft-desktop-audio/
```

Desktop library modules: core protocol DTO/client, native queries/guarded Lua,
workspace state/pure projection, lock/atomic IO, session actions/startup,
notification context, workflow config/process helpers. Entry points:
`workspace-controller`, `session-desktop`, `session-startup`, `agora-notify`,
`session-pi`, `agora-desktop-admin`. Keep five existing public command names;
workspace gets a canonical non-`.py` command. Media installed names unchanged.
No daemon, registry of projects, core patch or new persistent schema.

R1/R2/R3 mutations and consistent reads own the existing single workspace lock
once at the outer boundary. Inner library functions require a borrowed locked
state/token, never spawn another lock-taking desktop CLI. Notification capture
may call public desktop status only when it holds no desktop lock.

Python installers remain allowed. Replace their runtime imports with these
**pure**, versioned admin stdin/stdout JSON operations (to implement in R1–R3):

- `capabilities`: compiled version/schema/operation support, no lock/state read.
- `project-state`: input `{raw, existing_ids}`, output validated projected v3.
- `validate-state`: validate a supplied state without repairing/writing it.
- `defer-marker`: input `{instance, previous}`, output `{changed, marker}`;
  preserve same-instance phase, otherwise propose v1 deferred. Never initialize.

These admin operations acquire **no lock**, read/write **no files** and call no
external process; a Python installer owns the lock, captures native/JSON inputs,
requests pure transformations and performs its existing atomic saves. Do not
introduce an unsafe generic `--already-locked` bypass or nested subprocess lock.
Unknown admin versions fail before publication. Operations are design contracts,
not implemented by the R0 dependency probe.

Cutover policy: stage all compatible desktop files/builds, validate callers and
rollback in temporary HOME, then coordinate the first activation with the QML
approval gate and shared lock. Do not overwrite the Python module pathname with
an ELF while any Python importer/interpreter caller still uses it. A later
executable-only compatibility alias may remain for old native exec callers;
it is **not** a solution for `python3 path`/importlib. Interrupted multi-file
conversion must fail closed or restore an explicitly selected coherent cohort;
R8 must prove this. No claim of global atomic activation from per-file renames.

## 5. Reuse and dependency feasibility

Reviewed `app-launcher/src/{context,process,fs}.rs` and its manifest. Reuse the
patterns (typed v3 source, confirmed owner validation, bounded direct-child IO,
fd-safe IO), **not a new dependency on the launcher binary/crate or its Gio,
history, Git and desktop-entry policy**. Its context bracketing is stricter than
legacy desktop status and includes entry/project identity; these contracts are
not interchangeable. Keep shared synthetic owner/source cases consistent first;
extract a common small library later only with dedicated regression coverage.

Rust **1.96.1**, edition 2024. `dependency-probe/Cargo.toml`, toolchain file and
full `Cargo.lock` lock the R0 feasibility build; carry reviewed versions and
checksums into the future workspace, reviewing any additional dependency/feature
rather than claiming this probe is the final production dependency graph.

| Dependency | Exact version | Purpose |
| --- | --- | --- |
| libc | 0.2.189 | Linux locks/fd flags, matching existing launcher |
| serde | 1.0.229 | typed contracts |
| serde_json | 1.0.151 | preserve unknown media JSON/order/large integer precision |
| toml | 0.8.23, parse only | TOML 1.0 workflow config, not newly accepted TOML 1.1 |
| zip | 9.7.3, stored/deflate via pure Rust zlib-rs | archive feasibility, no default codec/crypto bundle |
| num-bigint / num-rational / num-traits | 0.4.6 / 0.4.2 / 0.2.19 | exact arbitrary-precision timing |
| hound | 3.5.1 | PCM WAV frame count/sample rate |

Crates were fetched into the development cache, then tests/strict Clippy/release
built **offline and locked**. Four API tests prove JSON large integer roundtrip,
TOML config parsing, ZIP metadata roundtrip and rational/PCM timing. No Gio/GLib
or new system codec dependency for this probe. ZIP codecs required by actual CLI
synthetic output still need checking in R6; do not silently narrow accepted
archives to the probe subset. No deployment or system-wide package install.

The current runtime has unbounded native/lock/media waits. A future timeout or
output-limit policy must be explicit, tested and reviewed per command; never
apply the launcher's 30 s launch budget blindly to long media processing, kill
a child process group containing user apps or retry a possibly committed action.

## 6. Measurements and separate close-wait issue

See `baseline-results.json` and `benchmark.py`. Recorded Python 3.14.7, warm
local processes, 31 samples for short operations, wall-clock median/p95:

| Measurement | Median ms | p95 ms |
| --- | ---: | ---: |
| Python `-c pass` process | 17.501 | 18.991 |
| real hyprctl + read-only activeworkspace IPC | 5.120 | 7.771 |
| real core CLI + read-only session list IPC | 5.080 | 5.281 |
| in-process snapshot with fake native responses | 0.034 | 0.068 |
| in-process create_empty with fake native responses / temp filesystem | 0.216 | 0.475 |

Snapshot: five fake native queries. `create_empty` function: nine fake queries +
one fake guarded eval; this **excludes** the CLI's module startup/load/hide-first
entry overhead. Do not sum medians into an end-to-end user latency prediction.
Real probes capture process output only transiently to avoid Python wait(timeout)
polling-backoff measurement bias, then discard it; no identifiers/content in the
record. Optional live mode runs only `activeworkspace` and core `session list`.

A remaining fake window in the just-closed workspace causes 40 polls and exactly
2000 ms requested sleep; one real-sleep fixture measured **2007.167 ms**. A
separate private 75 ms lock holder delayed acquisition 75.463 ms (one sample,
not a distribution). `closed()` runs inside the shared lock, so unrelated queued
navigation/status/close work can inherit the wait. Rust won't remove that loop.

Track [CLOSE-WAIT-001](closed-wait.md) separately. Functional reference is the
frozen 2026-11-19 source, including the defect; the 2 s delay is **not** an
acceptance invariant to preserve permanently. Correct before R1 only as a
separate reviewed change with updated reference, or after parity in a separate
fix. R0 reproduces/documents it and does not silently implement the fix.

## 7. Commands / evidence and next gates

From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/runtime-migration/test_baseline.py
python3 tools/runtime-migration/scan_consumers.py
python3 tools/runtime-migration/benchmark.py                   # fully synthetic except Python process startup
python3 tools/runtime-migration/benchmark.py --live-readonly   # optional read-only IPC, no recorded payloads
cd tools/runtime-migration/dependency-probe
cargo +1.96.1 fetch --locked                 # one-time dependency preparation
cargo +1.96.1 fmt --check
cargo +1.96.1 test --offline --locked
cargo +1.96.1 clippy --offline --locked --all-targets -- -D warnings
cargo +1.96.1 build --offline --locked --release
```

Per-lot executable parity suites (Python harnesses remain valid tooling):

| Lot | Commands from repository root |
| --- | --- |
| R1 | `python3 configs/hypr/tests/workspace_columns_test.py`; `navigation_scratchpad_test.py` and `scratchpad_session_test.py` in that directory |
| R2 | `python3 configs/session-manager/test-session-{desktop,status,stop,close}.py` (run each file, not literal braces in Python) |
| R3 | `python3 configs/session-manager/test-session-startup.py`; `test-startup-install.py`; `test-neutral-v3.py` |
| R4 | `python3 configs/session-manager/test-agora-notify.py`; `node configs/session-manager/test-notification-policy.js`; `python3 configs/session-manager/test-notification-store.py`; Pi extension `test.mjs` |
| R5 | `python3 configs/session-manager/test-session-pi.py`; `test-agora-workflow-config.py`; `test-neutral-v3.py` |
| R6 | `bash scripts/photocraft-thumbnail/test_photocraft-thumbnail.sh` (synthetic images, real headless CLI, no GUI); add failure fixtures |
| R7 | no dedicated existing full suite found; R0 signature/early-validation seeds only; build new fake-CLI and synthetic-audio acceptance suite |
| R8 | navigation/startup/Pi notification/media installer tests in private HOME, plus source-versus-installed verification without executing real actions |

R0 reran controller **36**, stop **18**, close **15**, startup **22**, status/Pi/
notification wrapper regressions and actual private-core integration; all pass.
These existing tests still target Python: **not Rust parity evidence**. The new
eight frozen smoke tests and four dependency tests pass as well. No real media
pipeline/GUI, terminal, model, session mutation, window operation, real
notification, config reload or shell restart was executed for R0.

R0 accepts the architecture as an implementation design with dependency/API
feasibility demonstrated, not user approval for later QML reload or a claim that
R1–R8 are complete. No live installation script is appropriate for development
fixtures/documentation; runtime deployment is explicitly deferred to R8.
