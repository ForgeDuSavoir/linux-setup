# Session notification integration (stage 2)

## Ownership and compatibility

This is a downstream `linux-setup` contract. Session Manager is unchanged: it owns UUIDs, lifecycle and ordered logical sessions, not notifications, history, attention or desktop confirmation. `SessionService.qml` supplies its confirmed graphical context. `NotificationStore.qml` contains the **existing single** notification server and in-memory history, extracted from `NotificationService.qml` for isolated testing. `NotificationService.qml` inherits that store and renders its eligible notifications. This is not a second daemon, server or history.

Untagged notifications continue to use global presentation. Stage 3's helper, the versioned OBS/pre-edit scripts and Pi's completion extension now support explicit captured contexts (see inventory below); Beeper remains deliberately global after a static audit of its installed 4.3.123 package, and FilmCraft render completion is deferred.

## Standard notification hint

Send an optional string hint `x-agora-context` in the standard `org.freedesktop.Notifications.Notify` hints map:

| Value | Meaning |
| --- | --- |
| `session:<UUID>` | Specific session; canonical lowercase hyphenated UUID |
| `neutral` | Neutral desktop, not a session UUID |
| `global` | Show independently of selected session |
| Missing/invalid | Recorded as `unknown`, presented globally; never guess active session |

Example with an **explicitly selected test UUID**, not a production auto-capture wrapper:

```sh
notify-send --hint=string:x-agora-context:session:11111111-1111-1111-1111-111111111111 'Synthetic test' 'No private content'
```

The caller of an asynchronous operation must capture its UUID when work starts and retain that value until notification emission. Setting an environment variable without transmitting the hint does nothing. Hints are same-user coordination, not authentication/security isolation. No correlation by app name, summary or notification arrival's active session is implemented.

A well-formed UUID absent from a fresh session list is marked orphaned and presented globally. Its original context/source remain in history; it never creates a session. If the session list is stale, retain scoped attribution conservatively rather than guessing that the session stopped. On a subsequent fresh list, orphan status is reconciled. A live notification newly orphaned can be surfaced globally once.

## Emission helper and script inventory (stage 3, first two tasks)

`configure_session_manager.sh` installs the Rust `agora-notify` ELF in `~/.local/bin` via `runtime/install_notify.py`. R4 was deployed independently without a shell reload; [contracts, compatibility and evidence](../../runtime/R4-notify.md). The public capture/send interface and existing single server/history are unchanged; Pi's targeted installer uses the same validated build rather than restoring Python. [R5](../../runtime/R5-pi.md) also ports the Pi launcher, retaining fresh capture with stale inheritance removed, coherent origin/global fallback and literal terminal `env` argv; both setup paths now deploy the validated Rust launcher.
It uses standard `notify-send`, not Quickshell IPC or a core notification method.
Capture uses the existing read-only `session-desktop status`, so it works with
another notification server and does not depend on Quickshell being active.

```sh
# Freeze once, before launching the asynchronous work. Inherited snapshots
# are validated and preserved, so child jobs retain their parent's origin.
AGORA_NOTIFICATION_CONTEXT="$(agora-notify capture)" || AGORA_NOTIFICATION_CONTEXT=global
export AGORA_NOTIFICATION_CONTEXT
# ... work, potentially while the user changes sessions ...
agora-notify send 'Processing finished' 'Synthetic example'

# Explicit modes do not look up whatever session happens to be current now.
agora-notify send --context "session:<canonical-UUID>" 'Finished' 'Details'
agora-notify send --global -u critical 'System operation failed' 'Details'
```

`capture` prints a validated inherited `AGORA_NOTIFICATION_CONTEXT`, or captures
the confirmed displayed session/neutral context. Missing/inconsistent desktop
state fails (it never invents neutral). The script examples deliberately choose
global on that failure, without blocking their main operation. `send` **never**
recaptures: explicit `--context`/`--global` wins, otherwise it uses the inherited
value, otherwise global. Invalid explicit/inherited values are rejected.
Options include urgency, app name, expiration and replacement ID; summary/body
are literal subprocess arguments, never shell-evaluated.

Inventory of actual repository emitters and installed scripts:

