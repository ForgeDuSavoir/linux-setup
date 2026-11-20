# linux-setup

Personal Linux setup and provisioning scripts for my desktop environments, applications, webapps, and workflow automation.

This repository is designed to:

* quickly reproduce my Linux environment on a new machine
* keep my setup modular and maintainable
* automate installation and configuration
* isolate webapps with dedicated browser profiles
* version my workflow and infrastructure decisions over time

The project is currently focused on:

* Arch Linux / CachyOS
* Wayland
* Hyprland
* Quickshell
* content creation workflow
* development tools
* productivity tooling
* self-hosted services integration

---

# Philosophy

The goal is not only to install applications, but to build:

* a coherent workflow
* reproducible environments
* isolated digital contexts
* low-friction tooling
* maintainable system configuration

The repository is structured to separate:

* installation
* configuration
* secrets/private data
* reusable shared logic

---

# Features

## Application installation

Each application has its own dedicated installation script.

Example:

```text
packages/media/obs/install_obs.sh
```

This allows:

* modularity
* maintainability
* independent testing
* easier debugging

---

## Development tools

Development tools that must be reproducibly available on the machine are installed through dedicated scripts in `packages/programming/`.

For the Fire Emblem: Fortune’s Weave tool:

- `packages/programming/pnpm/install_pnpm.sh` installs pnpm globally through npm when it is absent. It requires Node.js and npm to be available first and can be run repeatedly without reinstalling pnpm.
- `packages/programming/tauri/install_tauri_dependencies.sh` installs the Arch Linux/CachyOS system dependencies required to develop Tauri applications. It follows the dependency list published in the [Tauri prerequisites documentation](https://v2.tauri.app/start/prerequisites/) and uses `pacman --needed` so it can be rerun safely.

## Python-to-Rust runtime migration — R1–R7 installed

The remaining desktop/session and selected media helpers have an audited
[compatibility/caller map, architecture and reproducible reference baseline](tools/runtime-migration/README.md).
R0 includes frozen synthetic oracles, dependency/API feasibility and separate
startup/IPC/lock-wait measurements. The [R1 Rust controller](runtime/README.md)
now implements the workspace library/CLI with 21 Rust tests, 61 differential
scenarios and 19 actual-CLI tests. [R2 desktop/SUPER+Q](runtime/R2-desktop.md)
adds the typed v3 client and graphical actions, with 33 Rust tests total, 52 R2
differential scenarios, 12 CLI tests and a private-core scenario. These were initially validated
in isolation, before the R8 deployment. [R3 startup and pure admin](runtime/R3-startup.md)
complete the isolated desktop runtime cohort: 41 Rust tests total, 23 R3
startup scenarios, 11 CLI/admin cases and private-core relogin pass. Activation
is prepared by [R8 cohort deployment](runtime/R8-deployment.md), including installer/caller conversion,
private failure/restore tests and inactive generation staging. Live activation followed separate Quickshell RAM-history-reset approval on
2026-11-20; normal-flow user acceptance remains open. [R4 notifications](runtime/R4-notify.md)
is installed independently as the Rust helper, with compatible capture/send and
no shell reload. [R5 Pi routing](runtime/R5-pi.md) is also independently installed:
57 Rust tests total, 60 R5 differential cases and a private-core/stale-terminal-server
scenario pass. Fresh launch origin, explicit Agora and literal argv are preserved.
Pi and normal configuration installers now deploy validated Rust for both commands.
[R6 thumbnail](runtime/R6-thumbnail.md) is also independently installed: separate
media crate, exact versioned mask and no-overwrite publication; 71 Rust tests total,
73 differential cases and real FFmpeg/headless PhotoCraft with synthetic images
pass. Normal/targeted installers and explicit restore are tested. No active document
or personal media was touched; separate measurements do not prove a pipeline speedup.
[R7 FilmCraft desktop audio](runtime/R7-filmcraft.md) is independently installed too:
87 Rust tests total, 57 differential cases and real private rational-FPS/PTS/padding
integration pass. WAV no-clobber/retention and atomic project exchange with retained
original explicitly harden publication; no two-file transaction or auto-rollback.
Pre-edit now reports uncertain publication honestly. No live project/recording is
used for tests; final coordinated desktop activation/acceptance remains R8.
The native cohort is active on this machine, with matching Lua/QML and a complete
private journal. Immediate snapshots matched; later observed changes are recorded
without attributing their origin. See R8's current deployment record. Updated R4/R5 installers add guarded explicit restore
(including pinned-hash legacy backups) and deployed validated ELF refreshes only.
Quickshell's explicit Python controller calls are a later coordinated activation
gate, and the known close-handler wait is a separate functional fix.

## Session Manager

### Rust application launcher — deployed

`configs/session-manager/app-launcher/` now builds the contextual launcher in Rust
1.96.1. The installed command and SUPER+D / SUPER+B interfaces are unchanged;
Rofi remains the menu, Gio supplies metadata, and literal GTK/Gio commands launch
entries. No Python/PyGObject dependency for this component. The former Python
implementation is a frozen test fixture only. Version 0.2.1 records accepted
SUPER+D menu selections only (SUPER+B / --browser does not feed statistics) in private project-local history, or separate Neutral/unowned
state files. Frequency decays with a seven-day half-life; Rofi filters without
re-sorting. Context/entry revalidation, bounded atomic storage and exact local Git
exclusion protect scopes and data; invalid statistics never block a valid launch.
Installed without changing sessions/windows or restarting the shell/core; no
personal history was seeded for validation. See [contracts, build, tests and targeted install/restore](configs/session-manager/app-launcher/README.md).


### Fresh graphical login — installed for the next connection

Each new Hyprland instance (PC boot or logout/login) now forgets old open logical
sessions through the existing core API and creates exactly one Neutral-1 on a
fresh empty workspace before starting Quickshell. Reused compositor IDs never
inherit old UUID ownership. No project/application is restored or window moved.
Config/Quickshell/core reload within the same login does not reset sessions.
Current live sessions were explicitly deferred during installation; the shell,
core and notification history were left untouched. See [the startup policy,
installer and isolated tests](configs/session-manager/session-startup.md).

### Single workspaces — deployed

The desktop controller now removes the two-row column model: SUPER+S cycles
session workspaces, SUPER+Tab inserts/focuses a fresh empty workspace after an
occupied current one or returns to the preceding workspace when the current one is empty, SUPER+Shift+Tab isolates or joins the preceding occupied workspace without wrap,
and SUPER+Shift+S moves to the next existing workspace with wrap. Temporary
vertical animation switching remains removed. Existing real workspace
IDs/windows are preserved; explicit list order replaces ID arithmetic. Empty
workspaces are forgotten when left without stopping logical sessions.

Implementation and isolated tests passed; the coordinated deployment completed
on 2026-11-17 after explicit Quickshell history-reset approval. Real windows,
workspace IDs and monitor context were preserved, without restarting or mutating
the core service. Future changes must use the dedicated coordinated installer,
not a partial copy of the controller over an incompatible bar/helper. The later
Shift-action revision uses the coordinator’s movement-only mode: no Quickshell
restart/history reset; source help text waits for the next full QML deployment. See
[the single-workspace contract and installation gate](configs/hypr/workspace-navigation.md).


### Multiple neutral sessions — v3 deployed

The reviewed core source is published and pinned at
`9032a6aceffbe53053968dfa918371851e866fcd`. Compatible clients and the explicit
offline state migration were deployed together on 2026-11-17 after approval.
Session identities, opening order, active role and revision were preserved;
windows, workspace ownership and focused workspace/special context were unchanged.
No neutral instance or application was started to test the live upgrade.
Quickshell was restarted as approved, resetting its in-memory notification history.

The built-in Neutral source is an ordinary row in the common start list; its
UUID-backed instances share the normal menu/bar and have independently scoped
columns, scratchpads and attention. The old unowned/no-active desktop remains
separate and reachable through Deselect session. Pi uses the configured Agora root
for neutral instances; Firefox uses the eligible installed entry.

See [the transition contract, isolated evidence and deployment record](configs/session-manager/neutral-v3-transition.md).
The installers prevent mixing v2/v3 clients or replacing a known running daemon
in place. Future upgrades require an explicit controlled service stop.
Visual acceptance of user-driven neutral starts and notification interactions
remains manual; technical deployment checks were read-only.


`packages/productivity/session-manager/install_session_manager.sh` builds the reviewed, pinned
[`session-manager`](https://github.com/ForgeDuSavoir/session-manager) revision with vendored Rust
dependencies and installs the binary to `~/.local/bin/session-manager`. It obtains the
pinned source from GitHub into `~/.cache/linux-setup/session-manager`, never from an
Agora project checkout. It builds the immutable published revision with vendored
dependencies and no downstream patches; the former hidden-entry/deactivation/
Flatpak/opening-order fixes are upstream. The cache remains clean and builds use
an owned temporary tree. A known running user service must be stopped explicitly
before the binary can be replaced. Installation never migrates state or starts
a daemon automatically.
Rust 1.96.1 must already be installed. The separate
`configs/session-manager/configure_session_manager.sh` creates `config-v2.toml` only when
absent, targeting `${HOME}/Obsidian/Agora/2 Projects` by default, and enables a user
systemd service for the next login. The unit supplies stable, absolute HOME/XDG
paths and PATH (including XDG Flatpak application roots) even before the graphical
environment preloader runs; Session Manager otherwise rejects malformed startup
environment values. It preserves an existing configuration and does not
start/restart a running daemon or touch Hyprland/Quickshell. Set
`SESSION_MANAGER_PROJECT_SOURCE` to choose another existing directory before running it.
The full installer skips this configuration when the directory is absent. The same
configuration script installs `SUPER+ESC` (Quickshell session menu), `SUPER+D`
(contextual Rofi application menu), and `SUPER+B` (launch the current context's
`firefox.desktop` directly, without Rofi). Without a session, the installed Firefox
entry is used; missing/unavailable context data produces an error rather than
silently opening the wrong profile. `SUPER+A` opens the global Rofi drun application menu. `SUPER+P` directly opens Pi in the active
session's project using `session-pi`, without the former project picker or Yazi. The new menu uses `session-desktop` to start in a fresh empty column, return to
the retained unowned desktop without stopping running sessions, switch to the selected
session's columns, and refuse graphical stop while session windows/scratchpads
remain. Graphical stop also refuses the last open session; stopping the active one first selects/focuses the next survivor in opening order, wrapping, rather than returning to the unowned desktop. Explicit Deselect session and direct core CLI/API behavior are unchanged. A visible scratchpad is hidden before a menu action; its windows stay
open, and a nonempty session still cannot be stopped through the menu. The menu
closes after success and stays open to display an action error. In the menu,
open sessions receive keyboard focus first, with a fallback to projects if none
are open. Tab moves to the launch-source search field; typing there filters projects
only (not the built-in Neutral row or open sessions).
Up/Down select an item, Tab switches between projects and open sessions, and
Enter starts/switches the selected item; the selection scrolls into view.
The five scratchpad names are scoped by session UUID; pre-existing `session-*` scratchpads
remain reachable only in the unowned/no-active context. Multi-monitor
context changes fail closed until a focus policy is designed. Direct core
CLI/API stops still have no Hyprland window guard. Deployment on an already
running desktop must be coordinated with an upgraded daemon and existing
window/scratchpad verification. The targeted desktop installer refuses to run
while the known user service still executes an older binary; installing files
does not reload the UI or change focus.
The application bridge uses `gtk-launch` for installed desktop entries and `gio launch`
for project-local desktop files, never shell-evaluates their `Exec`. Each current
immediate project has a local `.session-manager/apps/firefox.desktop` overriding
`firefox.desktop` in its application list with `Name=Firefox` and
`GenericName=Web Browser`, without the project name. The application bridge uses
Gio through Rust bindings (system Gio/GLib libraries, no PyGObject) to read localized desktop
names, GenericName and Keywords from the selected installed/local entry. Like
Rofi drun, it renders the generic description in smaller italic parentheses;
keywords and comments are searchable through Rofi's hidden `meta` field. Text is
markup-escaped and IDs remain hidden; selection still uses the row index/ID.
Core application eligibility and project-specific launch commands are unchanged.
The downstream Flatpak patch permits exported desktop-file symlinks into the
same installation's matching app deployment, retaining XDG priorities, bounded
reads and validation; directory links and unrelated symlinks remain excluded.
Its stable UUID identifies a distinct
Firefox profile at `${XDG_DATA_HOME:-$HOME/.local/share}/agora-project-firefox/<UUID>/firefox-profile`.
`configure_session_manager.sh` installs the `agora-project-firefox` executable;
it creates the private profile directory on first launch and calls Firefox with
`--no-remote --profile`, as the webapp installers do. The UUID survives a
project-folder rename; browser profile data stays outside Agora and is not
versioned. A copied `.desktop` must receive a new UUID to avoid sharing a
profile. Without an active session, the installed/default Firefox entry remains
available. The service is **enabled but not started** by installation; the
current graphical session is not reloaded. See the [Session Manager usage guide](https://github.com/ForgeDuSavoir/session-manager/blob/9032a6aceffbe53053968dfa918371851e866fcd/docs/usage.md).

The retired `agora-project-launcher` Pi/Yazi project picker is removed by the
Rofi configuration installer. Its shared `project-launcher.rasi` theme remains
in use by the application menus, and the terminal helper remains in use by Pi.

### Shared session bar (stage 1)

`SessionService.qml` owns a single serialized, two-second read loop using
`session-desktop status`, preserving core opening order for both menu and strip.
The read-only status operation observes the focused workspace's owner under the
controller lock, compares it with the logical active session, and never initializes
or migrates workspace state or dispatches a compositor action. Unknown/error state
is not treated as neutral. Snapshots from before an action are discarded; a failed
read retains the last good list as stale and disables desktop confirmation.

`SessionStrip.qml` replaces the textual active-session label with a bounded,
horizontally scrollable row of square initials/number labels,
a distinct current-context background and ordinary numbered Neutral entries. No
synthetic no-active case is inserted; Deselect session remains a menu action. No hover tooltip
is used: an in-panel Qt tooltip could be clipped and interfere with clicks.
Full names remain available in the session menu. Each case is a real 26×26 Qt
button with full-square hover/click handling and explicit zero theme insets.
A clipped row plus wheel handler replaces the Flickable/scrollbar entirely, so
no scrolling layer can steal presses under the labels. Overflow still scrolls
with the mouse wheel/touchpad. The offscreen QtTest fixture
`configs/session-manager/tst_session_strip.qml` verifies corners/edges, every
integer coordinate in the lower half, wheel scrolling and disabled-state clicks,
at both 100% and 150% scale. Normal pending/stale refreshes during session
switches do not tint all borders or reduce opacity; red borders are reserved
for actual scoped notification attention. `visualContext` preserves the last
painted selection while confirmation is pending, but notification acknowledgement
never uses that visual cache. Unchanged session snapshots preserve the row model;
no periodic button recreation. Scoped popups are temporarily masked without
mutating their attention until the destination is confirmed. Errors remain
exposed by the session service/menu rather than flashing every session case. Clicks and menu
actions share the same `session-desktop` client and its existing safeguards.
Notification server/popups/history are unchanged in stage 1; no unread flag is
stored in the core or introduced in this strip yet.

The UI is implemented, tested offscreen and installed on the current machine
after explicit approval to reload Quickshell. Its existing in-memory notification
history resets on reload; visual interaction acceptance remains manual. To install only the client scripts while preserving the running
shell, use `SESSION_MANAGER_INSTALL_DESKTOP=0 bash configs/session-manager/configure_session_manager.sh`.
After approval, `bash configs/session-manager/install_desktop_integration.sh`
installs the new components and shell. It never kills Quickshell itself, but the
shell watches its files and normally reloads automatically.

Tests: `test-session-service.js` (fake process/state transitions),
`test-session-status.py` (mock core/compositor), `test-session-qml.py` (real
service/strip offscreen with a private runtime and fake executable), and
`test-session-menu-keyboard.js` (keyboard/search behavior). Use Qt 6 `qmllint`
for the menu/shell; an offscreen platform has no PanelWindow backend.

### Contextual notifications (stage 2)

The existing single notification server/history is now factored into
`NotificationStore.qml`, inherited by `NotificationService.qml`. The pure
`NotificationPolicy.js` classifies optional `x-agora-context` string hints and
controls popup eligibility and attention, without changing Session Manager.
The history still holds at most 100 entries in RAM. Session/neutral background
notifications mark their case red, and confirmed entry acknowledges without
replaying popups or clearing history. Global/unknown notifications still pop up.
The history view shows context and supports individual removal and clear-all.

See [the downstream contract](configs/session-manager/notification-context.md)
for lifecycle, orphan handling, replacement behavior and privacy constraints.
Untagged scripts and Beeper remain global. Stage 3's first two tasks add
`agora-notify` and capture propagation in the versioned pre-edit/OBS scripts;
A subsequent static audit of installed Beeper 4.3.123 found no reliable session
correlation; its untagged notifications deliberately remain global. No real
Beeper D-Bus notification was captured (no running instance), and no personal
message/profile was inspected. The synthetic policy regression covers this
fallback without introducing an application-name/session heuristic. Tests include actual
notification calls on a private D-Bus with offscreen Quickshell and synthetic
payloads; no personal notification bus/content is used.

Stage 2 files are implemented, tested and installed after approval to reload
Quickshell/reset its in-memory history. Startup guards handle temporary session
service unavailability. Two synthetic current/background notifications were sent
without changing sessions; visual acceptance of popup/border/entry behavior is
still manual. The targeted installer copies policy/store/service plus the shared
session components together.

### Script notification contexts (stage 3, first two tasks)

`configure_session_manager.sh` installs `agora-notify`. `agora-notify capture`
returns an inherited validated context or a confirmed desktop snapshot; it never
sends a notification. Export that value as `AGORA_NOTIFICATION_CONTEXT` before
starting asynchronous work. `agora-notify send` uses that frozen value, not the
session selected when work finishes; `--context` and `--global` provide explicit
modes. See the [script inventory and contract](configs/session-manager/notification-context.md).

`pre-edit` captures once before processing (or inherits OBS's snapshot). Both OBS
Lua hooks capture at recording start and pass the snapshot to their stop-time
shell hooks and pre-edit children. Capture failure/missing recording-start state
falls back explicitly to global; notification errors never fail the main job.

Deploy scripts only, without replacing OBS settings or restarting it:

```sh
bash scripts/pre-edit/install_pre-edit.sh
sudo -v  # required for system-installed OBS Lua files
bash configs/obs/configure_obs.sh --scripts-only
```

Then reload the Lua scripts in OBS **between recordings**, never during an active
recording. On the current machine helper/pre-edit/shell hooks are installed;
Lua installation was blocked by missing noninteractive sudo authorization and
remains a manual step. Until updated Lua is loaded, legacy stop hooks remain
global rather than guessing the recording's originating session. Test with
`python3 configs/session-manager/test-agora-notify.py`; this only uses temporary
media, fake editors/OBS and a fake notification sender.

### Guarded window / empty-session close

`SUPER+Q` closes only the confirmed visible window (ordinary workspace or visible
scratchpad) by explicit address with a compositor-side visibility/context guard.
Without a visible target, a wholly empty UUID session is stopped through the
same next-survivor policy as the menu. A blank workspace with windows elsewhere
in its session does not authorize stop; the last session remains protected.
The keypress workspace ID is retained so queued Q presses cannot close the
survivor. See [contract and isolated evidence](configs/hypr/workspace-navigation.md#guarded-superq-2026-11-19).
Deploy through the movement-only installer; no Quickshell reload is needed.

### Pi in the current session

Each immediate project's `.session-manager/apps/session-pi.desktop` runs
`session-pi`, installed by the Session Manager configuration script. It queries
the active session and current project list, then calls
`launch-terminal-command <project-directory> env AGORA_NOTIFICATION_CONTEXT=<captured-context> pi` with literal arguments. It opens
neither Rofi nor Yazi and does not fall back to Agora when AGENTS.md is absent.
With no active session it opens Pi at the user-configured `agora_root`; a missing
project or unavailable daemon still fails rather than silently choosing another
directory. There is no built-in Agora path. On first installation, supply it
explicitly:

```sh
AGORA_ROOT="/absolute/path/to/your/Agora" bash configs/session-manager/configure_session_manager.sh
```

This creates `${XDG_CONFIG_HOME:-$HOME/.config}/agora-workflow/config.toml`:

```toml
agora_root = "/absolute/path/to/your/Agora"
```

Subsequent installs preserve the file (even if AGORA_ROOT is supplied again).
Edit it directly to change the neutral directory; no daemon restart is needed.
A missing/invalid path produces a clear error rather than an implicit fallback.
The separate Session Manager `project_source` setting is unchanged.
The configuration script also installs `session-pi.desktop` globally with
`Exec=session-pi --agora`. Project-local entries of the same ID override it in
`SUPER+D`; without a session, the installed entry opens Agora directly.
The terminal helper and Pi must already be installed. `SUPER+P` invokes
`session-pi` directly and follows the same neutral-Agora/active-project policy.

Pi's global [completion extension](configs/pi/session-notifications/README.md)
uses `agent_settled`, not the premature low-level `agent_end`. It retains the
launch/start context across retries/continuations and sends one generic desktop
notification through `agora-notify`; aborted tasks/reloads do not notify and
errors have a distinct title. No prompt/answer or path is exposed. The existing
Quickshell popup/background-attention policy remains authoritative. Install only
this integration with `python3 configs/pi/session-notifications/install.py --apply`;
the normal Pi package installer delegates to it. New Pi processes auto-load it;
existing idle instances need explicit `/reload`. No shell restart/history reset.

## Webapps

Webapps are installed with:

* dedicated Firefox profiles
* isolated sessions
* custom desktop entries
* custom icons

Example:

```text
webapps/syncthing/
```

This enables:

* contextual separation
* isolated authentication
* separate history/cookies/extensions
* cleaner workflows

---

## Fonts

Custom fonts are installed automatically from:

```text
fonts/
```

---

# Secrets and Private Configuration

Private data is intentionally excluded from Git.

Examples:

* `.env`
* `.private`
* server addresses
* API keys
* network IDs

Public templates are provided with:

```text
.env.example
```

Example:

```env
ZEROTIER_NETWORK_ID=
```

---

# Requirements

Mainly designed for:

* CachyOS
* Hyprland

---

# Installation

Clone the repository:

```bash
git clone https://github.com/ForgeDuSavoir/linux-setup.git
cd linux-setup
```

Create your environment and private keys :

```bash
cp ./configs/hosts/hosts.private.example ./configs/hosts/hosts.private
nano ./configs/hosts/hosts.private
```

```bash
cp ./configs/zerotier/.env.example ./configs/zerotier/.env
nano ./configs/zerotier/.env
```

Run the main installer:

```bash
chmod +x ./install.sh
./install.sh
```

---

# Current Scope

The repository currently manages:

* desktop applications
* webapps
* theme
* hyprland configuration
* quickshell configuration
* Linux services
* personal workflow tooling

It may later expand toward:

* dotfiles
* Docker/self-hosted tooling
* automation workflows

---

# License

MIT License.
