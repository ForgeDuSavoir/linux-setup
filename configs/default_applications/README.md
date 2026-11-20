# Default applications

`configure_default_applications.sh` configures the standard browser, editor,
terminal and media defaults. To configure **only** the directory/file-manager
associations, without launching/quitting Thunar or changing its preferences/actions:

```sh
bash configs/default_applications/configure_default_applications.sh --file-manager-only
```

This narrow mode requires installed Thunar and xdg-mime, sets/checks
`thunar.desktop` for `inode/directory` and the existing saved-search association,
and checks GIO's directory handler when available. Already-correct defaults are
not rewritten. It never runs the full browser/editor/terminal setup or `thunar -q`.

Hyprland **SUPER+E** calls native `session-files`, which opens the confirmed session
project root through `xdg-open`. Neutral/no session, unavailable project or any
unknown/inconsistent context falls back to HOME. Future directory-handler changes
are respected; Thunar remains the setup default. The application menu and .desktop
entries are unchanged. [Routing, installation and tests](../../runtime/session-files.md).

Deploy the changed binding with the existing native coordinator:

```sh
python3 runtime/install_desktop.py --apply --movement-only
```

This requires an already native cohort, reloads Hyprland only and does not write
watched QML or restart Quickshell. Do not use full Thunar/default-app configuration
just to update this shortcut.

Test: `python3 configs/default_applications/test_file_manager.py`.
Private fake tools verify narrow/idempotent defaults and the actual native Lua
binding. Runtime tests additionally cover project/HOME routing, literal paths
with spaces/quotes and an alternate default handler.
No graphical file manager is launched as a test.
