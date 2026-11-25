# Shift application shortcuts — fresh workspace, then contextual launch

## Contract

Stage 1 only: SUPER+Shift+B/P/E/Return/D invoke
`workspace-controller open-new browser|pi|files|terminal|apps` respectively.
Plain shortcuts, SUPER+Shift+S, SUPER+Tab and SUPER+Shift+Tab are unchanged.

Each valid request allocates a **fresh** ordinary workspace, including when the
source is already empty. Insert directly after the source in metadata order,
retain its exact UUID owner (or unowned `neutral`), focus and confirm it empty.
Ordinary empty-workspace cleanup remains; an empty source may disappear on leaving.
No logical session is started, stopped or transferred. No window is moved/adopted.
A visible scratchpad, unknown context or multiple monitors refuses the request:
hide the scratchpad explicitly before using these shortcuts.

## Shared orchestration and guards

`new_workspace.rs` owns the five closed targets; no command string/user shell
parser, new daemon or registry. Before creation:
- Require absolute HOME/runtime, fresh confirmed desktop/core context, one ordinary
  monitor, matching owner metadata and repeated stable status.
- Prepare existing files/Pi routing and freeze the directory dev/inode; Pi keeps
  native `--continue`, the existing Agora fallback and its captured notification
  origin. Files retains the project-or-HOME fallback policy.
- Check required executables/capabilities. The app menu needs the existing
  `[expected-workspace-v1]`; browser requires `[expected-browser-v1]`. Missing/old
  helpers fail before allocating a workspace.
- Recheck the captured workspace/context after planning. Under the desktop lock,
  reread metadata, require the captured source/owner, reserve a fresh ID and
  publish the existing metadata schema. In the same Lua evaluation as fresh
  focus, reject changed source, visible special workspace, multiple monitors and
  target collisions. No polling, fixed delay or mutation retry.
- Confirm the target exists/active/empty after metadata finalization, release the
  lock, then verify fresh core/desktop ownership again. Do not focus back on a
  failed check. Files/Pi recheck pinned directories and expected context directly
  before launch.

App/browser exec-replace the controller with the existing expected-workspace
launcher. Its additional pre-menu/pre-selection/desktop-token checks remain.
The controller appends `~/.local/bin` to that child's PATH if absent (plain B/D
previously obtained it via a login shell), preserving literal desktop Exec/TryExec
lookup without evaluating a shell command. Pi/files/terminal use literal argv.
Only plain SUPER+D records statistics. Shift+D reads ranking but publishes no
usage event. Shift+B, like B, does no history/store/lock/Git-exclusion work.

## New-window requests and limits

- **Terminal:** existing `kitty` command, normal independent window.
- **Pi:** existing `launch-terminal-command DIRECTORY env ORIGIN pi --continue`.
  It resumes by directory, not UUID; no new conversation/concurrency registry.
- **Files:** always one literal `xdg-open ABSOLUTE_DIRECTORY`; the system selects
  its default file manager. No MIME-ID specialization, Thunar binary/flag or
  dependency. A default manager may reuse a window/tab according to its settings.
- **Browser:** a guarded Firefox launch uses the selected desktop entry's declared
  `new-window` action if present. Otherwise keep the literal installed/project
  Exec path, not a rewritten command. Existing project Firefox wrapper already
  requests a new window and retains its UUID/profile/`--no-remote` policy.
  Custom overrides and profile exclusivity can still reuse/refuse a window.
- **Apps:** preserve normal arbitrary desktop-entry behavior; not every application
  offers a new-window interface.

This confirms context before dispatch, not an atomic transaction with later GUI
mapping. A later navigation, app-specific routing, single-instance reuse, browser
profile locking or application failure cannot be repaired by moving windows.
Cancel/failure leaves the new workspace (ordinary cleanup when subsequently left);
no automatic rollback, return-focus, retry or session stop. A GIO desktop action
has no synchronous application-success acknowledgement.

## Validation and deployment

`tests/test_new_workspace.py`: 40 real orchestrator/launcher cases on private
D-Bus, temporary HOME and **all** explicit XDG roots, fake native/core/apps only.
Covers five targets, occupied/empty/unowned/project origins, literal paths, Pi
continuation/origin, generic default opener (no Thunar/MIME special case), actual GIO new-window action using a
fake executable in `~/.local/bin`, history exclusion, released workspace lock,
source/target/directory races, uncertain replies, cancellation and no replay.
Exact generated source/fresh-target guard also executes with Lua.
Full `runtime/check.sh` passes: 113 Rust workspace tests (83 desktop) plus existing
cohort/core/CLI/notification/QML suites and 14 legacy Tab cases. Separate launcher
30 Rust tests pass. No real application, project session, workspace or profile is
opened to validate deployment; visual acceptance uses normal user activity.

Install matching launcher first, then native/keybind cohort:
```sh
CARGO_NET_OFFLINE=true bash configs/session-manager/install_app_launcher.sh --apply
python3 runtime/install_desktop.py --apply --movement-only
```
No QML copy/reload, Quickshell restart/history reset, initializer or core restart.
Existing installer backup/journal and explicit restore procedures apply. This
publication is two installer operations, not a global filesystem transaction;
capability refusal protects against an old browser launcher during partial setup.

