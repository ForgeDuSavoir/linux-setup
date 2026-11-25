#!/usr/bin/env python3
"""Source-only regression: retired desktop bindings, not Tab within menus."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
keys=(root/'configs/hypr/files/keybinds.lua').read_text()
assert not re.search(r'hl.bind\(mainMod.*?\+ (?:SHIFT \+ )?TAB"',keys)
for name in ['browser','pi','files','terminal','apps']:assert ' open-new '+name in keys
assert ' move-next' in keys and 'hl.bind("ALT + TAB"' in keys
qml=(root/'configs/quickshell/files/shell.qml').read_text()
assert '["SUPER+Tab",' not in qml and '["SUPER+Shift+Tab",' not in qml
assert 'Qt.Key_Tab' in (root/'configs/quickshell/files/SessionMenu.qml').read_text()
print('Retired Super+Tab/Shift+Tab bindings/help absent; Shift replacements, Alt+Tab and menu Tab retained.')
