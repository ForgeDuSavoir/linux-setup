# R7 — Native FilmCraft desktop-audio repair

Implemented, tested and independently installed on 2026-11-19.
Separate `filmcraft-desktop-audio` Cargo member; installed public name remains
`filmcraft-patch-desktop-audio RECORDING PROJECT`. No Python delegation, desktop
policy, core dependency, GUI automation or render-completion notifications.

## Preconditions and unchanged processing contract

**Caller must use a fresh project that is closed in FilmCraft.** This is a
precondition, not a claim that the helper detects/locks an open GUI document.
The advisory project-inode flock serializes cooperating repair helpers only.
Never invoke it on the live project to test this migration.

Resolve existing, distinct regular recording/project paths in the same directory.
Relative paths and symlinks resolve as before; JSON paths must be valid UTF-8.
Require exactly two stereo audio streams, four aligned nonempty audio tracks,
a video track, one sequence with Audio 1..4 names and initial per-track source
channels [0], [1], [2], [3]. All Audio 3 clips must reference the supplied recording.
Missing/misaligned/multi-recording projects fail before extraction, not get adopted
or normalized into the pre-edit layout.

Native JSON inspection and params use literal argv, no shell. Existing external
ffprobe/FFmpeg/FilmCraft waits/output capture remain unbounded, with no retries or
new media timeout. The four-step JSONL batch is written concurrently with output
capture, avoiding a pipe deadlock for large clip lists.

Exact arbitrary-precision rational arithmetic (pinned num-bigint 0.4.6,
num-rational 0.4.2, num-traits 0.2.19; R0-probed cached dependencies):

- Positive rational FPS = frame_rate.num / den.
- Ticks/frame = sequence duration / durationFrames.
- Required media end = max(sourceOut / ticks-per-frame / FPS) over Audio 3 cuts.
- hound 3.5.1 reads WAV frame count/sample rate, not a floating-point approximation.
  Extracted output must be valid stereo PCM16, nonempty and >=1000 bytes.
- FFmpeg selects **0:a:1**, the second audio stream, not microphone channel 1.
  `aresample=async=1:first_pts=0` materializes initial PTS offset as silence.
- Shortage >1/5 s fails; positive shortage <=1/5 s is padded with `apad` to
  required end + one frame, never time-stretched. Confirm padded WAV strictly
  exceeds required end.
- Only FFmpeg's `-t` boundary becomes decimal: exactly rounded nine places,
  ties-to-even from the rational. This avoids the old intermediate float rounding
  for extreme values. Human shortage display uses three decimal places.

Import the existing WAV into a temporary project, relink its basename relatively,
disable linked selection, replace only Audio 3 clips with keepSourceIn, delete
Audio 4, then set linked selection true. This preserves the fresh pre-edit default;
it does not discover/restore an arbitrary prior false preference.

Require all four JSONL results successful, complete replacement and no short/
sourceInClamped result. Afterward validate sequence durationFrames, unchanged video,
three surviving track IDs, each cut's clip/start/duration/sourceIn/**sourceOut**/link
and expected item. Raw microphone tracks must remain identical; desktop channels
must be [0,1] or the engine's null/default-all on the confirmed stereo media.
Require no missing media, relative WAV path and Audio 4 absent in raw JSON.
These added explicit postconditions fail closed rather than accepting collateral
changes that the old narrower check could miss.

## Publication / recovery — explicit R7 safety changes

This is **not an atomic transaction between project and WAV**. The old script's
exists-check followed by replace could overwrite a late WAV, and its failure
cleanup could unlink a concurrent public file. Those policies are deliberately
hardened here, separately from timing/algorithm parity.

1. Read/hold the original project with no-follow, nonblocking regular-file checks,
   snapshot bytes/identity/timestamps and take nonblocking advisory flock.
2. Create exclusive 0600 local temporary files, CLOEXEC. Mutating CLI steps may
   replace a temporary; refresh ownership only after those known operations.
   Subsequent read-only checks verify held identity/timestamps, not adopt new
   unvalidated content. Cleanup unlinks only a still-matching owned inode.
3. Publish the verified WAV via **hardlink no-replace**, fsync file/directory.
   Existing file, directory or even dangling symlink is refused, including a late
   arrival. Once published, never unlink/replace that public WAV on later failure.
4. Prepare/validate the patched project while the original pathname remains
   unchanged. Confirm public WAV identity/timestamps and original project identity,
   metadata and bytes again. An observed outside edit aborts, keeping that edit.
5. Preserve normal project permissions, fsync the candidate, then use Linux
   `renameat2(RENAME_EXCHANGE)` to swap project and candidate atomically.
   The displaced original stays at the reported local
   `.filmcraft-original-XXXXXX.fcproj` path, with its existing access permissions.
   That is a retained original, not a hidden-data registry or a private 0700
   installer backup. Unsupported exchange fails; never fall back to destructive
   replace.
6. Verify both exchanged identities and displaced bytes, then fsync directory.
   A late outside edit in the check/swap window or post-swap sync/error/lost reply
   yields an **uncertain publication error** and reports the retained version.
   The new public project may already be committed. Never automatically swap back,
   delete a public artifact or replay the operation.

