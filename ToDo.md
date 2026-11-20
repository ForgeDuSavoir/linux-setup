# To do

- [x] Implement/test/stage [SUPER+F1 attention-first navigation](runtime/session-attention.md): exact bar-order leftmost pending, otherwise successor/wrap; fresh status, existing safe switch/acknowledgement, ignored repeats until confirmation, no new timer/retry/queue. Full runtime suite and genuine private QML/IPC/D-Bus tests pass. Inactive generation `a3c8cad3a5fab1959be14a9f`; live pointer/QML/keybinds unchanged.
- [x] Explicit Quickshell restart/RAM notification history loss approval obtained; SUPER+F1 activated via full coordinator, generation `a3c8cad3a5fab1959be14a9f`, backup `20261120T150245-r2l_slj8`, complete journal. Persisted core/desktop/state/marker checks pass, unique F1 binding and IPC method verified without invoking real navigation. Additional manual baseline failed before saving; coordinator baseline used instead.
- [ ] User normal-flow acceptance of SUPER+F1 pending-first priority, successor/wrap and rapid-press behavior.

- [x] Implement/install [SUPER+Tab confirmed-workspace menu](runtime/tab-launcher.md): explicit created outcome, readonly Hyprland acknowledgement, no timers/polling, lock released before exec, expected workspace/owner checked before Rofi/selection. Empty return/scratchpad behavior unchanged; only SUPER+D records history. Runtime/launcher regression suites pass; 14 real private CLI cases and Lua guards pass. Matching launcher + movement-only native cohort installed without QML reload or live workspace tests.
- [x] User-approved cleanup of the two disclosed synthetic `test.desktop` records completed under both launcher locks: private before/after backup and complete journal, exact targeted JSON removal without reserializing other entries/numbers, other counters verified unchanged, 0600 retained. Backup `tab-launcher-test-incident-cleanups/20261120T131207Z-3daug6ov`. Isolation/Tab non-counting already corrected; unavailable full pre-test baseline is not claimed restored.
- [ ] User normal-flow acceptance of SUPER+Tab menu, empty return, scratchpad dismissal and context changes while selecting.

- [x] Move specialized OBS FDS/QMK entries to project-local `com.obsproject.Studio.desktop` overrides; remove backed-up exact legacy global aliases, retain generic OBS elsewhere. Reproducible normal/targeted installation, canonical Gaming filenames and uninstaller name, literal Gio/private-core tests, personal/symlink/race/fault guards. Live `--launchers-only` preserves both installed helpers (FDS hardware behavior deliberately unchanged), OBS settings/other profiles/usage/index; second run is a no-op. [Details](configs/obs/README.md).

## Contextual Obsidian

- [x] Implement/test/install [session-obsidian](runtime/session-obsidian.md): exact registered project vault or Agora, explicit requests preserved, same menu ID/metadata/MIME/history, no CLI activation/registration/window transfer. 103 Rust tests total and complete runtime suite pass; 25 ELF cases, real private-core routing, genuine Gio dispatch, idempotence and guarded partial-install return. Registry/config/index and shell/core PIDs unchanged; observed active-session revision +1 is recorded without attribution or repair.
- [ ] User normal-flow Obsidian validation: cold start, already-running app, existing/nested vault; URI focus/reuse is not per-session window isolation. Register new vaults once via Obsidian itself.

## Contextual file manager

- [x] Implement/test/install [session-files](runtime/session-files.md) for SUPER+E: confirmed project root, HOME for Neutral/no session/unavailable or inconsistent context, standard opener/default preserved. No menu/MIME/desktop-entry/usage changes; 95 Rust tests, 28 CLI cases, real private-core routing and compatible four-to-five cohort expansion/restore pass. Movement-only live install preserves Quickshell/history/core/desktop/marker; no graphical test launch.

## Planned Python-to-Rust runtime migrations

- [x] Prepare/test [R8 cohort deployment](runtime/R8-deployment.md): immutable verified generations, atomic native pointer, first-handoff lock/journal/marker guard, partial-failure and explicit restore, converted normal/caller routes, offline provisioning and real private-core login acceptance. R4/R5 guarded restore/legacy pinned hash added; R6/R7 retained. Only staging (no current pointer) and validated R4/R5 ELF refreshes applied live; desktop/core/QML/PIDs/personal entries/index unchanged.
- [x] Separate Quickshell RAM-history-reset approval obtained; live cohort activated via coordinator, private complete journal and identical immediate snapshots. Native context confirmed; marker/non-cohort files/core-media PIDs preserved, shell restarted as authorized.
- [ ] Clarify later observed activity (one fewer window/session, revision +4), without inferring its origin or replaying/repairing state.
- [ ] Complete per-lot normal-flow visual/aural acceptance and final R8 closure.

