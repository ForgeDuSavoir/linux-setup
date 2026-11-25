# Window animations — full popin opening and closing

## Current settings — installed 2026-11-25

Both windowsIn and windowsOut now use **popin** without a percentage: centered
full expansion on opening and centered contraction on closing. Hyprland clamps
the minimal geometry to 5×5 pixels; this is visually a point, not literal zero.
Both use speed 3 (~300 ms) and windowEase without overshoot. All other animation
and fade/opacity settings are unchanged.

Generation `670a661055243ec53aa8c608`, complete visuals-only backup
`desktop-cohort/20261125T121428-5oi6emd0`. Actual animation map confirms only
windowsIn/Out changed, curves unchanged. Actual-source Lua assertions, scratchpad/
session regressions and private visual apply/restore pass. Exact live state/PIDs/
QML/index/keybinds preserved, no real window open/close used to test and no
Quickshell restart. Normal visual acceptance remains user-driven.

## Initial 90% opening preview (historical)

Installed 2026-11-25 in `files/visuals.lua`: windowsIn uses popin 90%, speed 3
(about 300 ms), windowEase curve (0.16,1)/(0.3,1), no overshoot. Geometry grows
from 90% to final size around the final center. Closure/windowsMove/fade settings
and workspace/session/scratchpad transitions are unchanged. The existing fadeIn
inheritance is intentionally not shortened by this geometry-only preview.

Apply: `python3 runtime/install_desktop.py --apply --visuals-only`.
Generation `7fa36f6a592da2d43896c3f1`; complete backup
`desktop-cohort/20261125T120104-paqvrle7`. Actual animation query confirms only
windowsIn and the new curve changed. Lua config test, scratchpad/session animation
regressions and private visual apply/restore pass. The restore test now selects
its visual-mode backup by manifest instead of lexicographic random-suffix order.
Exact live core/desktop/metadata/marker, PIDs/index/QML/keybinds preserved; no real
window opened or session switched to test, no Quickshell restart.

## GNOME styles in the installed compositor

Exact Hyprland commit efb50993780079460b0cbed1363e2166a2de1d9f,
`src/desktop/view/animationControllers/WindowAnimationController.cpp`:
`gnome` and `gnomed` both call **the same applyGnomed implementation**. At opening,
the starting rectangle has full target width and zero height, centered vertically;
it expands upward/downward to full height. Closing, if configured with that style,
reverses it into a horizontal line at the center. No 3D cube or dock-directed
magic-lamp effect. Popin instead scales both width and height around the center.

A future right-entry experiment is not applied yet. The built-in `slide right`
starts one goal-window width to the right of its target position in this version,
not necessarily at the physical screen edge; that distinction matters for a
partially visible scroller column.
