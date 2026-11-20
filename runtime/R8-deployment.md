# R8 — Cohort deployment and acceptance gates

Prepared, privately validated and **activated on 2026-11-20 after separate explicit
approval to reload Quickshell and lose its current RAM history**.
R4–R7 are installed; no visual/aural user acceptance is inferred from tests.

## One desktop coordinator

`runtime/install_desktop.py` is the only publication coordinator for controller,
desktop adapter, startup, pure admin and dependent Lua/QML. Python is installer
infrastructure, never an implementation fallback inside these native commands.

- Exact Rust 1.96.1, locked/offline desktop-only build; verify four ELF versions and
  pure admin v1 capabilities/core3/state3/marker1 before publication.
- Stage immutable-by-convention, hash-verified generations under
  `~/.local/libexec/agora-desktop/generations/<content-hash>/`, containing all four
  binaries and matching config templates. Stage has no active pointer, runtime
  metadata, core/compositor call or watched QML write.
- Public `~/.local/bin/{workspace-controller,session-desktop,session-startup,
  agora-desktop-admin}` become exact managed links through a single `current`
  pointer. Subsequent native upgrades switch the four-binary generation with one
  atomic pointer replacement, never overwrite an ELF with Python.
- First handoff from Python still involves multiple filesystem entries: stop only
  the positively identified matching Quickshell after explicit approval, hold the
  existing workspace flock, save evidence/backups/journal, defer the current login
  with the **pure admin subprocess** and publish compatible links/config.
  There is **no global filesystem transaction**. No public startup initialization,
  native focus/move/close, session lifecycle operation or inferred rollback runs.
- Validate existing v3 metadata without rewriting any byte; reject v2/corrupt
  input rather than silently migrate. Admin handles marker proposals without
  lock acquisition or IO: same-login valid phases/extras remain exact, failed
  attempts never get replayed. A new deferred marker prevents same-login reset.
- Live full handoff touches only critical Hyprland hooks/bindings/startup/scratchpad
  plus the versioned seven QML/JS files. Existing monitor/input/visual configuration
  and unknown personal extras are not overwritten. Explicit offline provisioning
  installs the base templates too.
- Snapshot native client/workspace assignments, focused monitors, core list and
  exact metadata before/after under the lock. A mismatch reports uncertainty,
  never repairs/adopts/moves windows. Private backups contain real evidence only
  outside Git. Core daemon/service/unit and project/profile/statistics files are
  outside this coordinator's write set.

### Consent, modes and installer routes

```sh
python3 runtime/install_desktop.py                       # no-effect plan
python3 runtime/install_desktop.py --stage               # prepare only, no activation
python3 runtime/install_desktop.py --preflight --allow-notification-history-reset
# Only after explicit agreement about the current RAM history:
python3 runtime/install_desktop.py --apply --allow-notification-history-reset
# Future native-only updates, never QML/history writes:
python3 runtime/install_desktop.py --apply --movement-only
python3 runtime/install_desktop.py --apply --startup-only
```

No approval is inferred from implementing R1–R3, staging, or requesting a generic
movement/startup-only update. Reduced modes require already-native public entry
points and native QML, and update the four ELF cohort together. Full no-op repeats
do not stop a shell or rewrite markers. Known shell matching uses `list --all`,
exact config path, UID and /proc executable identity; no broad process kill.

`--apply --offline` is explicit provisioning only: no known login signature,
no compositor instances and no Quickshell instances/ambiguous listing. It never
starts/reloads a compositor/bar or initializes a login. Ordinary live callers must
not use it to evade consent.

Legacy installer paths delegate to the coordinator:

- `configs/hypr/install_workspace_navigation.py` (plan default);
- `configs/session-manager/install_session_startup.py` (native startup-only unless
  full approval/offline is explicitly requested);
- desktop integration, Quickshell config and Hyprland config shell installers.
  Their old no-argument apply entry remains gated; explicit shell flags or
  `AGORA_ALLOW_NOTIFICATION_HISTORY_RESET=1` / `AGORA_DESKTOP_OFFLINE=1` propagate
  operator choices. Hyprland layout setup runs only after consent preflight.
- `configure_session_manager.sh` preflights before writing when desktop install is
  requested. `SESSION_MANAGER_INSTALL_DESKTOP=0` leaves all existing desktop
  helpers/config alone, not secretly downgrade a native helper.
- QML calls the native workspace-controller argv directly; Lua calls the quoted
  public command. No production installer imports a Python runtime implementation
  or copies the old `.py` over a native entry.

The historical source Python files and eight frozen R0 assets remain unchanged
for legacy/oracle tests. They are not a second production implementation.
An old installed controller file can remain unreferenced for historical/manual
recovery; native callers never execute it. Deleting such personal files is not
necessary for the switch and is not done implicitly.

## Journal, partial failure and explicit restore

