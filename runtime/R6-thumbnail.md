# R6 — Native PhotoCraft thumbnail utility

Implemented, validated and installed independently on 2026-11-19.
Workspace member `photocraft-thumbnail` is separate from desktop tools and core.
The runtime is Rust, not a wrapper around the former Python implementation.
FFmpeg/ffprobe and the existing headless PhotoCraft CLI still do image processing.

## CLI and filesystem contract

`photocraft-thumbnail DIRECTORY [--top EXACT_FILENAME]` creates only
`DIRECTORY/miniature.pcraft`. Help exits 0, syntax errors 2, operational/validation
failure 1. New `--version` is read-only. Long-option abbreviations and literal
arguments are retained; diagnostics/help are not byte-for-byte argparse output.
No command string is shell-evaluated.

Expand `~`/named users, resolve the directory, then select exactly two immediate
files with suffix (case-insensitive) PNG/JPG/JPEG/WebP/TIF/TIFF/BMP. Subdirectories
and other files are ignored. As before, candidates must pass is-file; image
symlinks to regular files are refused, broken links/non-files are not candidates.
Any preexisting destination, including a dangling symlink or directory, is refused.
Source images are never written. Filename order uses the R0 Python baseline's
full Unicode 16.0 case folding plus exact-name tie-break; the embedded 1557-entry
table is reproducible with `tests/generate_casefold.py`. This is data, not a runtime
Python dependency. Non-UTF-8 names/arguments fail rather than lossy-convert.

Directory symlinks may resolve as before; this is not a policy forbidding linked
ancestors. Input checks are preflight checks, not an inode pin across external
programs. Supported command paths remain on PATH, with no new deadlines/output
limits or retries for potentially long media jobs. Stdin remains inherited
(FFmpeg still receives `-nostdin`); stdout/stderr are captured like the reference.

## Geometry, brightness and composition

For each image, ffprobe must return one stream with integer width/height:
width >=1920, divisible by 16, exact ratio 16:10. Checked integer arithmetic refuses
overflow. Crop height = width ×9/16; equal top/bottom offsets must be integers.
FFmpeg keeps the original center-crop/Lanczos/RGBA filter, output 1920×1080.
Examples: 2880×1800 → 2880×1620 at y90; 2304×1440 → 2304×1296 at y72.

Measure the prepared central rectangle `576:756:672:162`, resized to 32×32 area
gray; require exactly 1024 bytes and use their mean. Choose the darker image only
when the absolute gap is >=15 and dark <=0.75×bright. Ambiguity fails with a
`--top` suggestion; an exact explicit filename overrides ordering, not validation.
The selected image becomes the top pixel layer; the other is bottom. Names,
embedded pixels, canvas and editable layers remain equivalent to Python.
No YouTube export, GUI opening or notification is added.

PhotoCraft creates a private temporary document with literal JSON command params.
The ZIP/JSON layer then:

- Requires format v1 and 1920×1080, exactly bottom/top named layers without an
  existing mask, and the original Grayscale/U8/no-alpha mask format.
- Requires 40 unique coordinates covering 8×5 and 64-character lowercase hex
  tile references (36 unique compressed tiles in the reviewed asset).
- Attaches exactly the reference mask JSON to the top layer only, preserves
  unknown document fields/large integers, and copies **only** required reference
  tile bytes. Additional template image pixels are never copied.
- Rejects missing/corrupt/incompatible ZIP/JSON, bad references and differing
  data at an existing tile path. ZIP CRC is checked even for opaque source entries.
  Duplicate ZIP names are now explicitly refused, not ambiguously interpreted.
- Reads stored, deflate, Bzip2, LZMA and Zstandard archives. Actual PhotoCraft
  0.23.1 and the template use stored ZIP entries; all five Python-supported codecs
  are fixture-tested rather than silently narrowing the contract. ZIP 9.7.3 is
  pinned with explicit codecs; initial fetch prepared new locked dependencies,
  subsequent checks/build/install run offline. Zstandard's dependency builds C
  codec code, requiring the usual C build toolchain.
- Preserves opaque source compressed entries; rewritten manifest JSON is stored
  (ZIP library cannot encode LZMA), so archive bytes/compression are not promised
  identical. Document JSON, payload and mask semantics are the compatibility unit.
  Hash-name syntax/byte collision checks are **not** a new cryptographic validation
  of decompressed Zstandard tile payloads; installer verifies the full asset SHA.

The final headless `info --compact` must confirm top/bottom names, full
[0,0,1920,1080] bounds and mask only on top. Then hardlink the validated file to
the destination: atomic no-overwrite even if a concurrent file, symlink or
directory appeared. Never remove a concurrent destination or retry publication.