- [x] Implement/install [R7 FilmCraft desktop audio](runtime/R7-filmcraft.md): native rational timing, second stereo stream/PTS/padding and preserved cuts/microphone/video. 87 Rust tests total, 57 differential scenarios, stricter guards, races and private syscall failures/lost reply pass, plus actual generated media/XML/headless CLI with identical reference WAV/timeline. Explicit no-clobber/retain WAV + project exchange/retained original, no two-file transaction/replay. Normal/targeted installer and restore tested; pre-edit uncertainty message atomically deployed/backed up. No personal recording/live project/GUI/session/reload touched.
- [ ] Normal-flow functional/aural R7 acceptance on a fresh closed project; inspect artifacts before any recovery, never auto-replay.

- [x] Implement/install [R6 PhotoCraft thumbnail](runtime/R6-thumbnail.md) independently: native separate media crate, exact two-image geometry/luminance/reference mask contract, five ZIP codecs and no-clobber hardlink publication. 71 Rust tests total, 73 differential cases and real headless tools on generated images pass. Normal/targeted installer/explicit restore verified in private HOME; live ELF-only update retains mask/Thunar/Pi/QML/core/desktop/PIDs. Separate startup/ZIP/native timings show no demonstrated pipeline speedup. Duplicate-ZIP refusal and legacy offset quirk R6-ZIP-001 are explicit.
- [ ] User normal-flow visual acceptance of the R6 Thunar entry; no active document/personal media is used by automated tests.

- [x] Implement/install [R5 Pi launcher](runtime/R5-pi.md) independently: native project/Neutral/unowned routing, explicit Agora, fresh coherent origin or global fallback, literal terminal env argv. 57 Rust tests total, 60 differential cases and actual private v3/R4/R2 plus stale-terminal-server simulation pass. Standalone/Pi/full-configuration installers deploy validated ELF without Python rollback. Live launcher-only backup/deployment preserves personal overrides/settings, core/desktop/PIDs, QML and notification helper; no real Pi/model/reload/session change used as a test.
- [ ] User normal-flow visual acceptance of R5 SUPER+P/global/project entries; existing Pi instances stay untouched.

- [x] Implement/install [R4 notification helper](runtime/R4-notify.md) independently: canonical context and capture-once/send-never-recapture contract, literal notify-send argv, same deadlines. 50 Rust tests total, 75 differential cases plus A→B, real wrappers, 11 Pi cases and actual private D-Bus pass. Pi/full configure routes install the pinned Rust ELF, never silently restore Python. Helper-only private backup/deployment preserves exact live core/desktop/PIDs and Pi/QML files; no live notification or reload used as a test.
- [ ] User normal-flow visual acceptance of R4 attribution; no shell reload/history reset is needed.

- [x] Implement isolated [R3 startup/admin](runtime/R3-startup.md): marker v1/signature, guarded new-login reset, private backups, one confirmed Neutral-1 and exec/recovery/no-replay rules; pure protocol-1 installer transformations without locks/IO/reset. 41 Rust tests total, 23 startup differential scenarios, 11 CLI/admin cases, private-core relogin and temporary ELF/defer flow pass. Runtime R1–R3 is available; production installer/caller conversion and activation remain R8.

- [x] Implement isolated [R2 desktop/SUPER+Q](runtime/R2-desktop.md) on R1's owning lock/library: typed v3 transport and 35 s deadline, all graphical CLI actions, read-only status and guarded close/menu survivor policy. 33 Rust tests total, 52 R2 differential cases, 12 CLI cases and real private-core integration pass; old Python/JS suites remain green. No live controller/helper/QML replacement; R3/R8 and activation approval remain pending.

- [x] Implement R1 in [runtime/](runtime/README.md): typed state/pure projection, all workspace actions, common flock and fd-relative atomic publication, guarded native allocation/moves and scratchpad behavior. 21 Rust tests, 61 frozen-reference differential cases, 19 real-CLI cases, strict fmt/Clippy/release offline and same-world measurements pass. No installed controller/desktop/QML change; R2/R3/R8 are still required before activation.

