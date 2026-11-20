# Session-aware Obsidian — installed menu integration

Native `session-obsidian` in `desktop-tools` changes only a no-argument launch
from the existing `obsidian.desktop` menu identity. No new menu entry, core API,
project registry, Obsidian plugin or CLI activation.

## Policy

1. Obtain a fresh confirmed project directory through the shared
   `files::project_directory` resolver (typed v3 status/catalogue, 2-second
   helper probes, final context/directory recheck).
2. Require a real directory named `.obsidian` directly at that project root.
3. Match that exact absolute root in the existing Obsidian vault registry,
   `${XDG_CONFIG_HOME:-$HOME/.config}/obsidian/obsidian.json`.
4. Open the unique registered 16-hex vault ID through
   `obsidian://open?vault=ID`.
5. Otherwise use the configured `agora_root` from
   `agora-workflow/config.toml`, with the same marker/exact registration checks.
   Neutral/no session, unknown/inconsistent/unavailable context, missing project
   marker or registration all select Agora.

Never infer a containing parent vault or select by project/vault basename.
Duplicate root registrations, invalid IDs and another vault name shadowing the
selected ID are refused. Project lookup errors fall back to Agora. If Agora
itself is unavailable/unregistered/ambiguous, or the global registry cannot be
read safely, fail with an explicit error instead of opening an arbitrary last vault.

The registry is readonly, regular/no-follow and size-bounded to 4 MiB. No notes,
plugins or vault configuration contents are read. No registration, creation,
registry/settings/history write, session switch, focus/move/close dispatcher,
ownership transfer or automatic retry is implemented. The initial shared resolver
check is best-effort, not an atomic context/filesystem/Obsidian transaction.

## Explicit requests and graphical launcher

URI/files arguments are authoritative and bypass all routing/config checks.
They are preserved as literal OS argv, not shell-parsed. The backend is the
absolute graphical launcher `/usr/bin/obsidian`, never PATH-resolved `obsidian`:
a later official CLI registration cannot redirect the call to the TUI.

Reserved launcher diagnostics: `--version`, `--help`, `--print-uri`.
The latter only resolves/prints the ID-based URI, without opening Obsidian.
Treat that URI as private local metadata.

## Desktop integration and deployment

```sh
bash configs/obsidian/configure_obsidian.sh
# equivalent: python3 runtime/install_obsidian.py --apply
python3 runtime/install_obsidian.py --restore /absolute/private/backup
```

Normal `configs/install_configs.sh` also calls the targeted script after the
Agora/Session Manager configuration. Standard Arch graphical Obsidian must be
installed. No Flatpak/custom-profile launcher support is claimed.

The installer builds pinned/locked/offline Rust, then adds:
- `~/.local/bin/session-obsidian` (ELF);
- `${XDG_DATA_HOME:-$HOME/.local/share}/applications/obsidian.desktop`,
  preserving the system entry's identity, localized names, icon, WMClass and MIME
  declaration, or an existing compatible local entry's metadata.

Only main Exec/TryExec/DBusActivatable behavior is adjusted. Custom Exec flags or
unrelated commands require review instead of silent replacement. Desktop Exec
uses `/usr/bin/env -- "ABSOLUTE_HELPER" %U`, without a shell. This also works
around Gio checking the executable before expanding literal `%%` in HOME paths.
The same `obsidian.desktop` identity keeps existing SUPER+D history keys;
the helper itself neither reads nor writes usage. Explicit URI handler requests
retain their original meaning. No MIME default reassignment or cache cleanup.

Publication is atomic **per file**, not a two-file transaction: helper first,
then desktop entry. Private lock, before/after payloads and a phase journal
support explicit return even after partial publication. No automatic rollback.
Return checks both current targets against recorded before/after states and
rejects foreign edits/corrupt payloads; restore desktop before helper.
Existing local metadata and permissions are backed up/restored. Reinstallation
is idempotent. Symlinked/foreign-owned/hardlinked targets are refused.

Live deployment 2026-11-20:
`~/.local/state/linux-setup/obsidian-upgrades/20261120T131634-931sutda`.
Agora registration and installed readonly URI resolution verified without
printing IDs or launching the GUI. Registry/workflow config, previous desktop
entries/project overrides, MIME/usage files and Git index unchanged; workspace
metadata/marker/desktop generation and shell/core PIDs unchanged.

**Observation, not attributed to installation:** between the private baseline and
post-check, active session changed, core revision +1 (same two sessions, only
their active flags changed), and monitor context changed. Other desktop fields
and workspace metadata were unchanged. No switch/move/repair/rollback was issued.
Do not describe the entire live snapshot as identical.

## Validation and remaining user acceptance

Complete `bash runtime/check.sh` passes: **103 Rust tests** (eight new Obsidian
invariants), fmt/strict Clippy/offline release and all existing runtime suites.
- `tests/test_obsidian.py`: 25 real ELF resolution cases on synthetic projects/
  registry, project/Agora/error paths, timeout, malformed/oversized/symlink
  registry, marker/registration absence, explicit bypass and literal backend
  launch/failure with a fake executable. Registry unchanged, no GUI.
- `tests/test_obsidian_private_core.py`: real private v3 daemon and Rust desktop
  status, synthetic native tools, exact project, marker/registration absence,
  Neutral/no session and spatial mismatch; core/metadata/registry unchanged.
- `tests/test_obsidian_install.py`: fake ELF and genuine Gio desktop dispatch
  with complex HOME names and %U arguments; idempotence, identity/metadata/MIME,
  personal edits/Exec refusal, partial publication and guarded return.

The actual graphical Obsidian behavior remains user normal-flow acceptance:
cold start, app already running, same vault already open, and nested project
vaults. URI requests can focus/reuse an existing window in another logical session;
there is no per-session Obsidian window isolation. Cold-start restoration of
other vault windows is controlled by Obsidian, not this helper. A new vault must
first be registered through Obsidian's own “Open folder as vault” UI; merely
adding a .obsidian directory does not register it.

Official sources: [URI](https://help.obsidian.md/uri),
[CLI](https://help.obsidian.md/cli). Installed Arch package inspected during
analysis: `obsidian 1.13.7-2`; URI dispatch accepts known IDs/names and chooses a
known containing vault for path-based requests. This implementation intentionally
avoids ancestor matching and does not edit the private registry format.