Temporary directories are private 0700, on the target filesystem. Handled failure
cleans only that operation's directory, checking directory identity before cleanup;
unrelated prefixed directories remain untouched. Published output is never removed
by cleanup. Forced termination can leave private temporaries; no signal-handler/
crash-recovery policy or guaranteed directory-fsync durability was added.

### Isolated reference quirk: R6-ZIP-001

The historical Python writer mutates source ZipInfo offsets while rewriting
manifest.json. With an identical preexisting mask tile *after* that manifest, its
later collision read can fail with “Truncated file header”; placing the same tile
before the manifest succeeds. This is reproduced separately, not counted as a
parity pass. Rust's independent source reads preserve the intended identical-data
acceptance for either order. This serialization/API difference is explicit; no
Python/oracle fix or wider algorithm change is bundled. Normal prepared RGBA
projects do not deliberately preload mask tiles. The unrelated desktop
CLOSE-WAIT-001 remains untouched.

Other malformed JSON integer/boolean/coercion accidents fail closed, including
non-v1 matching future schemas. Existing valid v1 documents are unchanged.

## Installation and restore

```sh
python3 runtime/install_thumbnail.py               # no-effect plan
python3 runtime/install_thumbnail.py --apply       # helper + unchanged mask only
python3 runtime/install_thumbnail.py --restore /absolute/private/backup
bash scripts/photocraft-thumbnail/install_photocraft-thumbnail.sh # legacy apply entry
```

Rust 1.96.1, locked offline build, ELF/version verification. Require external tools,
but never install packages, open a GUI or process images during installation.
Private backup/manifest, atomic individual replacements at 0755/0644, fsync,
idempotence and symlink/nonregular-target refusal. Mask-first deployment uses the
same reviewed mask as the previous helper; this is **not** a two-file transaction.
Explicit restore validates backup privacy/ownership/hashes and refuses foreign
later target edits; no automatic rollback or replay. Normal `install_scripts.sh`
still delegates to this entry and cannot restore Python. Thunar's public command
and existing custom actions are unchanged; no Thunar configuration reload needed.

Applied using only that installer. Private backup:
`~/.local/state/linux-setup/thumbnail-upgrades/20261119T185326-lc63001a`.
Installed version: `photocraft-thumbnail 0.1.0 (Rust; reference mask)`.
ELF equals release; adjacent asset equals the frozen reviewed asset. Before/after
hashes verify unchanged mask, Thunar actions, core/desktop state/helpers, Pi/QML
and core/Quickshell/PhotoCraft PIDs. No real user media, active document, window,
terminal, model, session, notification, restart or reload was used to deploy/test.
Legacy Python remains a historical reference only; final cleanup belongs to R8.

## Evidence and measurements

`bash runtime/check.sh` now includes:

- **71 Rust tests total** (57 desktop +14 thumbnail), fmt, strict Clippy and offline
  locked release binaries/examples.
- **73 differential CLI fixtures**, exact exit codes and normalized external argv,
  semantic ZIP/JSON/tile equality; five codecs; corrupt archives/CRC/JSON/mask,
  layer mismatch, input/output symlinks, bounds, ambiguity, tool errors and late
  publication races. Two duplicate-name refusals plus R6-ZIP-001 checked separately.
- Updated `test_photocraft-thumbnail.sh` actually exercises the Rust binary with
  real ffprobe/FFmpeg/headless PhotoCraft on generated PNGs: exact tile bytes,
  layer names/bounds/mask, dark-image ordering independent of alphabet, explicit
  ambiguity override, unchanged inputs and no overwrite.
- Standalone/normal installers and explicit restore in private HOME: plan,
  verified bytes/modes, private backup, idempotence, foreign edit/symlink refusal.
- R1–R5, Pi extension (11 cases), wrappers and actual private D-Bus regressions
  retained. No personal GUI/document is part of these suites.

`python3 runtime/tests/benchmark_thumbnail.py` writes
[synthetic results](tests/thumbnail-benchmark-results.json): 31 warm help-startup
samples Python **48.176 ms** / Rust **0.441 ms** median; 31 in-process mask ZIP
assemblies with private I/O **0.841 / 0.243 ms**. Real instrumented 3-sample pipeline
medians **593.735 / 636.657 ms**; native costs were measured separately per tool,
and generated document semantics matched across Python/Rust. These illustrative
pipeline samples **do not demonstrate an end-to-end speedup**. Timing wrappers add
Python startup overhead and external scheduling varies; no FFmpeg acceleration
or live latency promise, no subtraction of unrelated medians.

Normal-flow visual acceptance through Thunar/user media remains separate.
R1–R3 activation and R7–R8 remain open.
