# Context shortcuts: Y / O / physical sleep key

## Policy

- SUPER+Y: `session-app-launcher --youtube`, same confirmed context/catalog/entry
  integrity checks as the browser. Prefer exactly one eligible **project** override
  named youtube.desktop / youtube-fds.desktop / youtube-qmk.desktop. Ambiguous
  overrides refuse rather than choose a foreign account. Without a project override,
  send https://www.youtube.com/ to the contextual Firefox entry through GIO URI
  launching; preserve literal Exec/profile/field-code handling. No Rofi/history IO.
- SUPER+O: existing `session-obsidian`, exact registered project vault or Agora.
- XF86Sleep (user-observed Fn+F1): existing Control Center IPC, **only** when live
  logind properties HandleSuspendKey and HandleSuspendKeyLongPress both say ignore.
  Lua uses bounded readonly busctl probes at config load. Missing/error/other mode
  leaves this key unbound; no unsafe simultaneous suspend/Control Center action.

## Privileged setup (completed; effective state verified 2026-11-25)

At initial deployment logind exposed suspend / hibernate and no noninteractive
sudo credentials were available, so Sleep was deliberately left inactive. Following
the user's setup, both live properties now report ignore and the unique XF86Sleep
binding is active (verified during the 2026-11-25 help refresh). Fresh setup uses
the normal logind installer; the targeted existing-installation command is below.
Run as the graphical user (sudo prompts in that user's terminal):
```sh
sudo bash "/home/will/Obsidian/Agora/2 Projects/linux-setup/configs/logind/configure_sleep_key.sh" && hyprctl reload
```
The targeted script installs only its logind drop-in, privately backs up any prior
file, reloads (never restarts) logind, and verifies effective short/long-press
properties. Other drop-ins/lid policy remain unchanged. The normal logind setup
also calls it; `configure_logind.sh --sleep-key-only` is a targeted route.
If another drop-in overrides ignore, fail and inspect; do not activate the binding.
Explicit suspend from menus remains available; this disables only the key action.

## Tests and deployment

Six private launcher/GIO cases: neutral/project URI literal/profile preservation,
project YouTube override, ambiguity, unavailable browser and unconfirmed context;
no real browser/profile/window. Thirty launcher Rust tests/strict Clippy and 33
history regressions pass. Actual Lua gate tested with effective ignore/suspend/
hibernate/invalid responses, plus syntax validation. Root logind mutation was not
performed or simulated as if accepted; privileged effective verification is pending.

Generation `6903aff5c9b5204f8628b5ba`, complete backup
`desktop-cohort/20261125T103048-qvbldc2c`; launcher backup
`app-launcher-upgrades/20261125T093047-6D0FXWpI`. Unique O/Y bindings and gated absence
of Sleep verified live; exact snapshots/state/marker/PIDs/index/QML preserved.
No apps/vaults/profiles opened to test. Help rows were subsequently deployed with explicit Quickshell restart/RAM-history
approval, generation `06309a3218d7b290b49b5743`, complete backup
`desktop-cohort/20261125T105635-x1uv6bpa`. Exact state/core PID/index/helpers preserved;
only the authorized shell PID changed.
