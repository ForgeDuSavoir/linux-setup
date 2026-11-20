# FilmCraft desktop-audio repair — Rust

`filmcraft-patch-desktop-audio RECORDING PROJECT` repairs a **fresh, closed**
pre-edit FilmCraft project beside its OBS recording. It requires exactly two
stereo streams and the four aligned Audio 1..4 import tracks. It does not detect
or close a GUI project; do not run it on an open/active editing project.

Extract stream `0:a:1` with PTS offset materialized as silence, retain exact
rational cut timing, replace only Audio 3 with stereo desktop audio, remove Audio 4,
and preserve video/microphone/cuts/links. Small final audio shortages <=200 ms get
silence plus one frame of reserve; larger shortages fail. No render notification,
GUI opening or model integration is included.

## Safety / recovery

No transaction is claimed across WAV and project. WAV publication is no-clobber.
After WAV publication, later failure **retains** it. Project publication atomically
exchanges the validated candidate and original; the displaced original is kept at
the reported local `.filmcraft-original-*.fcproj` path, even on uncertain failure.

A failed command may therefore mean a project was already published. Inspect
project, WAV and retained version before manual recovery. Never automatically
retry, overwrite a preexisting WAV or remove a public file merely by its name.
The closed-project precondition and advisory-lock limitations remain important.
See [full contract, failure-state table and compatibility changes](../../runtime/R7-filmcraft.md).

## Build / targeted install

```sh
python3 runtime/install_filmcraft_audio.py              # plan only
python3 runtime/install_filmcraft_audio.py --apply
python3 runtime/install_filmcraft_audio.py --restore /absolute/private/backup
bash scripts/filmcraft-patch-desktop-audio/install_filmcraft-patch-desktop-audio.sh
```

The existing no-argument setup route applies and is still called by
`scripts/install_scripts.sh`. Pinned Rust 1.96.1 / locked offline build, private
backup and atomic helper update. Runtime dependencies: ffprobe, FFmpeg,
`filmcraft-cli` and Linux/filesystem exchange support. Python is installer/test
infrastructure only. Legacy `.py` remains historical until R8; normal setup does
not install it.

Pre-edit retains the same literal helper call. Its error message now acknowledges
uncertain publication instead of claiming the project must be unchanged.
Install that message-only wrapper update with `scripts/pre-edit/install_pre-edit.sh`;
it backs up and atomically replaces without truncating a running descriptor.

## Validation

`bash runtime/check.sh`: Rust invariants, 57 differential CLI scenarios, races,
private syscall faults/timeouts, installer/restore, real generated two-stream
recording + auto-editor XML + headless FilmCraft. The real fixture verifies rational
FPS, cuts, +100 ms desktop PTS, padding and exact reference WAV/timeline semantics.
No active project, personal recording or GUI is used.
