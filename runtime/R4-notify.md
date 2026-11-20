# R4 — Rust notification helper, installed independently

Implemented, tested and **installed as the single helper only** on 2026-11-19.
R1–R3 desktop runtime activation remains deferred. No core API change, new daemon,
notification server/history or desktop/Pi/Quickshell reload is introduced.

## Contract

`agora-notify capture` prints a validated inherited AGORA_NOTIFICATION_CONTEXT,
including explicit global/unowned, without HOME/backend access. Invalid inherited
values fail; they never trigger a fresh capture. Without inheritance, query the
existing absolute `~/.local/bin/session-desktop status`, with its original 35 s
budget, and require an actual boolean confirmed flag and consistent displayed/
active/member identity. A real Neutral instance uses session:UUID; legacy no-active
uses neutral. Unknown/unconfirmed/malformed state fails, never invents Neutral.

The helper is native Rust; the desktop companion is intentionally its existing
public process interface, not an embedded Python fallback. That companion is still
Python on the live machine until R8 and will become the R2 ELF without changing
this ABI. Thus R4 removes Python from the **helper itself**, not yet from the
entire capture process tree. No dependency on a neighbouring core checkout.

`send [--context VALUE | --global] [-u low|normal|critical] [-a NAME]
[-t INTEGER] [-r UINT32] SUMMARY [BODY]` retains defaults, short/long options,
long-option unique abbreviations, repeated same options, explicit `--`, optional
body, negative expiration and integer normalization. Context priority is explicit
global/context > inherited > global. Invalid values fail rather than recapturing.
Only canonical lowercase UUID context syntax is accepted. Syntax errors return 2,
operational/validation errors 1, success/help 0; `--version` is a new read-only path.
Help text/diagnostic wording is not byte-for-byte argparse output. CLI numeric
syntax is ASCII decimal (with signs/underscores as supported), not exotic Unicode
digit coercion. Negative/dash message arguments and literal quotes/shell syntax
are preserved without evaluation.

Emission calls `notify-send` through literal argv, including
`--hint string:x-agora-context:VALUE`, app name, urgency, optional expiration/
replacement, and `-- SUMMARY BODY`. Replacement ID is checked as u32; expiration
is kept as a normalized arbitrary-length signed decimal string, avoiding a new
helper-side i64 overflow restriction. The emission budget remains 10 s.
**Send never consults status** and is never retried after failed/uncertain emission.

Existing outer deadlines remain authoritative: Pi capture 2 s, Pi send 3 s,
OBS capture 2 s. R4 does not change the extension's settled hook, payload privacy,
abort/error/reload rules or the shared Quickshell attribution/attention policy.
The common direct-child transport adds the already reviewed 4 MiB per-stream
capture bound; oversized/invalid results fail without retry. Native sender output
is captured, not replayed into model context; routine notify-send emits no stdout.

## Installation and prevention of Python rollback

```sh
python3 runtime/install_notify.py          # no-effect plan
python3 runtime/install_notify.py --apply  # pinned offline build, helper only
```

The installer builds only `agora-notify` with Rust 1.96.1, locked dependencies,
fixed runtime target directory and offline Cargo; verifies ELF/version without
status/send; privately backs up the previous command and atomically replaces
`~/.local/bin/agora-notify` at 0755. Refuses symlink/nonregular targets/unsafe backup
paths; repeated unchanged installation is a no-op. It never installs toolchains,
starts a service or emits a notification. Reverting to a saved prior helper is
an explicit operator action, not an automatic retry/rollback after uncertainty.

- `configs/pi/session-notifications/install.py` now builds/installs this validated
  ELF via the shared build routine, not `agora-notify.py`. Other Pi resources are
  preserved as before. It additionally refuses to downgrade an already ELF Pi
  launcher to Python; R5 remains responsible for the new launcher implementation.
- `configure_session_manager.sh` delegates notification installation to the same
  targeted Rust installer, so a subsequent normal setup cannot silently restore
  the Python helper. The normal full configuration was not run on the live machine.
- The old Python file remains temporarily for legacy/import-based tests and R0
  history; **no production installer copies it**. The immutable R0 oracle is used
  for differential comparison. Final source cleanup is R8, not a second runtime.

Only the standalone helper installer was applied live, not the Pi/full desktop
installer. Backup: `~/.local/state/linux-setup/notify-upgrades/20261119T161513-kzorwdzo`.
Installed bytes equal the release ELF and version reports
`agora-notify 0.1.0 (Rust; x-agora-context)`.
Private before/after snapshots compare exact core/desktop state and core/shell
PIDs; QML, Pi settings/extension/launcher, desktop/startup helper hashes remain
unchanged. No real capture/send, notification content inspection, application,
model, core/session mutation or reload was used to validate installation.

## Evidence

`bash runtime/check.sh` now includes all R1–R3 suites plus:

- **50 Rust tests total**: context syntax, priorities, invalid inheritance,
  confirmed status, literal argv, expiration/replacement bounds and parser/help;
  fmt, strict Clippy and release offline/locked pass, no new crate dependency.
- **75 R4 real-CLI differential scenarios** vs frozen Python, plus a capture-A →
  selection-B → send-A case verifying one capture and no completion-time lookup.
  Inherited invalid/empty context, unknown status, sender/status failures, numeric
  boundaries, explicit/global precedence and shell-like payloads are covered.
- Actual OBS Lua/start-stop and pre-edit wrappers now use the **Rust ELF** with
  fake status/sender/editors and temporary synthetic media. Original wrapper tests
  preserve A through an asynchronous switch to B. No recording/editor is launched.
- The **11 existing Pi extension tests** now exercise the real Rust helper for the
  frozen-context integration case (fake sender/status), and still load via Pi's
  installed loader without starting a model or reading credentials/transcripts.
- Pi targeted installer tests in private HOME check actual ELF bytes, backup,
  personal settings/extension preservation, unsupported Pi/symlink refusal and
  no downgrade of a preexisting ELF Pi launcher. Standalone installer tests verify
  plan/idempotence/private backup/ELF copy/symlink refusal. Real private-core/normal
  setup regressions also pass with the Rust notification installer.
- **Actual offscreen Quickshell server on private D-Bus**, standard notify-send
  from the Rust helper: hint/context/app identity arrive in the single store with
  expected background unread/no popup. Full policy/strip lifecycle tests still
  cover global/unknown/orphan, acknowledgement, replacement and expiry. No personal
  bus or notification content is used. This is not live Wayland visual acceptance.

At the R4 deployment only this helper was activated; [R5](R5-pi.md) has since
independently deployed the native Pi launcher and updated its installer tests.
The historical R4 checks above describe that earlier deployment. The extension
uses the public helper on each invocation without requiring Pi reload. Visual acceptance in the user's normal flow
is separate; no synthetic live notification was emitted merely as a test.

R8 adds guarded `--restore ABSOLUTE_BACKUP`; older backups without manifests require
an explicit reviewed `--expected-current-sha256`. [R8 state/backup/test details](R8-deployment.md).
No notification is emitted by install/restore.
