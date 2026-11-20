# PhotoCraft thumbnails — native Rust

`photocraft-thumbnail DIRECTORY [--top EXACT_FILENAME]` takes exactly two immediate
PNG/JPG/JPEG/WebP/TIF/TIFF/BMP files and creates `miniature.pcraft` beside them.
It never changes source images or overwrites a preexisting/concurrent output.
Directory paths, image names and command arguments remain literal.

Each image must be exact 16:10, >=1920 pixels wide and center-croppable to integer
16:9. FFmpeg performs the original center crop and Lanczos/RGBA resize to 1920×1080.
Central 32×32 gray luminance selects the darker screenshot for the upper layer
only with a gap >=15 and dark <=75% of bright. Otherwise fail and request explicit
`--top`, naming exactly one input image.

The result has two editable embedded pixel layers, named after the inputs.
Only the exact reviewed Grayscale/U8 raster mask and its compressed tiles are
copied from `photocraft-thumbnail-mask.zip`; never reference-project image pixels.
No YouTube export or GUI opening is added. Final headless CLI inspection checks
size, bounds, ordering and mask before atomic no-overwrite hardlink publication.
Handled failures clean the operation's own private local temporary directory.

## Install / restore

```sh
bash scripts/photocraft-thumbnail/install_photocraft-thumbnail.sh  # existing apply route
python3 runtime/install_thumbnail.py                            # no-effect plan
python3 runtime/install_thumbnail.py --apply
python3 runtime/install_thumbnail.py --restore /absolute/private/backup
```

Build: pinned Rust 1.96.1, locked dependencies prepared once, offline thereafter;
usual C build toolchain for the ZIP Zstandard dependency. Runtime dependencies:
FFmpeg/ffprobe and `photocraft-cli`, **not Python**. Python remains installer/test
infrastructure. Binary/mask are installed at `~/.local/bin/`, privately backed up,
validated and individually atomically replaced. No toolchain/package install,
image processing or GUI reload occurs during installation.

`scripts/install_scripts.sh` still delegates to this installer, so future setup
does not restore Python. The old `photocraft-thumbnail.py` is a historical source/
test reference only; cleanup is R8.

## Thunar

Right-click **one directory**, choose **Créer une miniature PhotoCraft**.
The existing custom action passes the full folder through `launch-terminal-command`
and keeps a terminal open for progress/errors. It uses the configured terminal
(`xdg-terminal-exec`, otherwise `x-terminal-emulator`), not a hardcoded terminal.
For ambiguous images, run manually with `--top`. No action configuration change
or reload is required by the Rust replacement; unrelated custom actions stay intact.

## Validation

From repository root:

```sh
bash runtime/check.sh
bash scripts/photocraft-thumbnail/test_photocraft-thumbnail.sh
python3 runtime/tests/benchmark_thumbnail.py
```

73 executable/oracle scenarios plus real FFmpeg/PhotoCraft with synthetic PNGs
check exact mask/tile semantics, ordering, errors, cleanup and publication races.
Normal/corrupt ZIP codecs, installer/restore and malformed inputs are covered.
See [full R6 contract/evidence/compatibility notes](../../runtime/R6-thumbnail.md),
including explicit duplicate-name refusal and the legacy ZipInfo offset quirk.
Separate measurements do **not** demonstrate a full-pipeline speedup.
No active GUI document or personal media is used by these tests.
