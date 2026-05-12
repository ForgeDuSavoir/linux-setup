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
* Niri
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
applications/media/obs/install_obs.sh
```

This allows:

* modularity
* maintainability
* independent testing
* easier debugging

---

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

* Arch Linux
* CachyOS

Package managers currently used:

* pacman
* paru
* flatpak
* pipx

---

# Installation

Clone the repository:

```bash
git clone git@github.com:ForgeDuSavoir/linux-setup.git
cd linux-setup
chmod +x ./install.sh
```

Run the main installer:

```bash
./install.sh
```

---

# Current Scope

The repository currently manages:

* desktop applications
* webapps
* fonts
* Linux services
* personal workflow tooling

It may later expand toward:

* dotfiles
* Niri configuration
* Waybar configuration
* shell configuration
* Docker/self-hosted tooling
* automation workflows

---

# License

MIT License.