- [x] Complete R0 in [tools/runtime-migration](tools/runtime-migration/README.md): seven CLI contracts, 43 caller files/dynamic import map, independent workspace design and pure installer-admin interface, eight hash-frozen assets, eight smoke contracts, four pinned dependency API tests, offline locked fmt/Clippy/release and separate read-only/synthetic timings. Existing Python/private-core regressions pass; no runtime replacement or installation. QML interpreter calls require a future separately approved shell reload; CLOSE-WAIT-001 reproduced but not fixed.

- [ ] Execute the staged plan in [Linux Workflow](../Linux%20Workflow/Migration%20des%20scripts%20Python%20vers%20Rust/ToDo.md): workspace controller, desktop adapter and startup as a compatible group; notification helper and Pi launcher; then PhotoCraft thumbnail and FilmCraft desktop-audio utilities. Inventory/import removal, CLI/state parity, private tests, reproducible builds and targeted backup/rollback are explicit gates. R0 and isolated R1–R3 runtime implementations complete; R4 helper, R5 Pi launcher, R6 thumbnail and R7 FilmCraft audio independently installed. Desktop activation remains deferred to the compatible group and explicit QML/history approval. Keep the core independent; installers/test harnesses may remain Python. No automatic fix of the known close-handler wait is implied by a language port.

## Guarded SUPER+Q

