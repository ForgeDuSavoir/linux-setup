# Touchpad gestures

There are now **no compositor swipe/pinch shortcuts** in `files/inputs.lua`.
Three-finger horizontal workspace swipe was removed first on 2026-11-25 because
native traversal bypasses session-scoped navigation. The remaining three-finger
pinch inward (tile) and outward (float) shortcuts were then removed at user request.
Normal scrolling, natural-scroll/typing suppression/clickfinger settings remain.
Applications may implement their own gestures; this inventory concerns compositor
shortcuts, not a global suppression of every touchpad event.

Apply: `python3 runtime/install_desktop.py --apply --inputs-only`.
This reduced mode changes only inputs.lua plus existing managed native links/
generation pointer, reloads Hyprland and keeps QML/visuals/bindings untouched.
It requires an already-native cohort and uses the existing journal/restore/state
guards. Normal source/offline provisioning includes the same input asset.

Actual-source Lua recorder confirms zero gesture declarations and
unchanged touchpad settings. Generic private reduced-mode tests cover both visual
and input apply/restore without changing fake shell PID/core/state/marker/bindings.
Syntax validation passes. No actual user gesture, float operation or workspace
switch was performed to test installation.

Latest generation `b89a4a085abe20280cd78ba4`, complete backup
`desktop-cohort/20261125T142056-qkcmxmv4` (pinch removal). Initial swipe-only removal
was generation `cadc8400aa8a96ed1174d3a1`, backup
`desktop-cohort/20261125T140751-g_4rhwvu`. Prior live input bytes matched source
except the requested deletion. Installed input bytes/reload/config-error status
verified; exact core/desktop/state/marker/PIDs/index/QML/keybindings/visuals preserved.
No Quickshell restart/notification-history loss. Normal physical-swipe acceptance
remains user-driven; no live gesture-list query is available via standard hyprctl.
