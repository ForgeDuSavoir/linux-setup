# SUPER+Tab — confirmed empty workspace, then contextual launcher

## Behavior

SUPER+Tab now invokes `workspace-controller create-empty-and-launch`.
- Occupied ordinary workspace: allocate a fresh ID in the same owner, focus it,
  finalize desktop metadata, confirm it with Hyprland, then open the contextual menu.
- Empty workspace: retain existing previous-same-owner navigation; no menu.
- Visible scratchpad: retain hide-first behavior; no creation/menu.
- Failure, uncertain reply or unsuccessful confirmation: no menu or automatic retry.
- Menu cancellation/failure leaves the created workspace; no automatic undo/stop.

The old `create-empty` action is unchanged and remains available without a menu.
Shift+Tab and all other navigation are unchanged. No core API/policy change.

## Explicit compositor acknowledgement, no delay

Existing guarded Lua performs fresh-ID collision checking and workspace focus.
After its synchronous reply and metadata cleanup, one **readonly Lua eval** checks:
the target exists, `hl.get_active_workspace().id` matches, and
`#hl.get_workspace_windows(target) == 0`. Error/nonzero/native transport failure
aborts before menu invocation. Creation and confirmation are two sequential IPC
requests, not a guessed sleep, polling loop, animation timer or global event hook.

Only the actual fresh-creation branch returns an internal
`{workspace_id, owner}` outcome. The CLI drops the controller/LockedStore before
exec-replacing itself with the absolute installed launcher:

```text
session-app-launcher --expected-workspace ID OWNER
```

The workspace lock is never held/inherited while Rofi or launcher queries run.
A readonly launcher capability check before workspace IO refuses an old/missing
launcher; no workspace is created when the required interface is absent.

## Expected context guard and history

The launcher accepts only a positive bounded workspace ID and canonical UUID
owner (or literal `neutral` for unowned). Its existing confirmed core/metadata/
monitor snapshot additionally checks exact workspace, owner and absence of a
special workspace, both during snapshot/revalidation and immediately before Rofi.
Selection revalidation checks them again before GTK/Gio invocation.

Navigation concurrent with these checks cancels the request rather than focusing
back, adopting windows or launching on a knowingly different workspace. An
already-visible Rofi menu is not continuously supervised/closed on every event;
a changed context is refused when selecting. There is no atomic transaction
between independent context checks and GUI mapping/launch: later races remain
possible, and this is not a guarantee that rendering/animations have finished.

Existing ranking is read for SUPER+Tab, but **only ordinary SUPER+D selections
update history**, as before. Guarded Tab launches pass no store to the launch/
publication path. Browser still bypasses all history IO, locks and exclusions.

## Installation / compatibility

Native cohort plus keybind:
```sh
bash configs/session-manager/install_app_launcher.sh --apply
python3 runtime/install_desktop.py --apply --movement-only
```

No QML write/reload or notification-history reset. Normal setup installs both
components via existing routes. During partial/older deployment the new action
fails closed until a matching launcher is installed; ordinary menu/browser calls
remain compatible. Explicit restore uses existing separate launcher/cohort backup
mechanisms, never a runtime session/window rollback.

Live native generation: `5066b18c0a4e8ac8ccd1bec2`.
Cohort backup: `~/.local/state/linux-setup/desktop-cohort/20261120T135719-ps0dmxeu`.
Initial launcher backup: `app-launcher-upgrades/20261120T125719-lHhN6oRK`;
final history-policy correction backup:
`app-launcher-upgrades/20261120T130154-IRU7ciQ6` (same private state root).

Immediate deployment checks: exact core/desktop/metadata/marker snapshots and
shell/core PIDs unchanged, one SUPER+Tab binding, no Hyprland config errors,
existing project entries/history/index unchanged. No real workspace/menu/app was
created to validate this change. Normal graphical user acceptance remains open.

## Validation and test isolation incident

Complete runtime suite passed, including frozen existing workspace parity.
Launcher: **30 unit tests**, fmt/strict Clippy/locked-offline release, 22 CLI
regressions, 33 history cases and installer/restore checks passed.
`tests/test_tab_launcher.py` executes real controller and real launcher against
private fake Hyprland/Core/Rofi/GTK: **14 cases** (creation, unowned, cancellation,
empty return/no-op, scratchpad, collision/lost reply, confirmation failure,
navigation before/during menu, special workspace, missing/old launcher).
The exact confirmation Lua also runs under synthetic compositor state.
Checks cover ack-before-menu, lock released, no retry/rollback and no Tab usage
publication. Included in `runtime/check.sh`.

**Incident requiring explicit follow-up:** the first two runs of the new test
overrode HOME/runtime/data/config but accidentally inherited real XDG_STATE_HOME.
They added `test.desktop` with count **2** to each real
`~/.local/state/session-app-launcher/{neutral,unowned}.json` (and may have created
associated lock files). Other records were not individually edited by the test;
normal history retention/publication logic ran, and there is no full pre-test
global snapshot from which to assert byte-for-byte preservation.

The test now explicitly sets XDG_STATE_HOME inside its temporary root and asserts
no usage JSON is published by guarded Tab launches. Corrected tests and the
33-case history suite passed, and the corrected launcher is installed. The
incident was disclosed to the user. **No real history entry/file was deleted or
restored automatically** before consent. Do not claim all personal/global usage
data remained unchanged during the incident.

### User-approved cleanup completed — 2026-11-20

After explicit approval, both stable launcher history locks were acquired and the
known synthetic count/timestamps validated. Private before/after payloads and a
complete phase journal are saved at
`~/.local/state/linux-setup/tab-launcher-test-incident-cleanups/20261120T131207Z-3daug6ov/`.
Only the `test.desktop` member was removed from each JSON object, without
reserializing other entries/numbers. Exact post-cleanup contents and unchanged
other counters were verified under the locks; file permissions remain 0600.
No other entry, history file or lock was removed. This cleans the two known
synthetic records, not a reconstruction of the unavailable full pre-test baseline.
