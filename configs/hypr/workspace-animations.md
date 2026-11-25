# Workspace animation — historical slidefadevert preview

Current policy now distinguishes [workspace/session/scratchpad transitions](../../runtime/context-animations.md): slidevert / slidefade / slidefadevert respectively. The preview record below is historical.

Installed 2026-11-25: ordinary `workspaces` style is `slidefadevert` in
`files/visuals.lua`. Duration parameter remains 5, curve wind, enabled true.
Special workspaces/scratchpads retain their existing fade/6/default settings;
window/layer/opacity/border animations are unchanged.

Targeted coordinated apply:
```sh
python3 runtime/install_desktop.py --apply --visuals-only
```
This reduced mode publishes only visuals.lua plus the existing managed native
links/pointer, reloads Hyprland, never copies/restarts QML or invokes startup.
It requires the already-native cohort, retains the existing backup/journal/state
checks and explicit restore support; does not broaden movement-only file scope.
Normal source/offline provisioning includes the same visuals asset.

Active generation `90209980f82372bcb6734940`, complete backup
`desktop-cohort/20261125T111758-5s2x1f4o`. Prior installed visual bytes matched source
except the requested style/comment change. Actual `hyprctl animations -j` confirms
exactly one changed field (workspaces.style); speed/curve/other animations unchanged.
Exact core/desktop/metadata/marker, QML/core/shell PIDs and index preserved.
No real workspace switch, app launch or session mutation used for testing.

Private actual-coordinator apply/restore test and existing cohort-mode regressions
pass, plus Lua syntax. `runtime/tests/test_visuals_mode.py` verifies no QML/bindings/
core/metadata/marker/synthetic-shell change. Visual preference is user acceptance,
not asserted by the configuration checks. Revert by choosing a new style or the
coordinator's explicit backup restore (no automatic session/runtime rollback).
