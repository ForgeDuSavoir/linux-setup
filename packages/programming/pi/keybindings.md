# Pi word deletion shortcuts

Configured through native Pi actions, no plugin or terminal remapping:
- `tui.editor.deleteWordBackward`: Ctrl+Backspace plus Ctrl+W / Alt+Backspace.
- `tui.editor.deleteWordForward`: Ctrl+Delete plus Alt+D / Alt+Delete.

Word boundaries/within-word behavior are Pi's own editor implementation. These
are prompt-editor bindings, not changes to session-picker deletion shortcuts.
After installation run `/reload` in the active Pi; `/hotkeys` shows active bindings.
No terminal restart, Quickshell reload or synthetic typing in a real conversation.

```sh
python3 packages/programming/pi/install_keybindings.py --apply
```
The normal Pi installer calls the same targeted merger. It keeps unrelated user
bindings, supplies absent packaged defaults and unions the two word-action arrays
with existing personal aliases. It does not overwrite the full config as the old
normal installer did. Invalid JSON/types/redirected targets are refused. The old
file is privately backed up, rechecked before atomic publication; no auto rollback.

Installed 2026-11-24, backup
`~/.local/state/linux-setup/pi-keybinding-upgrades/20261124T232639-d1coon9z`.
Tests:
- `test_keybinding_install.py`: private HOME/all XDG roots, personal bindings/aliases,
  backup, repeat setup and symlink refusal.
- `test_word_keybindings.mjs`: actual installed Pi TUI keybinding manager and Editor,
  synthetic Kitty Ctrl+Backspace / CSI Ctrl+Delete, both directions and mid-word
  deletion, retained aliases. No model, live TTY or personal prompt involved.
