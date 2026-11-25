# Session application launcher (Rust)

Downstream Session Manager v3 client. **0.2.1 implements project-local usage history for menu selections only**, on top of the 0.1.0 Python-to-Rust migration baseline. No dependency on the core checkout/internal runtime files; no core API change.

## User behavior

- SUPER+Y / `--youtube`: one eligible project YouTube desktop override, otherwise
  YouTube URI in contextual Firefox via GIO. No arbitrary installed YouTube account
  selection, Rofi or statistics. [Routes, tests and related O/Sleep bindings](../../../runtime/context-shortcuts.md).

- SUPER+Shift+D uses the same expected-workspace protocol after unconditional fresh
  allocation; reads ranking, never records usage. SUPER+Shift+B uses
  `--browser --expected-workspace ID OWNER` (`[expected-browser-v1]`).
  For a declared desktop `new-window` action, invoke it through Gio after normal
  context/entry revalidation; otherwise preserve the selected desktop Exec, including
  project profile wrappers. No injected flags/custom Exec rewrite or window transfer.
  A profile/application can still reject or reuse a window; no retry/repair.
  [Five-shortcut orchestration, deployment and limitations](../../../runtime/new-workspace-launch.md).

- Historical SUPER+Tab (unbound since stage 3; protocol retained for Shift+D):
  after confirmed fresh workspace creation, the controller uses
  `--expected-workspace ID OWNER`. Exact active workspace/owner/no-special checks
  precede Rofi and application acceptance; ranking is read but no usage is recorded.
  No menu on empty-workspace return or scratchpad dismissal.
  [Protocol, deployment/tests and isolation incident](../../../runtime/tab-launcher.md).
- SUPER+D: confirmed contextual catalog, usage-ranked rows in Rofi; filtering preserves order (`-no-sort`). Existing metadata, icons, search keywords and escaped labels remain.
- SUPER+B / `--browser`: resolve exactly `firefox.desktop` in that catalog without a menu, preserving the project override/profile and never falling back to another profile silently.
- Only SUPER+D counts successful GTK/Gio launch acceptance, not window focus, running time or proof of a visible window. SUPER+B / `--browser` bypasses usage reads/writes, lock creation and Git exclusions completely; pre-launch context/profile checks remain. Firefox selected in the menu still counts. Cancel/rejection/timeout is not recorded or replayed.
- Existing aggregate counters are preserved, including any earlier 0.2.0 browser contributions; no retrospective reset/subtraction is attempted.
- SUPER+A, SUPER+P and third-party launchers are unchanged and do not feed these counters.

## Storage and ranking

| Scope | Data file |
|---|---|
| Project, shared by its sessions | `PROJECT/.session-manager/app-usage.json` |
| Any real Neutral instance | `${XDG_STATE_HOME:-$HOME/.local/state}/session-app-launcher/neutral.json` |
| No active session, confirmed unowned desktop | same directory, `unowned.json` |

The project file moves/copies with the project. Session UUIDs are not storage keys; new login/session recreation never resets history. Global state paths must be absolute, with no redirected/symlinked data ancestors. Unsafe/unwritable data placement disables statistics, not valid launches.

Version-1 closed JSON: `{"version":1,"apps":{"firefox.desktop":{"count":1,"last_used":1795000000,"weight":1.0}}}`. Duplicate keys at every level, unknown fields/versions, invalid IDs/types/numbers and excessive files are rejected, never silently replaced. Counters saturate at u64 maximum; dates are Unix UTC seconds through year 9999; weight is finite/positive and at most min(count, 1,000,000).

Each launch adds one point to the decayed previous weight. Half-life is **7 days**: `weight * 2^(-max(0, now-last_used)/604800)`. Sort by descending score, descending last-used clamped to now, lowercase Unicode display name, then ID. One clock snapshot per menu; no live reordering. Future timestamps receive no recency bonus. With absent/invalid history use deterministic name/ID order.

Read limit **1 MiB**, at most **4096 IDs**. On valid updates only, expire entries older than **180 days**, then evict oldest entries until both count/serialized-size bounds hold, protecting the just-updated ID. Temporarily excluded/uninstalled apps are not listed but retain their history until expiration/eviction. Never clear history on menu cancellation or read.

## Confirmed context and entry integrity

`context.rs` reads the **documented desktop status contract directly in Rust**: core `session list`, `hyprctl -j monitors`, and read-only `${XDG_RUNTIME_DIR}/hyprland/workspace-columns.json` (v3; legacy v2 owner projection supported). This avoids calling the Python `session-desktop status` adapter at runtime. It does not acquire a writer lock, create metadata, focus workspaces or change owner associations. Physical/logical mismatch, unknown context or unavailable transport is an error, never a neutral fallback.

Catalog/project resolution is bracketed by confirmed snapshots of the same revision/context. Always resolve a project even if all its applications are installed entries. Retain canonical path and directory identity/capability while the menu is open. Before launch, revalidate identity, typed source, UUID, current eligibility/origin and effective desktop entry (path, device/inode/mode/size, SHA-256 of bounded contents). A replaced/changed entry or moved/replaced project requires reopening the menu. Revisions may change while the menu is open if the context/selected entry remains unchanged.