## First latency reduction — installed 2026-11-23

Initial capture remains fully bracketed. Revalidation now checks the *expected*
workspace/owner/no-special/single-monitor under the metadata lock, releases that
lock and validates one fresh typed core/desktop status. It no longer constructs
another full capture with two status subprocesses. The redundant common post-focus
check was removed: every route retains its own check immediately before dispatch
(Pi/files after directory identity validation; browser/menu also retain their child
launcher guards). Atomic source/collision protection and empty-focus acknowledgement,
token removal, no retry/rollback/cache/daemon remain unchanged.

Terminal route status subprocess count: **8 -> 4**; files may perform additional
existing directory-routing checks. The 40-case private matrix and full runtime
suite (113 Rust) pass with the revised checks and all prior race/refusal cases.

Measurement: four terminal requests (occupied/empty/unowned/project), same private
Python fake core/native/apps, old executable vs new executable, no GUI:
- before milliseconds: 1129.2, 1095.1, 1087.2, 1063.2; median **1091.2**;
- after milliseconds: 882.7, 886.4, 879.7, 869.4; median **881.2**;
- approximately **19.2%** median reduction in this small synthetic sample only.
This includes fake-tool startup overhead and controller completion, not real
application mapping, a cold-start guarantee or a per-phase production profile.
The harness accepts `SHIFT_TEST_CONTROLLER=/absolute/test/binary` for reproducible
private comparisons and prints the four terminal times.

Installed via movement-only cohort `78eed325e679186ccc29ceaf`, complete backup
`desktop-cohort/20261123T085853-mj6y_54d`. Exact core/desktop/state/marker/PIDs,
index/QML/keybinds/ordinary helpers preserved. No real app/workspace test or shell
restart. User-perceived improvement remains to confirm. Direct in-process status
transport/batched compositor reads are possible follow-up work, **not implemented
or counted as gains in this iteration**.

## Placement repair — installed 2026-11-23

User acceptance found B/P/Return mapping in the source workspace and E not opening.
The initial test fixtures missed real compositor environment placement and accepted
a nonexistent Thunar flag; they proved dispatch order, not actual GUI mapping.
Exact installed Hyprland source (`efb50993780079460b0cbed1363e2166a2de1d9f`,
Executor.cpp / Window.cpp) confirms exec captures the source workspace in
`HL_INITIAL_WORKSPACE_TOKEN`, inherited by children and applied at mapping.
Live configuration had one-shot tracking enabled with 10-second expiry.
An isolated Thunar parser probe printed `Unknown option --new-window` even with
exit 0; its documented flag is `--window`, but we now remove this specialization.

All five Shift launch routes now remove **only** `HL_INITIAL_WORKSPACE_TOKEN`
from their application child environment after creating/confirming the target.
Pi has a new launch variant; ordinary `pi::launch`/SUPER+P retains its environment.
No process-global environment mutation or global compositor tracking change.
Browser/menu descendants inherit the cleaned environment. No window-move repair.
Later mapping races and existing-app window reuse remain possible as documented.

The 40-case matrix injects a synthetic source-workspace token and fails if any
application receives it (including GIO action/Pi helper); files asserts literal
xdg-open and no Thunar/xdg-mime invocation. Full suite/strict Clippy pass
(113 Rust). These remain private tests, not a real GUI-placement acceptance claim.

Active generation: `61ed3e668f4a0d136aa4fec3`.
Backup: `desktop-cohort/20261123T084140-eho4iyu9`, complete journal.
Movement-only installer used; exact core/desktop/ownership/marker snapshots,
core/shell PIDs, index, QML/keybinds, ordinary Pi and app-launcher bytes unchanged.
No real app/workspace/initializer launched to validate; user retry remains open.

## Initial installation 2026-11-22

- Active native generation: `d4b8a674a739f593d080d4bd`.
- Cohort backup: `~/.local/state/linux-setup/desktop-cohort/20261122T115330-7avclhby`.
- Launcher backup: `~/.local/state/linux-setup/app-launcher-upgrades/20261122T105330-DwSAVT4G`.
- Full runtime suite passes: 113 Rust tests (83 desktop + 16 audio + 14 thumbnail);
  launcher 30 Rust tests/strict Clippy and 33 usage regressions pass. The new
  40-case private executable matrix and exact Lua guard tests cover all routes,
  empty source, Neutral/project/unowned owners, directory replacement, context
  switches, no history writes and browser new-window action/local-bin lookup.
- Actual deployment checks: five unique SUPER+Shift bindings, native capability
  tags and installed source bytes; exact core/desktop/metadata/marker snapshots,
  personal desktop entries/project histories/index and shell/core PIDs unchanged.
  Hyprland reports no config errors. No artificial real workspace, app, menu,
  project/profile, transfer or initializer used for acceptance.
- Normal visual acceptance remains user-driven. Step 2 (Shift+S) and step 3
  (Tab removal) have **not** been applied.