- [x] Close only a confirmed visible window by explicit address in one guarded Lua evaluation; otherwise stop the empty UUID session through the existing menu fallback. Preserve last-session/all-workspaces/scratchpad guards and uncertainty policy; freeze keypress workspace to protect against queued Q acting on the survivor. 15 isolated Python/Lua cases and stop/navigation/install/private-core regressions pass; targeted movement-only deployment, no real close/switch as a test.
- [ ] User visual acceptance; shortcut-help source updated but its QML deployment remains deferred to an explicitly approved shell reload/history reset. See [contract](configs/hypr/workspace-navigation.md#guarded-superq-2026-11-19).

## Pi completion notifications

- [x] Implement/install the global settled-activity extension via the existing helper; capture once before work, preserve launcher-inherited origin, distinguish errors and suppress abort/reload/duplicate alerts. 11 extension tests, temporary-HOME installer, launcher/helper and real-private-core regressions pass. Targeted live file copies preserve settings/other extensions and exact core/desktop/shell/PIDs; no real task/model/notification used for validation.
- [ ] Existing Pi instances: explicit idle `/reload` or reopen, then user visual confirmation of current popup and background origin attention. Quickshell is not reloaded and its RAM history is preserved. See [contract](configs/pi/session-notifications/README.md).

## Rust contextual application launcher

- [x] Migrate the complete Python launcher to Rust 1.96.1 with locked Gio/serde dependencies; preserve menu/browser CLI, localized metadata/search/markup, overrides and literal GTK/Gio launching. Freeze Python as a test oracle, not a runtime dependency.
- [x] Validate 7 Cargo tests, 22 private-HOME executable cases, strict fmt/Clippy/release offline, the real private v3 core and actual targeted install/restore in temporary HOME. General configuration now builds/installs the Rust binary without a PyGObject preflight.
- [x] Deploy the executable only with a private backup and explicit restore path; compare exact core/desktop/shell snapshots and PIDs. No live application/menu/session mutation or notification reset used as a test.
- [ ] Obtain user visual acceptance of the migrated launcher.
- [x] Implement/deploy 0.2.0 project-local usage history: decaying weekly frequency, neutral/unowned separation, menu counting (browser contributions subsequently excluded in 0.2.1), pure-Rust confirmed context/entry revalidation, strict bounded JSON and fd-safe atomic writes, exact local Git exclusions without index changes. 28 Cargo tests, 31 private-HOME usage cases and 22 launcher regressions plus actual private core/temporary installer pass. Live core/desktop/shell/PIDs unchanged, no real history or Git exclusion seeded.
- [x] Deploy 0.2.1: --browser/SUPER+B bypasses all usage storage/exclusion work; project/neutral/unowned tests verify existing data unchanged and no new data/locks/rules. Menu counting remains active; 33 usage CLI cases pass. Preserve historical aggregate data, desktop/core/shell/PIDs and notification history.
- [ ] Obtain user visual acceptance of ranking/persistence and browser non-contribution; the first real menu selection populates statistics.

## Fresh Hyprland login

- [x] Initialize one ordinary Neutral-1 on a fresh UUID-owned workspace per new compositor signature; forget prior open instances via the core API before starting Quickshell. Reset desktop ID ownership without adopting windows; leave core persistence/restarts and project/profile files unchanged.
- [x] Validate 22 fake startup cases, a real private v3 daemon across first/repeated/new logins, fake Lua reload behavior and full/targeted installers in temporary HOME. Install for the next connection only, deferring the current instance; exact desktop/core/status and core/shell PIDs preserved, no notification reset.
- [ ] At the next user-chosen logout/login or PC reboot, verify exactly one Neutral-1, local workspace label 1 and no initial context-mismatch error. No actual logout or real-session reset is an automated test.

## Graphical stop survivor policy

- [x] Refuse the last open session; before stopping the active one select/focus the next surviving session in opening order with wrap. Preserve window guards, ownership during fallback, explicit deselection and unchanged direct core semantics.
- [x] Validate 18 fake core/desktop stop cases plus the real private v3 core, controller/status/session regressions and targeted temporary-HOME installer. Deploy helper/controller via movement-only mode; core/session/desktop and shell/PIDs unchanged, notification history preserved.
- [ ] Obtain user visual acceptance of active stop fallback and last-session error; no real session was stopped or switched for automated validation.

## Multiple neutral sessions (v3 client transition)

References: [downstream behavior, isolated evidence and upgrade gate](configs/session-manager/neutral-v3-transition.md). The local core contract is owned by the separate Session Manager repository, not this task list.

- [x] Implement typed launch-source discovery/start, ordinary UUID-backed neutral instances in the menu/strip, source-aware application/Pi routing, UUID-scoped attention and explicit retention of the unowned/no-active desktop.
- [x] Test with a real isolated v3 daemon and fake compositor, private notification D-Bus, offscreen QML, existing controller/launcher regressions and temporary-HOME installation. Check all deployment entry points refuse v2 before writing and a mismatched known service executable fails closed.
- [x] Consume a reviewed published v3 core revision in the reproducible installer and retire the old v2 patches only against that matching revision. Verify the pinned build before live installation; do not bypass publication using the neighbouring development checkout.
- [x] After explicit deployment approval, back up private state, stop the known v2 owner/producers, install and explicitly migrate offline, install the compatible clients together and restart the known v3 service. Quickshell reload clears its in-memory notification history and requires approval. No automatic window adoption or movement.
- [ ] Obtain visual acceptance for independent Neutral starts/selections/scratchpads, guarded stop and UUID-specific notification attention after the coordinated upgrade. Keep the old unowned space reachable via Deselect session without presenting it as a neutral instance.

The approved live upgrade completed on 2026-11-17 from published core revision `9032a6aceffbe53053968dfa918371851e866fcd`, with original v2 files and private backups retained. Session projection, window/workspace placement and ownership metadata comparisons passed unchanged; Quickshell history reset was approved. Visual interaction acceptance remains manual.

## Single-workspace navigation

- [x] Replace the two-row model with explicit ordered stable workspace IDs: SUPER+S cycle, SUPER+Tab fresh empty insertion, existing Shift+Tab isolation/move, no Shift+S or temporary vertical animation changes. Preserve session UUID ownership, scratchpads, stop guards and metadata-only legacy projection. See [contract/evidence](configs/hypr/workspace-navigation.md).
- [x] Validate controller, source/target races, cleanup, session integration, bar and targeted installation with fake native tools and temporary state; keep the staged personal-desktop deletions untouched.
- [x] Apply the coordinated navigation installer after explicit Quickshell history-reset approval; exact window/workspace/context comparison passed, core PID/session projection unchanged, live bindings and configuration verified. No live workspace creation/move was an automated deployment test.
- [ ] Obtain visual key-sequence acceptance for cycle, empty insertion/cleanup and isolation/move with the normal user workflow.

## Revised window movement

- [x] Separate Shift+Tab isolation/previous-occupied (no wrap) from Shift+S existing-next (wrap); preserve UUID scope/follow and delete emptied sources. Remove origin-based routing and retire old origin metadata.
- [x] Validate 32 controller cases and movement-only installation in a temporary HOME; deploy through the versioned movement-only mode with unchanged real windows/core/shell and no notification reset.
- [ ] At the next separately approved full Quickshell deployment/reload, install the updated shortcut-help labels. The live bindings already use the revised behavior.

## Tab create/return

- [x] Make SUPER+Tab create after an occupied workspace or return from an empty one to the previous existing same-owner workspace, without wrap/allocation when none exists. Forget the empty source and keep all Shift behavior unchanged.
- [x] Validate 36 controller tests and install via movement-only mode. Real desktop/core/shell snapshots remain unchanged; no live navigation test or notification reset.
