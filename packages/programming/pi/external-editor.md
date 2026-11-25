# Pi external editor — Mousepad

Pi's configured `externalEditor` takes precedence over VISUAL/EDITOR. A running Pi
started directly by the desktop may still inherit nvim from the compositor;
changing MIME associations/Fish startup does not override a configured Pi bridge.

`launch_external_editor.sh` is installed as `~/.local/bin/pi-external-editor`:
`mousepad --disable-server --opening-mode=window -- FILE`, literal argv, no shell
interpretation or terminal launcher. The installed Mousepad help documents both
options. Disabling the shared server creates a separate process, so Pi waits until
that editor instance closes before rereading its temporary prompt. No nonexistent
`--wait` flag, no global Mousepad setting/quit, no interaction with existing windows.
Save and close that editor window to return the text to Pi. Exit failures propagate.

The targeted installer:
```sh
python3 packages/programming/pi/install_external_editor.py --apply
```
backs up the previous bridge/global settings, merges only `externalEditor` to
`pi-external-editor` in `~/.pi/agent/settings.json`, and atomically publishes each
file, with a private phase journal. Unrelated settings are preserved. Symlinks,
nonregular/foreign targets, oversized settings and redirected ancestors fail closed.
The two publications are not a transaction; uncertain failure requires inspection,
not automatic rollback. Other project overrides are not scanned or rewritten.

Both normal `install_pi.sh` and the default-applications script's editor setup
(including `--editor-only`, when Pi is installed) call this same installer. The
normal/default text editor is Mousepad, not the optional Neovim desktop helper.

## Installed 2026-11-24

- Pi backup: `~/.local/state/linux-setup/pi-editor-upgrades/20261124T231147-0kqpc_oj`.
- Defaults backup: `default-editor-upgrades/20261124T221147-Rj87Ggko`.
- Linux Workflow `.pi/settings.json` already names `pi-external-editor`; it stays
  unchanged and now resolves the corrected bridge, even with stale nvim variables.
  An already-running Pi using that same command can use the updated executable
  without changing its cached command string or restarting the conversation.
- Targeted default-app installer run live. Bridge bytes/global preference and
  text/plain/text/markdown MIME results verified; other Pi fields/project settings/
  index unchanged. No real editor, model, conversation, terminal or reload launched.

`test_external_editor.py`: private HOME/all XDG, real installer, fake blocking
Mousepad; verifies settings merge, backup, idempotence, literal filename, stale
nvim environment ignored, wait-until-close, edited text, error propagation and
symlink refusal. Real XDG/Fish default-editor and file-manager regressions pass.
GUI text round-trip acceptance remains normal user activity, not an automated
personal-session test.
