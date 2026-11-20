# OBS configuration and project launchers

## Targeted project desktop migration (no settings/hardware changes)

```sh
bash configs/obs/configure_obs.sh --launchers-only
```

Installs the existing specialized entries as project-local overrides of the
standard `com.obsproject.Studio.desktop` ID:

| Project | Launch helper |
| --- | --- |
| Forge du Savoir YouTube | `~/.local/bin/obs-fds` |
| hQamonky YouTube | `~/.local/bin/obs-gaming` |

They live in each project's `.session-manager/apps/`, replacing generic OBS in
SUPER+D rather than adding another application. Original display names/icons are
preserved. Outside these projects/with Neutral, the standard installed OBS entry
remains unchanged. No core or shell reload required.

The targeted mode preserves installed helpers byte-for-byte, checks that they
exist and are executable, and never starts OBS/scrcpy, configures hardware,
requests sudo, updates Lua, replaces scenes/settings, or changes session/window
state. Local exclusions, other overrides and usage history are untouched.
Historical alias usage counters are not rewritten or merged into the standard ID.

## Reproducible installation

```sh
bash scripts/run-obs-fds/install_run-obs-fds.sh
bash scripts/run-obs-gaming/install_run-obs-gaming.sh
# Or both helpers and entries:
python3 configs/obs/install_project_launchers.py --apply
```

Normal custom-script installation already delegates to these installers; full OBS
configuration also includes them. Gaming now consistently installs `obs-gaming`,
using the actual `run-obs-gaming.sh` and `obs-gaming.desktop` source files, not
the previously nonexistent filename combination. Its legacy uninstaller uses
the same canonical helper name. Project overrides are user project configuration;
legacy helper uninstallers do not delete them: explicitly remove a project
override if returning that project to generic OBS.

These full commands install the **versioned** helpers. The FDS source already
configures a Logitech C922; this task does not change that source. The live
migration deliberately used desktop-only mode to retain the existing Android
camera launcher. No claim is made that hardware behavior was migrated or tested.

Project source: `--project-source ABSOLUTE_DIR`, else
`SESSION_MANAGER_PROJECT_SOURCE`, else the v2 Session Manager configuration's
`project_source`, otherwise `~/Obsidian/Agora/2 Projects`.
Only existing named projects receive overrides; missing projects are not created
and their global shortcuts are not removed. Use `--only fds|qmk` to restrict scope.

Templates remain versioned beside their helpers; they are no longer installed as
global profile-specific entries. Desktop Exec is literal absolute argv through
`/usr/bin/env --`, with Desktop escaping/percent handling, not a shell command.

## Migration guards and backups

After publishing each project override, remove only the exact known old global
`obs-fds.desktop` / `obs-gaming.desktop` (and matching historical
`run-obs-gaming.desktop` when present). Modified global entries or project
overrides require review, never silent overwrite/deletion. Symlinks,
foreign-owned/hardlinked targets and relative paths are refused.

Private before-file copies, mode/hash metadata and a phase journal are stored in
`${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/obs-project-launchers/`.
Publication is per-file atomic, **not** a multi-file transaction. On failure,
inspect the journal and backups before manually recovering; no automatic rollback.
Concurrent target changes are refused. Reinstallation of identical content is a
no-op. Existing installed helper differences are backed up by explicit full mode.

Live desktop-only migration: **2026-11-20**, backup
`~/.local/state/linux-setup/obs-project-launchers/20261120T133239-erhbc_j8`,
journal complete. Both global aliases removed and project targets verified;
second targeted run was a no-op. Installed helpers, generic OBS desktop,
previous profiles/exclusions/usage and Git index checked unchanged. No real
OBS/camera action was executed.

## Tests

```sh
python3 configs/obs/test_project_launchers.py
python3 configs/obs/test_project_launchers_core.py
```

Private HOME/fake helpers plus genuine Gio test literal complex paths, migration,
idempotence, preserved data, personal/relative/symlink guards, missing projects,
correct install names, injected publication failure and concurrent edits.
A genuine private core verifies one same-ID override per FDS/QMK project and
generic OBS in Neutral without launching applications or seeding usage.
Both suites are included in `runtime/check.sh`.

## Existing automation / full settings

`--scripts-only` still installs existing post-record hooks and can require sudo
for system Lua files; reload scripts only between recordings. The no-argument
`configure_obs.sh` still replaces OBS configuration with its existing backup
behavior. **Do not use full configuration merely to migrate menu entries.**