Recovery states:

| Last stage | Possible visible state |
| --- | --- |
| Before WAV publication | Original project unchanged; no new public WAV |
| WAV published, project not exchanged | Original project unchanged; complete WAV retained |
| Project exchange occurred | Patched project + WAV; displaced original retained, even if exit is error |
| Forced interruption | Last completed stage plus possible local temporaries; inspect explicitly |

A later retry is intentionally blocked by the WAV/three-track layout. Inspect
project, WAV and reported original before any manual restore/removal; never remove
a file just because its name matches the WAV convention. Local filesystem atomic
operations are not a hostile-same-UID sandbox or GUI save lock. Other processes
holding old FDs can continue editing the retained inode; the closed-project
precondition remains essential. Abrupt termination/unconfirmed CLI replacements
may retain temporaries rather than risk deleting someone else's data.

The pre-edit consumer's old “project not patched” error is now an honest
“failed or uncertain publication; inspect project/WAV/backup” message. Its execution,
notification capture and editor-opening policy otherwise stay unchanged.

## Build, targeted deployment and installer rollback

```sh
python3 runtime/install_filmcraft_audio.py          # no-effect plan
python3 runtime/install_filmcraft_audio.py --apply
python3 runtime/install_filmcraft_audio.py --restore /absolute/private/backup
bash scripts/filmcraft-patch-desktop-audio/install_filmcraft-patch-desktop-audio.sh
```

The legacy no-argument setup route still applies; normal `scripts/install_scripts.sh`
cannot restore Python. Rust 1.96.1, pinned/locked dependencies, offline build,
ELF/version validation, private backup, atomic helper replacement/fsync, idempotence
and symlink/nonregular-target refusal. Restore is explicit, validates backup
ownership/privacy/hashes and refuses foreign later edits. No toolchain/package
installation, project/media/GUI action or service reload during install.
Legacy Python/R0 oracle remains historical only until R8 cleanup.

Live targeted helper backup:
`~/.local/state/linux-setup/filmcraft-audio-upgrades/20261119T192535-v3ii4wns`.
Version: `filmcraft-patch-desktop-audio 0.1.0 (Rust; exact stereo stream)`;
installed bytes equal release. A final validated ELF refresh (UTF-8/diagnostic
checks) has its own backup at
`~/.local/state/linux-setup/filmcraft-audio-upgrades/20261119T193058-kvpcc4px`.
The first backup contains Python, the latter the preceding Rust build. Restores
are guarded and one step at a time: to reach that original Python installation,
explicitly restore the latter backup then the first; never bypass the changed-target
check or perform that rollback automatically.

The sole pre-edit runtime change is the uncertainty diagnostic. Its targeted
installer now privately backs up and atomically replaces rather than truncate a
possibly running script descriptor. Applied separately, backup:
`~/.local/state/linux-setup/pre-edit-upgrades/r804STfD`.
No pre-edit job was run against real media. Before/after hashes/PIDs verify all
other helpers, core/desktop state, QML, Thunar/Pi settings, personal desktop entries
and core/Quickshell/FilmCraft/PhotoCraft processes unchanged. No notification,
session/window mutation, model/terminal/GUI launch or reload was used to deploy.

## Evidence

`bash runtime/check.sh` includes R1–R6 and:

- **87 Rust tests total** (57 desktop +14 thumbnail +16 audio): rational/time
  validation, exact rounding including >f64 precision, real flock, temporary
  identity, no-clobber WAV and retained-original exchange. fmt, strict Clippy,
  offline locked release pass.
- **57 full CLI differential scenarios** vs frozen R0 Python: normalized argv/
  JSONL, exact exit codes, timeline semantics and successful WAV samples match.
  Failure cleanup intentionally differs after WAV publication. Five stricter
  refusals and four concurrent WAV/project cases are checked separately.
- Test-only C interposition exercises actual private syscalls: failure before
  exchange, post-exchange fsync failure, lost success reply and edit in the last
  check/swap window. Original/concurrent bytes remain recoverable; no replay.
  Two harness timeouts terminate only their isolated fake-process group, proving
  no project publication before exchange. They add no production CLI deadline.
- **Actual FFmpeg + auto-editor XML + headless FilmCraft**, private HOME/XDG and
  generated two-second media: 30000/1001 FPS, two retained cuts, distinguishable
  stereo streams, desktop +100 ms PTS, padding, relative WAV and preserved original.
  Python/Rust produce exactly the same WAV and inspected timeline; leading silence
  and subsequent nonzero desktop samples are checked. No live GUI/recording.
  Auto-editor is a fixture-generation test dependency only, not an R7 runtime one.
- Syntax/path guards, cross-process advisory lock and unchanged literal pre-edit
  entry; standalone/normal helper installer, explicit restore (previous/absent),
  foreign edit/symlink refusal; pre-edit backup/idempotence and running old FD
  preservation in private HOME.
- Existing R1–R6, notification wrappers, 11 Pi extension tests and actual private
  D-Bus lifecycle remain green. No claim of FFmpeg speedup is made.

Normal-flow functional/aural acceptance remains separate. R1–R3 activation and
R8 coordinated cleanup/deployment/acceptance are not completed by this lot.