| Emitter | Context policy and capture point |
| --- | --- |
| `scripts/pre-edit/pre-edit.sh` | Capture at processing start, before auto-editor; preserve an inherited recording snapshot. Completion/failure notifications and child operations share it. |
| `configs/obs/scripts-lua/obs-post-record{,-gaming}.lua` | Capture on `OBS_FRONTEND_EVENT_RECORDING_STARTED`, with a two-second time budget; pass that immutable value to the background stop hook. Missing start event/reload during recording uses global, never the stop-time session. |
| `configs/obs/scripts-sh/obs-post-record{,-gaming}.sh` | Accept the recording context as argument 2, export to pre-edit and use it for all notifications. No capture at recording stop. Without a supplied/inherited context, use global. |
| `scripts/safe-update/safe-update.sh` | System-wide operation; remains global through the existing untagged sender. No per-project ownership inferred. |
| `scripts/text-tools/{dictation-start,dictation-stop,text-insert}.sh` | Global desktop/input-tool status; remains untagged/global. Scoping an entire recording/transcription across separate invocations would require a separate policy/state change, not a stop-time guess. |
| `configs/kdenlive/scripts-sh/kdenlive-post-render.sh` | Existing completion-only hook lacks a render-start snapshot; remain global. Never capture the currently selected session at render completion. |
| `configs/pi/{photocraft,filmcraft}/launch_*_ai.sh` | Immediate launcher errors remain global. No FilmCraft render-completion integration is added. |
| Installed `~/.local/bin/obs-pre-edit`, `test-notification` | Legacy/local-only scripts absent from this repository; inventoried, left unmodified/global rather than silently replacing personal files. Current versioned OBS hooks are the integration targets above. |
| Pi [`session-notifications`](../pi/session-notifications/README.md) extension | `session-pi` passes confirmed launch context as environment and literal terminal command arguments. Capture once at `agent_start` (preserving that inherited origin), retain across retries/continuations, emit at `agent_settled`, not `agent_end`. No late active-context lookup; explicit global fallback, abort/reload suppression, distinct generic error title. Existing Pi requires idle `/reload`; new processes auto-load. |
| Pi `ctx.ui.notify` calls | In-terminal UI messages, not desktop D-Bus notifications; unchanged and not the completion emitter. |

No global notifications are silently reclassified as project notifications.
Beeper policy: keep untagged notifications global. A static inspection of the
installed `beeper-v4-bin` 4.3.123-1 package found application identity
`beeper.desktop` / `StartupWMClass=Beeper` and Electron notification creation,
but no discovered Agora session hint or reliable session correlation. Internal
account/conversation callbacks are not Session Manager UUIDs. No Beeper instance
was running, so actual D-Bus hints were **not** captured; desktop identity from
package metadata must not be presented as observed notification metadata. No
user profiles, messages or notification content were read. Do not infer a
session from app name, window placement, body, or the context active on arrival.
The existing unknown/global fallback needs no new runtime rule. A synthetic
Beeper regression test verifies global popup/no session unread indicator in
all foreground contexts. Future real-Beeper metadata inspection needs a
controlled non-sensitive notification and explicit observation scope; it is
optional and does not block script notification acceptance.
OBS script-only deployment uses `bash configs/obs/configure_obs.sh --scripts-only`:
it updates hooks without replacing OBS profiles/scenes or restarting the app.
System Lua files require administrator authorization; scripts already loaded by
OBS must be reloaded between recordings. Do not reload them during a recording
and lose its start snapshot. Until both new Lua and shell hooks are active,
untagged legacy invocations intentionally remain global.

Validation: `python3 configs/session-manager/test-agora-notify.py` runs the helper
with a fake status client/sender, changes session A to B during a fake processing
job, and verifies completion stays in A. It executes the real pre-edit/OBS shell
wrappers with fake editors and temporary media only, and both Lua callbacks with
a fake OBS API; no real recording, browser, editor, notification or session switch.

## State and presentation

The one history remains newest-first, at most 100 entries, in RAM only. Each entry retains native ID, local replacement key, timestamp, app name, summary, body and urgency, plus context, attribution source (`explicit`, `unattributed`, `invalid-hint`), orphan flag, `live`, `popup`, and `unread` flags. Context identity is captured at reception, never replaced by the currently selected session later.

