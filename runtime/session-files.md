# Session-aware file manager — SUPER+E

`session-files` opens one folder through `xdg-open`, using the existing default
directory handler (Thunar in this setup). Native Rust in `desktop-tools`; no
Python runtime, shell interpolation, new .desktop entry or MIME reassignment.

## Routing

| Situation | Folder |
| --- | --- |
| Confirmed project session, available project root | Current catalogue project root |
| Neutral UUID or no active session | HOME |
| Unknown/unconfirmed/inconsistent status | HOME |
| Missing/invalid/unavailable daemon, helper, project or catalogue | HOME |
| Inaccessible/non-directory/relative/final-symlink project path | HOME |
| Session/source or directory identity changes during lookup | HOME |

HOME must itself be an existing absolute directory. No Agora-root setting is read:
the HOME fallback is intentional here, unlike Pi's neutral-directory policy.

Read absolute `~/.local/bin/session-desktop status`, use the existing typed v3
session/source checks and canonical confirmed-context validator, then query the
public `session-manager --json project list`. Catalogue transport/lookup is shared
with Pi; Pi retains its own routing/failure policy. No project registry, cwd/name
guessing, adoption or core API change.

Check directory availability/access without enumerating contents, then recheck
the confirmed session/source and directory dev/inode before choosing it. Each of
at most three readonly probes has a 2-second deadline and the existing 4 MiB
per-stream capture limit. Errors/invalid JSON/nonzero/timeout select HOME;
notification-context inheritance is not used for this fresh launch.

Finally invoke `xdg-open ABSOLUTE_FOLDER` once, as literal argv. Quotes, Unicode,
spaces and shell metacharacters remain filenames. Opener failure is an error,
not a second launch: it may already have opened a window. This is not an atomic
transaction with external context/filesystem changes; races after the final check
cannot be ruled out. Window creation/reuse belongs to the default manager: no
window focus/move/close or ownership transfer is implemented.

## Scope and installation

Only SUPER+E calls this command. Application-menu entries and existing Thunar
.desktop/MIME associations remain unchanged. Explicit folder requests from other
applications continue opening their requested folders normally.

The native coordinator stages `session-files` alongside the four original desktop
commands and the matching binding, then applies with:

```sh
python3 runtime/install_desktop.py --apply --movement-only
```

Four-command generations/backups remain valid. A missing new entry is added only
when absent from the prior generation; a personal existing command is refused.
Generation-derived target plans permit explicit expansion rollback (remove new
link, restore prior binding/pointer), including restore of older four-command
manifests. No QML write/reload is required; Quickshell/history stay intact.

Deployed on 2026-11-20, generation
`~/.local/libexec/agora-desktop/generations/ef6cb4adb44e3ef98a29d5be`,
private backup
`~/.local/state/linux-setup/desktop-cohort/20261120T123323-tcs2tkci`.
Five native links verified; exact core/desktop/state/marker and shell/core PIDs
unchanged. Menu entries, personal desktop overrides, MIME associations and usage
files unchanged. No real file manager launched as a test.

## Validation

- Eight Rust routing/catalogue invariants; **95 Rust tests total**, fmt/Clippy strict
  and pinned locked/offline release plus the complete existing runtime suites pass.
- `tests/test_session_files.py`: **28 actual CLI cases**, help/version/syntax,
  project/HOME, unavailable/incoherent/changing context, malformed data, access,
  missing helper, timeouts, literal names and alternate default. Exactly one opener.
- `tests/test_session_files_private_core.py`: genuine private v3 core and Rust
  desktop status, synthetic native backend and fake opener. Project, unavailable
  catalogue, Neutral, no session and spatial mismatch; metadata/core unchanged.
- `tests/test_cohort_files_expansion.py`: old-four→five, personal-command refusal,
  no QML/PID/state change, explicit expansion rollback and older manifest return.
- Updated default-application test checks the actual Lua binding without executing
  a graphical action. Pi routing regressions remain green after shared lookup reuse.
