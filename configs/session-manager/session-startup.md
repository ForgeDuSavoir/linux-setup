# Fresh session at Hyprland login

## Policy

At each new Hyprland compositor instance (PC boot or logout/login), forget the previously open logical sessions and select exactly one **Neutral-1**, on a fresh empty UUID-owned ordinary workspace. Do not restore projects, launch their applications, move/close windows or modify project files/browser profiles.

This replaces the previous desktop policy of retaining open instances across graphical logins. It does **not** change the core's persistence/API contract: sessions remain durable across a core daemon restart within the same graphical login. The reset is a downstream initialization action, not a daemon `ExecStartPost` action.

- `startup.lua` invokes `session-startup` on **`hyprland.start`**, not configuration reload. When the helper is absent (an installation without Session Manager), retain the old Quickshell autostart fallback.
- `session-startup` waits for the existing v3 service, reads its open instances, stops that exact snapshot through the core API, verifies the list is empty, then starts one built-in Neutral instance. This is an explicit new-login exception to the ordinary graphical last-session stop guard. No persistent runtime file is deleted or rewritten externally.
- Existing ordinary windows in the new compositor remain unowned. Old desktop ownership metadata is archived privately and replaced by a fresh projection of the **new** compositor's IDs; reused IDs never inherit an old UUID. Select a newly allocated, compositor-guarded empty workspace for the new neutral session.
- Check the resulting logical session/source/number and visible desktop before starting Quickshell, so its first menu snapshot has a matching context. Other existing autostarts (wallpaper, idle/clipboard services) remain independent; initialization launches no user application.
- Exactly one compositor and the existing single-monitor policy are required. Already-present UUID-scoped scratchpad windows fail closed rather than losing their associations. Shared/global and legacy unowned windows are never closed or adopted.

## Once per graphical instance

`${XDG_RUNTIME_DIR}/hyprland/session-startup.json` records version 1, `HYPRLAND_INSTANCE_SIGNATURE` and a phase, under the shared `workspace-columns.lock`.

- `initializing` is published before attempting the reset; success records `ready` and the new session UUID.
- A successful repeat in the same instance does nothing, even if the user subsequently opened other sessions or stopped the original neutral instance. It does not start another bar.
- A different compositor signature authorizes a fresh initialization, including logout/login within one OS boot when the runtime directory survives.
- Core/Quickshell restart, config reload, screen lock and suspend/resume do not reset sessions. No systemd unit change or core restart is needed.
- Live installation records the current compositor as **`deferred`**, not initialized: all its sessions, windows, ownership and core revision stay intact. Only the next graphical instance uses the new policy.

## Failures and concurrency

Only initial read-only availability checks are retried (a bounded readiness wait with two-second query timeouts). Mutating calls are never replayed after a lost/invalid acknowledgement. Failed/crashed attempts are recorded as `failed`/`initializing` and cannot automatically reset the same login again. Independent direct core clients do not share the desktop lock: unexpected remaining sessions or final selection/source mismatches are reported, not fixed by deleting newly created concurrent sessions or moving windows.

A first-attempt failure is logged to stderr and the user journal (`journalctl --user -t session-startup`, or `journalctl -t session-startup` depending on journal routing); Quickshell still starts for manual menu recovery. A repeated failed attempt does not start a duplicate bar. There is no automatic rollback or claim that an uncertain stop did not commit. Private pre-reset core/desktop metadata backups live under the runtime directory, mode-0700 `session-startup-backup-*` directories; they are diagnostic only, never automatically restored.

## Install for the next login

```sh
python3 configs/session-manager/install_session_startup.py          # plan only
python3 configs/session-manager/install_session_startup.py --apply  # current desktop untouched
```

The dedicated installer requires protocol 3 and the single-workspace model, backs up the startup/helper files and private snapshots, installs `session-startup`, `session-desktop` and `startup.lua`, defers the current instance under the desktop lock and reloads only Hyprland configuration. It never invokes initialization, starts/stops/switches a real session, queries/restarts Quickshell or replaces QML. Core and desktop snapshots and workspace metadata must remain unchanged. Private installation backups are under `${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/session-startup/`.

Full desktop installation also ships the helper/startup hook; the coordinated full installer defers a running compositor before reload. Movement-only updates deliberately leave this separate policy untouched.

## Validation

- `test-session-startup.py`: **22** isolated cases, including reset/select, logout/login with a retained runtime, same-instance no-op, live-install deferral, shared-lock concurrency, startup availability, multiple compositor/monitor and scoped-window guards, uncertain stop, failed focus, concurrent core changes and bar launch ordering/failure recovery. No actual windows or applications are used.
- `test-startup-install.py`: real targeted installer in temporary HOME/XDG roots with fake native/core tools; dry run, current-context deferral, private backups, unchanged data and shell, installed extensionless helper execution, and no core mutation/Quickshell call. Fake Lua proves loading/reloading only registers the start callback.
- `test-neutral-v3.py`: real private v3 daemon and fake compositor; new-login reset, exactly one Neutral-1, repeat-call revision stability and new UUID after same-boot relogin, without consulting an unavailable project directory or launching applications.
- Existing controller, lifecycle/stop/status and full/movement-only installer regressions pass.

Installed live for the next login on 2026-11-18. Technical checks preserve the current desktop, complete core projection/revision and core/shell PIDs, with no notification-history reset. An actual logout/reboot is deliberately not an automated validation step; next-login visual acceptance remains manual.
