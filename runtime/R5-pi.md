# R5 — Rust Pi launcher, installed independently

Implemented, validated and installed on 2026-11-19. R1–R3 remain development-only;
R4 remains installed. R5 changes only the Pi launcher, not Pi itself, its settings,
models, global extension, desktop/session state or graphical hooks.

## Contract

The public command remains `~/.local/bin/session-pi [--agora]`.

- Default: query the public v3 `session-manager --json session list`. Active
  project routes through `--json project list` to that project's current path.
  Active Neutral UUID and no-active session route to explicitly configured
  `agora_root`. They remain different notification origins.
- `--agora` explicitly selects Agora without querying the routing catalogue. Its
  fresh capture may still describe the originating session; cwd is not identity.
- Configuration: `$XDG_CONFIG_HOME/agora-workflow/config.toml`, otherwise
  `$HOME/.config/agora-workflow/config.toml`. Empty XDG uses the default; relative
  XDG fails when config is needed. Read full TOML with pinned native
  `toml = 0.8.23` (parse-only, already probed in R0). No Python parser subprocess.
  Other settings are preserved/ignored, not rewritten.
- Missing/bad config, unavailable daemon/project, invalid v3 replies, relative/
  missing/non-directory/final-symlink cwd fail with exit 1; no invented root,
  Yazi/AGENTS discovery, model selection, stats or core mutation. Project routing
  does not need Agora config. Neutral does not query an unavailable project source.
- Session/project queries retain 35 s per request, literal argv and no retries.
  Reuse R2's bounded direct-child transport, 4 MiB per stdout/stderr stream.
- Remove inherited `AGORA_NOTIFICATION_CONTEXT` from the capture child's
  environment. Invoke absolute `~/.local/bin/agora-notify capture` once, with
  a 2 s deadline. Validate lowercase canonical UUID/global/neutral; require the
  routed UUID or unowned neutral exactly, except explicit `--agora` which accepts
  any valid fresh origin. Missing/failing/timed-out/malformed/UTF-8-invalid or
  inconsistent capture falls back to explicit `global`, never to a guessed UUID.
- Invoke absolute `~/.local/bin/launch-terminal-command DIR env
  AGORA_NOTIFICATION_CONTEXT=VALUE pi`. Set the same environment variable and
  preserve other inherited environment values. No shell evaluation; spaces,
  Unicode, quotes and metacharacters remain literal. The argv prefix survives
  stale environments in reused terminal servers. Terminal stdio is inherited,
  waiting remains unbounded as before, and failure is never retried.

Routing is a snapshot, not a new transaction: an external context change between
routing and capture keeps the planned cwd but yields global on mismatch. Directory
validation does not pin a directory inode across an external terminal launch.
Capture timeout owns/kills/reaps only its direct child, not unrelated descendants.

### Explicit compatibility differences

Reuse typed R2 v3 session/source validation: missing active-id field, duplicate
identities, malformed inactive sessions/sources and malformed project rows fail
closed, rather than silently ignoring them as the older Pi-specific parser could.
Valid v3 replies preserve routing. Like the other new runtime commands, HOME must
be supplied; no passwd-database fallback. New read-only `--version` needs no HOME,
daemon or config. Invalid options still exit 1; diagnostics are useful but not
byte-for-byte Python exception text.

The executable does not implement routing by importing/delegating to Python.
The existing public desktop companion used by R4 capture is still Python on the
live machine until R8; this does not claim the entire process tree is migrated.
No new daemon, registry, project identity, lock or protocol was added.

## Installation

```sh
python3 runtime/install_pi.py          # no-effect plan
python3 runtime/install_pi.py --apply  # launcher only, no model/terminal/reload
```

Pinned Rust 1.96.1, locked/offline build, ELF/version validation, private backup,
atomic replacement at mode 0755, unchanged reinstall no-op. Refuses symlink/
nonregular targets and unsafe backup ancestry. Uses the shared runtime builder
in `install_notify.py`; that installer's standalone apply still changes only
the notification helper. No toolchain installation or automatic rollback.

Both `configure_session_manager.sh` and the targeted Pi notification installer
now deploy validated Rust, never copy `session-pi.py`. The latter updates an
existing launcher, still under its v3 gate, and leaves a missing launcher absent.
Its existing extension/helper scope is otherwise unchanged. A normal setup can
therefore not silently undo R5. Legacy Python remains only for historical tests
and frozen R0 differential references; final cleanup belongs to R8.

Standalone installer applied live, **not** full configuration or the extension
installer. Backup: `~/.local/state/linux-setup/session-pi-upgrades/20261119T182156-32w6xcwr`.
Installed bytes equal the release and version is
`session-pi 0.1.0 (Rust; captured launch origin)`.
Before/after hashes/PIDs verify unchanged core/desktop/startup/notification/app
helpers, logical/desktop state, QML, bindings, Pi extension/settings and personal
project desktop overrides. SUPER+P still calls the same public command; global
entry retains `Exec=session-pi --agora`; project overrides need no rewrite.
No real launch/capture/send/session change/reload was used to test deployment.

## Evidence

`bash runtime/check.sh` includes R1–R4 and:

- **57 Rust tests total**, including seven Pi origin/config/path invariants;
  fmt, strict Clippy and offline locked release pass.
- **60 differential CLI scenarios** against frozen R0 Python: routing/cwd/context,
  explicit Agora, quoted/Unicode paths, invalid config/source/daemon/project,
  capture error/timeout/invalid UTF-8, terminal failure and literal environment.
  Three stricter v3 refusals, missing capture/terminal executables, no-HOME version,
  SUPER+P and global-entry source contracts are checked separately.
- Original import-based Pi tests also invoke the Rust black-box suite, rather than
  testing only the old implementation. Workflow-config tests stay pure Python.
- Actual installed v3 core in private HOME/socket, R4 Rust capture and R2 Rust
  status with fake native tools (also checked with the still-installed Python
  desktop ABI): project, Neutral UUID without project catalogue,
  unowned, explicit Agora and spatial/logical mismatch. A stub terminal really
  executes system `env` against a synthetic `pi` stub with a stale server
  environment, proving argv overrides it. No real Pi/model or personal data.
  Launcher calls preserve core revision, metadata, windows and absence of stats.
- Standalone/notification installers in private HOME: actual validated ELF,
  plan, backup, atomic copy, idempotence, symlink/capability refusal and unchanged
  personal settings/extensions/desktop entries. Normal full configuration tested
  separately by `test-neutral-v3.py`, including installed Rust bytes and untouched
  personal project override; it was not executed against the live desktop.
- Existing 11 Pi extension cases, notification wrappers/policy and actual private
  Quickshell/D-Bus history tests remain green.

Visual acceptance through normal SUPER+P/global/project use is separate.
Existing Pi instances are not restarted/reloaded; new invocations use the launcher
immediately. R6/R7 were subsequently completed; [R8](R8-deployment.md) now supplies
guarded installer `--restore` (legacy backups require an explicit reviewed current
hash). Coordinated live desktop activation and user acceptance remain open.
