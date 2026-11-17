# To do

## Multiple neutral sessions (v3 client transition)

References: [downstream behavior, isolated evidence and upgrade gate](configs/session-manager/neutral-v3-transition.md). The local core contract is owned by the separate Session Manager repository, not this task list.

- [x] Implement typed launch-source discovery/start, ordinary UUID-backed neutral instances in the menu/strip, source-aware application/Pi routing, UUID-scoped attention and explicit retention of the unowned/no-active desktop.
- [x] Test with a real isolated v3 daemon and fake compositor, private notification D-Bus, offscreen QML, existing controller/launcher regressions and temporary-HOME installation. Check all deployment entry points refuse v2 before writing and a mismatched known service executable fails closed.
- [x] Consume a reviewed published v3 core revision in the reproducible installer and retire the old v2 patches only against that matching revision. Verify the pinned build before live installation; do not bypass publication using the neighbouring development checkout.
- [x] After explicit deployment approval, back up private state, stop the known v2 owner/producers, install and explicitly migrate offline, install the compatible clients together and restart the known v3 service. Quickshell reload clears its in-memory notification history and requires approval. No automatic window adoption or movement.
- [ ] Obtain visual acceptance for independent Neutral starts/selections/scratchpads, guarded stop and UUID-specific notification attention after the coordinated upgrade. Keep the old unowned space reachable via Deselect session without presenting it as a neutral instance.

The approved live upgrade completed on 2026-11-17 from published core revision `9032a6aceffbe53053968dfa918371851e866fcd`, with original v2 files and private backups retained. Session projection, window/workspace placement and ownership metadata comparisons passed unchanged; Quickshell history reset was approved. Visual interaction acceptance remains manual.
