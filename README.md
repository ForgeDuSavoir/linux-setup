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

## Session Manager

`packages/productivity/session-manager/install_session_manager.sh` builds the reviewed, pinned
[`session-manager`](https://github.com/ForgeDuSavoir/session-manager) revision with vendored Rust
dependencies and installs the binary to `~/.local/bin/session-manager`. It obtains the
pinned source from GitHub into `~/.cache/linux-setup/session-manager`, never from an
Agora project checkout. Until the upstream changes are published, it applies the
versioned `hidden-entries-without-exec.patch` and `deactivate-session.patch` in a
temporary build tree so the GitHub cache stays clean and repeated installs remain
reproducible. The installed binary supports `session deactivate`; the running daemon
requires a separate controlled restart before it serves this new method.
Rust 1.96.1 must already be installed. The separate
`configs/session-manager/configure_session_manager.sh` creates `config-v2.toml` only when
absent, targeting `${HOME}/Obsidian/Agora/2 Projects` by default, and enables a user
systemd service for the next login. It preserves an existing configuration and does not
start/restart a running daemon or touch Hyprland/Quickshell. Set
`SESSION_MANAGER_PROJECT_SOURCE` to choose another existing directory before running it.
The full installer skips this configuration when the directory is absent. The same
configuration script installs `SUPER+ESC` (Quickshell session menu) and `SUPER+A`
(contextual Rofi application menu); `SUPER+D` and `SUPER+P` remain unchanged. The new menu uses `session-desktop` to start in a fresh empty column, return to
neutral workspaces without stopping running sessions, switch to the selected
session's columns, and refuse graphical stop while session windows/scratchpads
remain. A visible scratchpad is hidden before a menu action; its windows stay
open, and a nonempty session still cannot be stopped through the menu. The menu
closes after success and stays open to display an action error. The five
scratchpad names are scoped by session UUID; pre-existing `session-*` scratchpads
remain reachable in neutral context. Multi-monitor
context changes fail closed until a focus policy is designed. Direct core
CLI/API stops still have no Hyprland window guard. Deployment on an already
running desktop must be coordinated with an upgraded daemon and existing
window/scratchpad verification. The targeted desktop installer refuses to run
while the known user service still executes an older binary; installing files
does not reload the UI or change focus.
The application bridge uses `gtk-launch` for installed desktop entries and `gio launch`
for project-local desktop files, never shell-evaluates their `Exec`. The service is
**enabled but not started** by installation; the current graphical session is not
reloaded. See the [Session Manager usage guide](https://github.com/ForgeDuSavoir/session-manager/blob/bff500ff52a0fd57f68a938e4610dfe7e47009e1/docs/usage.md).

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