- Current confirmed context: popup, no unread flag.
- Other session/neutral context: no popup, unread flag on its square border.
- Global/unknown/orphan: popup in any context, no session badge.
- Unconfirmed/stale graphical context: scoped popups are hidden by a presentation filter, without changing their stored popup/unread eligibility. No context is acknowledged and no outgoing foreground popup is marked unread until a different context is actually confirmed. A failed/cancelled switch can restore the already-visible popup without replaying a background backlog.
- Entering a confirmed context clears its unread flags without deleting history or replaying suppressed popups.
- Leaving a still-live foreground scoped popup hides it and retains attention for that context. Hiding does not call `dismiss()`/`expire()`.
- Expiry and client closure end the live popup but preserve unread history. History deletion/clear/100-entry eviction removes attention belonging only to removed entries and hides their popups, without forcibly closing application notifications.
- Replacing a live native ID updates one history entry, attribution, attention and timeout rather than duplicating it. Quickshell updates replacement properties rather than emitting its new-notification signal; their changes are coalesced in the store. **An entirely identical replacement emits no observable change on this Quickshell build and is treated idempotently:** it does not re-alert/re-mark an already acknowledged entry. No D-Bus traffic sniffer is added to bypass that limitation.

`SessionStrip.qml` checks each case's exact scoped context directly against retained unread entries, with a strict boolean and an explicit exclusion of the current context, and renders a red border independently from the current-session background. Global/unknown entries cannot feed a session badge, including a stale global unread flag; receiving global notifications must not clear genuine pending notifications of another session. The private-bus regression uses three sessions and verifies that global/untagged messages add no red borders while an existing B notification remains scoped only to B. The history view remains an all-context view and displays context and attention; its existing clear action is preserved, with an additional per-entry removal control. Opening history alone does not acknowledge every context or claim messages have been read in the originating application.

Compositor workspace/special-workspace events invalidate desktop confirmation and trigger a fresh shared snapshot. Periodic reads still cover external core changes; there is a bounded observation delay (normally up to two seconds). No scheme can atomically join an external core mutation, compositor transition and incoming D-Bus message. A pending/failed selection does not itself acknowledge a background context.

## Lifecycle and privacy

Per-notification lifetime timers are instantiated independently of popup visibility and screen count. Suppressed notifications therefore still expire and are not retained indefinitely as live objects to implement history. Preserve the existing 5-second default (10 seconds for critical), hover pause, actions, and close button. Positive sender timeout and continuous hover are bounded to five minutes; timers restart for observable replacements. Urgency does not override session scoping. Notification content is not written to disk. As before, Quickshell reload resets history and attention; core sessions/order persist.

## Installed end-to-end acceptance status

The helper/script tests, private-bus native notification tests and context-policy
regressions were rerun successfully. Installed policy/store/service/session
components and `agora-notify` were compared with the repository sources and
matched. Two non-sensitive messages labelled `Validation Agora` were emitted
through the installed helper into the real server: current-context (4 seconds)
and background-session (1 second). The server remained available and Quickshell
reported no runtime errors; windows, displayed workspace and core sessions were
unchanged. No shell reload, application launch, session switch or personal
notification inspection was performed.

**Visual acceptance is still pending:** the user must confirm the current popup,
background red border without popup, then select that context and confirm that
the border clears while the notification remains in history. Native/private-bus
tests prove the policy/lifecycle, not the live Wayland rendering or the user's
observed result. These synthetic messages do not validate Beeper-specific
metadata or a real recording/render completion.

## Validation and deployment

- `node configs/session-manager/test-notification-policy.js`: attribution matrix, foreground/background, neutral/global/unknown, orphan transitions, failed/unconfirmed switches, replacement, expiration, eviction, deletion and no replay.
- `python3 configs/session-manager/test-notification-store.py`: actual Quickshell server and actual `Notify`, replacement, expiry and `CloseNotification` calls on a **private D-Bus**, offscreen; fake session state and synthetic payloads. Tests actual red case borders and clearing without opening a real desktop window. It never connects to the user's notification bus or reads personal content.
- Existing session-service/menu/controller tests and Qt 6 QML lint remain required. Wayland popup rendering is a separate visual acceptance check; the offscreen test exercises the store and strip, not a PanelWindow.

The targeted installer copies policy/store/service together with the shell and session components. Changing watched files normally reloads Quickshell and resets in-memory history: obtain approval before live installation. Do not test live session switching/window moves as an implicit part of deployment. The stage-3 inventory above records the implemented script/Pi integrations; Beeper's emitter remains unchanged/global and FilmCraft rendering remains deferred.