After acceptance, revalidate before writing and again after exclusion setup/history-lock contention. If this fails, skip the measure with a warning; the accepted launch still returns success and is never undone/replayed. There is no atomic transaction spanning independent core/native/filesystem actors: changes after the final checks remain possible. This limitation is not disguised as automatic adoption/repair.

## Safe storage and local Git exclusion

`fs.rs` uses Linux directory descriptors, no-follow opens, regular/owned/private file checks, stable separate flock files, a one-second acquisition deadline, bounded read-modify-write, owned O_EXCL temporaries, fsync and atomic rename/directory sync. New data files/locks/temporaries are private; new state directories are mode 0700. Symlinks, hardlinked/nonregular data, read-only files, replaced project directories and invalid JSON are not overwritten. Do not recreate a disappeared project. Failures warn without blocking/replaying an accepted launch; uncertain publication is not retried automatically.

Before any usage lock/data creation in a Git worktree, `git.rs` discovers the enclosing repository (including a parent repo or linked worktree), refuses already-tracked data and resolves the actual `info/exclude`. Add only exact anchored escaped rules for that data/lock and `.app-usage.tmp-*`; preserve existing comments/rules and update idempotently under a separate stable lock. No overlap between Git and history locks, no index/global-config/`.gitignore` mutation, no `git rm --cached`. The same guard applies to global state if it resides inside a worktree. Git calls use literal pathspecs, ignore inherited Git-directory overrides and disable optional index locks/fsmonitor.

Spaces, Unicode and glob-like path characters are supported. LF/CR in a **relative ignore pattern** cannot be represented exactly: warn/disable recording instead of writing an unsafe broad rule. Unwritable/invalid/symlinked exclusion files similarly disable recording. Git exclusions cannot prevent explicit user force-adds or arbitrary noncooperating mutations.

## Build and install

Prerequisites: Rust **1.96.1**, C linker, `pkg-config`, Gio/GLib development libraries (Arch: `glib2` plus normal build tools). Runtime: Gio/GLib, Rofi, GTK/Gio CLI, Hyprland's `hyprctl`, the installed v3 core; Git only when a repository owns the state location. **No Python/PyGObject runtime dependency for this component.** Other setup helpers still use Python.

```sh
cd configs/session-manager/app-launcher
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo build --release --locked
```

Pinned toolchain and Cargo.lock; Gio 0.18.4 / GLib 0.18.5, serde 1.0.229, serde_json 1.0.151, libc 0.2.189, SHA-256 via sha2 0.10.9. Add `--offline` with a prepared cache. Source/dependency locking is not a promise of bit-identical builds across arbitrary system libraries/environments.

```sh
bash configs/session-manager/install_app_launcher.sh --apply
bash configs/session-manager/install_app_launcher.sh --restore /absolute/private/backup/session-app-launcher
```

Same installed command `~/.local/bin/session-app-launcher`, no args / `--browser` / `--expected-workspace ID OWNER` / `--browser --expected-workspace ID OWNER`; `--version` is a read-only health command and does not initialize statistics. Core queries have a 35-second deadline, native queries five seconds, launch helpers 30 seconds, capture bounded to four MiB per stream. Literal GTK/Gio argument vectors only; never shell-evaluate `Exec`. Rofi cancellation/nonzero retains the previous exit-0/no-launch behavior.

The installer verifies the known protocol-3 stack, builds the locked pinned release, saves a private backup under `${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/app-launcher-upgrades/`, and atomically replaces only the executable. Explicit restore saves the version being replaced. No app/menu launch, core/shell restart, session/workspace change, history initialization or real Git exclusion edit is an installation check.

## Validation evidence

- **30 Cargo tests**: schema/duplicates/ranges, score/clock/ties/retention/eviction, pure reads, concurrent increments, final-context rejection, directory identity, fd-safe storage, permissions/symlink/hardlink/FIFO, atomic publication/noreplace, lock/output/time bounds. Format, strict Clippy and locked offline release build pass under 1.96.1.
- `../test-app-usage.py`: **33 executable cases** in owned HOME, covering project/shared/global persistence and move/reopen, ranking/selection, menu-only counting and browser non-mutation in all scopes, cancel/fail, UUID/entry/context/directory changes, post-acceptance failures, unsafe/corrupt/read-only state, symlinks/lock contention, exact Git rules/parent/worktree/special paths, tracked-data/index preservation, concurrent clients and compatibility with the existing legacy-status helper.
- `../test-session-app-launcher.py`: **22 migration regression cases**, retaining the frozen Python oracle for unchanged rows/launch semantics; new context queries, deterministic ranking and `-no-sort` are deliberate differences. Includes localization, literal project paths, missing browser, installed symlink exports and a native run without Python on PATH.
- `../test-neutral-v3.py`: actual private v3 daemon, fake GTK/native tools, neutral browser with an unavailable project source; full configuration installs the Rust binary in a temporary HOME.
- `../test-app-launcher-install.py`: actual offline install/restore in temporary HOME, ELF/private-backup checks and symlink refusal, no real desktop invocation.

`tests/fixtures/legacy-launcher.py` remains a frozen test oracle only. Actual user acceptance of ranking remains manual. Live installation compares read-only core/native/shell snapshots and executable version/bytes; it never seeds personal histories or launches real apps to test the feature.
