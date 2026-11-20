# Pi session-aware completion notifications

## Contract

A user extension sends a **standard desktop notification through the existing `agora-notify` helper** after a Pi activity settles. It does not create a notification server, change the core API or use terminal OSC notifications/`ctx.ui.notify` as a substitute.

- `agent_start`: capture once via `~/.local/bin/agora-notify capture`, with a two-second budget. Retain the snapshot across low-level retries, compaction recovery and queued continuation runs.
- `agent_before_settle`: observe the final activity outcome only; do not append context entries or request more work.
- `agent_settled`: notify once when automatic processing is actually finished. `agent_end` is deliberately not used because Pi can immediately retry/continue after it.
- Completed activity: fixed title/body indicating Pi finished processing and awaits input. Failed activity: a distinct generic error title/body, not a false success.
- Aborted activity, startup/restored idle session, session exit/replacement or extension reload: no completion notification and no replay of abandoned work.
- Clear pending state before sending. A failed/uncertain send is nonfatal and not retried. Missing helper or capture failure/invalid output uses an explicit **global** context, never the desktop active at completion.

The content contains **no prompt, answer excerpt, conversation/session name, project path or tool result**. This is readiness/completion of the Pi activity, not proof that the model successfully accomplished every requested real-world objective. Blocking UI questions during an active run are not completion events.

## Session ownership

`session-pi` now captures a confirmed launch context, checks it agrees with the logical routing snapshot and passes `AGORA_NOTIFICATION_CONTEXT` to the new Pi process. It strips any stale parent job tag before this fresh launch capture. The context is passed both as environment and literal `env AGORA_NOTIFICATION_CONTEXT=... pi` command arguments so reused terminal servers do not silently lose the per-launch tag. Capture inconsistency/unavailability chooses global without blocking the terminal launch.

The extension's `capture` preserves that validated inherited tag. Thus a Pi launched in A remains attributed to A even while the user views B. It does not derive ownership from the working directory, app name or Pi conversation ID. Real Neutral instances use their normal session UUID; legacy no-active is the separate `neutral` context.

For Pi started directly without the launcher/tag, capture the confirmed displayed context at the first agent run of each settled activity. This fallback cannot infer a hidden terminal's owner: background/manual callers that need a precise origin should explicitly inherit a valid `AGORA_NOTIFICATION_CONTEXT`. No extension-wide process-environment mutation is performed; independent SDK sessions are not given each other's tags. Reloaded existing processes lack the new launcher tag until relaunched, so they use this fallback.

Emission always uses `agora-notify send --context CAPTURED -a Pi -t 5000 ...` with literal arguments and a three-second budget. The helper attaches `x-agora-context`; the existing Quickshell policy handles current popup, background UUID attention and acknowledgement/history. A stopped source UUID follows the existing orphan/global presentation rule; no new session is created/adopted.

## Install / activation

```sh
python3 configs/pi/session-notifications/install.py          # read-only plan
python3 configs/pi/session-notifications/install.py --apply
```

The targeted installer checks the installed Pi declarations support `agent_settled`, then privately backs up and installs only:

- `<PI_CODING_AGENT_DIR or ~/.pi/agent>/extensions/agora-notifications/index.ts`;
- `~/.local/bin/agora-notify` as the pinned/locked offline-built Rust ELF (Rust 1.96.1/cargo must already be available);
- validated Rust `~/.local/bin/session-pi` **if already installed**, after the usual v3 compatibility guard. R5 uses the same pinned runtime builder; Python is never restored. A missing launcher is still left absent.

R4 replaced the helper implementation only; the extension API/lifecycle and 2 s capture/3 s send budgets are unchanged. The same Rust helper is installed by `configure_session_manager.sh` through `runtime/install_notify.py`, so neither configuration route restores the old Python helper. See [R4 contracts/evidence](../../../runtime/R4-notify.md). [R5 routing and installer evidence](../../../runtime/R5-pi.md) documents the independently installed native launcher; SUPER+P, global entry and personal project overrides keep their command names.

The ordinary Pi package installer delegates to this targeted installer. It does not update Pi/npm automatically. Unsupported distributions/events fail clearly rather than falling back to an early `agent_end` alert.

Personal settings, keybindings, other extensions, credentials, MCP configuration and session transcripts are not rewritten. Backups live under `${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/pi-notifications/` in private directories. Symlinked/nonregular targets are refused. No Pi/model/app/core/Quickshell restart, notification emission, trust change or real-session mutation is an installation check.

**New Pi processes auto-load the extension. Existing idle Pi processes require an explicit `/reload`**, or reopening Pi; an active agent is never forcibly interrupted/reloaded. Quickshell does not need reloading, so its current RAM history is retained. `--no-extensions` / resource exclusions intentionally disable this feature. Independent Pi processes which load the extension each produce their own settled notification; nested model calls within a process do not each count as a separate task.

## Evidence

- Read the installed Pi extension/configuration/settings/package/CLI documentation and event declarations; follow the official `examples/extensions/notify.ts` settlement hook, replacing terminal notifications with the session-aware helper.
- `node --experimental-strip-types --test configs/pi/session-notifications/test.mjs`: **11 tests** for no factory/startup side effects, capture-once/retries/queue settlement, duplicate suppression, independent activities, abort/shutdown/reload, error labeling/privacy, invalid/failed capture, send failure and late captures. Uses the real helper with a fake sender/status A→B; checks the transmitted context hint and inherited origin; loads the extension through Pi's installed loader without starting a model or reading credentials.
- `python3 configs/pi/session-notifications/test-install.py`: real targeted installer in temporary HOME with fake Pi/core tools; capability gate, backups/copies, settings/other extension preservation and symlink refusal. No actual task or desktop notification.
- `test-session-pi.py`: project/neutral routing plus expected UUID capture, literal terminal argv/environment, stale-parent removal and global failure fallback; no actual terminal launch.
- Existing real-private-core and helper/OBS/pre-edit regressions pass. The unchanged notification policy/private bus tests remain the authority for rendering/attention, not this extension's event mocks.

Actual popup/background-border acceptance remains manual after extension activation. Installation compares read-only core/native/shell snapshots and file bytes; personal messages/notifications and Pi transcripts are not inspected.
