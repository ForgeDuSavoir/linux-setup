#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TMP="$(mktemp -d -t photocraft-thumbnail-test-XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
DIR="$TMP/screenshots with spaces"
mkdir -p "$DIR"
python3 - "$DIR" <<'PY'
import pathlib, struct, sys, zlib
folder = pathlib.Path(sys.argv[1])
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
for name, rgb in [('Alpha image.png', (210, 35, 25)), ('Zeta image.png', (20, 45, 210))]:
    width, height = 2304, 1440
    scanline = b'\0' + bytes(rgb) * width
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(scanline * height)) + chunk(b'IEND', b'')
    (folder / name).write_bytes(data)
PY
before="$(sha256sum "$DIR"/*.png)"
"$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR"
[[ "$before" == "$(sha256sum "$DIR"/*.png)" ]]
python3 - "$DIR/miniature.pcraft" "$SCRIPT_DIR/photocraft-thumbnail-mask.zip" <<'PY'
import json, subprocess, sys, zipfile
file, template = sys.argv[1:]
info = json.loads(subprocess.check_output(['photocraft-cli','info',file,'--compact'], text=True))
assert (info['width'], info['height']) == (1920,1080), info
assert [(l['name'],l['bounds'],l['hasMask']) for l in info['layers']] == [
    ('Zeta image.png',[0,0,1920,1080],True),('Alpha image.png',[0,0,1920,1080],False)], info['layers']
with zipfile.ZipFile(file) as result,zipfile.ZipFile(template) as reference:
    mask = json.loads(reference.read('mask.json'))['mask']
    actual = json.loads(result.read('manifest.json'))['document']['layers'][-1]['mask']
    assert actual == mask  # Exact raster mask, not a newly approximated gradient.
    for tile in mask['surface']['tiles']:
        path = 'tiles/' + tile['hash'] + '.zst'
        assert result.read(path) == reference.read(path)
PY
hash="$(sha256sum "$DIR/miniature.pcraft" | cut -d' ' -f1)"
if "$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR" > "$TMP/error" 2>&1; then
    echo 'An existing project was overwritten' >&2; exit 1
fi
[[ "$hash" == "$(sha256sum "$DIR/miniature.pcraft" | cut -d' ' -f1)" ]]
rm "$DIR/miniature.pcraft"
cp "$DIR/Alpha image.png" "$DIR/Third image.png"
if "$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR" > "$TMP/error" 2>&1; then
    echo 'Three images were accepted' >&2; exit 1
fi
[[ ! -e "$DIR/miniature.pcraft" ]]
rm "$DIR/Third image.png"
# Dark image first alphabetically: the heuristic must not use filename order.
mv "$DIR/Alpha image.png" "$DIR/Zebra bright.png"
mv "$DIR/Zeta image.png" "$DIR/Alpha dark.png"
"$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR"
python3 - "$DIR/miniature.pcraft" <<'PY'
import json, subprocess, sys
info = json.loads(subprocess.check_output(['photocraft-cli', 'info', sys.argv[1], '--compact'], text=True))
assert [layer['name'] for layer in info['layers']] == ['Alpha dark.png', 'Zebra bright.png']
PY
rm "$DIR/miniature.pcraft"
# Identical images are ambiguous. Fail safely, then allow an explicit choice.
cp "$DIR/Zebra bright.png" "$DIR/Alpha dark.png"
if "$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR" > "$TMP/error" 2>&1; then
    echo 'An ambiguous pair was assigned an arbitrary order' >&2; exit 1
fi
[[ ! -e "$DIR/miniature.pcraft" ]]
grep -q -- '--top' "$TMP/error"
"$SCRIPT_DIR/photocraft-thumbnail.py" "$DIR" --top 'Alpha dark.png'
python3 - "$DIR/miniature.pcraft" <<'PY'
import json, subprocess, sys
info = json.loads(subprocess.check_output(['photocraft-cli', 'info', sys.argv[1], '--compact'], text=True))
assert [layer['name'] for layer in info['layers']] == ['Alpha dark.png', 'Zebra bright.png']
PY
if "$SCRIPT_DIR/photocraft-thumbnail.py" "$TMP/missing" > "$TMP/error" 2>&1; then
    echo 'Missing directory was accepted' >&2; exit 1
fi
echo '✓ PhotoCraft thumbnail tests passed (exact reference mask, ordering, fallback, two layers, no overwrite).'