Private `$XDG_STATE_HOME/linux-setup/desktop-cohort/<timestamp>/manifest.json`
records all before/after targets, generation pointers, modes, phase and prior
known-shell presence. Source bytes/marker/core/native evidence are privately backed
up before any publication. Prepared, shell-stopped, pointer/files-published,
verified and complete phases are not a promise of an all-or-nothing commit.

On failure stop and inspect. Do not automatically restart a possibly incompatible
bar, normalize state, roll back window/session actions or replay startup.
Restore is a separate operator action:

```sh
python3 runtime/install_desktop.py --restore /absolute/private/backup \
  --allow-notification-history-reset
```

Restore validates ownership, safe paths, generation/file hashes and the exact
managed target set. Every current target must be recorded before/after state;
foreign later edits or a later active generation refuse. Interrupted partial
publication is supported, including failure after stopping the bar but before
any pointer/file change. Previously running bar presence is remembered for explicit
recovery; a completed repeat restore is a no-op. Reduced restores never call
Quickshell. Config restoration occurs under the common lock, with only config
reload afterward as needed. **Logical state is never rolled back**; retain/defer
the current-login marker rather than restore an absent marker and permit a reset.

R4/R5 now also support `--restore ABSOLUTE_BACKUP`, with private manifests,
hash/mode checks, absent-target recovery and refusal of later foreign changes.
Their older pre-R8 backups have no manifest: use the additional
`--expected-current-sha256 EXACT_REVIEWED_INSTALLED_HASH` explicitly, otherwise
refuse. No legacy hash is guessed or backup history rewritten. R6/R7 already have
guarded single-lot restore; R7 runtime project/WAV recovery is separate from
helper-installer rollback and is never automated.

## Current real-machine state — activated with explicit consent

Activated using `install_desktop.py --apply --allow-notification-history-reset` after
the user's explicit approval, not inferred from the generic R8 request:
`~/.local/libexec/agora-desktop/generations/c3310e56b370115f1acdec6f`.
The active current pointer, four managed native entry points and matching Lua/QML
are installed. Private backup/journal (`complete`):
`~/.local/state/linux-setup/desktop-cohort/20261120T011200-cftwgyw_`.
Known Quickshell restarted and RAM history reset as authorized. No startup initializer
or logical/native graphical mutation was invoked as a deployment test.

The updated R4/R5 installers were applied separately. They produced validated ELF
refreshes (not no-ops), matching the current release ABI, with manifest backups:

- `~/.local/state/linux-setup/notify-upgrades/20261120T004725-ob604d62`
- `~/.local/state/linux-setup/session-pi-upgrades/20261120T004725-lwfkrmq_`

Those R4/R5 preparation refreshes left other live files/PIDs unchanged. During
approved activation the cohort files and Quickshell PID changed. The coordinator's
immediate private before/after snapshots are identical. Later checks confirm four
native links, confirmed current context, unchanged marker, no Hyprland config errors,
and preserved other helpers/personal settings/entries and core/media application PIDs.
No real capture/send, media operation, model/terminal launch or startup reset was tested.

A **later** comparison observed one fewer window and session, core revision +4 and
a different active context; common windows retained their workspace assignments.
Origin was not established. Do not attribute this automatically to user activity or
migration; no repair, replay or rollback was attempted. Immediate coordinator
snapshots cover only their controlled interval. User clarification/normal-flow
acceptance remains separate.

## Evidence and still-open acceptance

`bash runtime/check.sh` retains **87 Rust tests**, strict fmt/Clippy/offline release,
R1–R7 differential/real-private/native-media/notification suites, and adds:

- First Python→native cohort handoff against a real private core and native fake
  shell, approval refusal and stage-only proofs, active no-op, corruption/personal
  edit refusal, partial failure and explicit coherent restore.
- A poisoned historical controller proving public native commands do not execute
  Python; same-login startup does not reset or launch a second bar.
- Explicit offline provisioning, genuine new/same/next-login initialization through
  installed native links on synthetic native tools/private core. UUIDs renew only
  at new compositor login; legacy windows remain unowned, no apps restored.
- Startup-only generation switch and restore without QML bytes/PID/history changes;
  malformed marker/state, unmanaged public/config links fail closed.
- R4/R5 original/absent/legacy pinned-hash restores, idempotence and later
  foreign-edit/symlink refusal. R6/R7 restore tests remain retained.
- Normal full configure in private HOME verifies native entries and untouched
  personal project override; historical installer tests now invoke cohort
  acceptance rather than verify a retired Python copy.

**Completed**: consent and live desktop handoff. **Not completed**: user clarification
of subsequent observed activity, normal-flow visual/aural acceptance for all lots,
and any user-chosen next-login check. CLOSE-WAIT-001 remains deliberately unfixed. Benchmark results/limitations
remain those recorded in R0/R1/R6; no new live latency or FFmpeg speed claim.
