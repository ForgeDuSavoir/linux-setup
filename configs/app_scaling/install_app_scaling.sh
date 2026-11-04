#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
app_list="$script_dir/../../scripts/artcraft-release-sync/artcraft-apps.list"
source_bin=${APP_SCALING_SYSTEM_BIN_DIR:-/usr/bin}
source_desktop=${APP_SCALING_DESKTOP_SOURCE_DIR:-/usr/share/applications}
bin_dir="$HOME/.local/bin"
desktop_dir="$HOME/.local/share/applications"
launcher="$bin_dir/scaled-app-launcher"

mapfile -t apps < "$app_list"
if (( ${#apps[@]} != 13 )); then
    echo "Expected 13 ArtCraft applications in $app_list" >&2
    exit 1
fi
apps+=(steam)
if [[ -e "$launcher" && ! -f "$launcher" ]]; then
    echo "Refusing to replace $launcher" >&2
    exit 1
fi
for app in "${apps[@]}"; do
    if [[ ! "$app" =~ ^[a-z]+$ || ! -x "$source_bin/$app" ]]; then
        echo "Missing or unexpected application: $source_bin/$app" >&2
        exit 1
    fi
    link="$bin_dir/$app"
    if [[ -e "$link" || -L "$link" ]] && [[ ! -L "$link" || "$(readlink -- "$link")" != scaled-app-launcher ]]; then
        echo "Refusing to replace existing launcher: $link" >&2
        exit 1
    fi
    if [[ "$app" != steam ]]; then
        entry="$source_desktop/ai.storyteller.$app.desktop"
        if [[ ! -f "$entry" ]] || ! grep -q "^Exec=$app " "$entry"; then
            echo "Unexpected ArtCraft desktop command: $entry" >&2
            exit 1
        fi
        override="$desktop_dir/ai.storyteller.$app.desktop"
        if [[ -e "$override" ]] && ! grep -q '^# Managed by linux-setup app_scaling$' "$override"; then
            echo "Refusing to replace existing ArtCraft override: $override" >&2
            exit 1
        fi
    fi
done
if [[ "$bin_dir" == *[[:space:]]* ]]; then
    echo "Desktop launcher path contains whitespace: $bin_dir" >&2
    exit 1
fi
if [[ ! -f "$source_desktop/steam.desktop" ]]; then
    echo 'Steam desktop entry not found' >&2
    exit 1
fi
if [[ -e "$desktop_dir/steam.desktop" ]] && ! grep -q '^# Managed by linux-setup app_scaling$' "$desktop_dir/steam.desktop"; then
    echo "Refusing to replace existing Steam override: $desktop_dir/steam.desktop" >&2
    exit 1
fi

mkdir -p "$bin_dir" "$desktop_dir"
install -m 0755 "$script_dir/launch_scaled_app.sh" "$launcher"
for app in "${apps[@]}"; do
    [[ -L "$bin_dir/$app" ]] || ln -s scaled-app-launcher "$bin_dir/$app"
done

# Copy current vendor entries and replace only their Exec commands. Explicit
# paths work from Thunar and menus even when their PATH lacks ~/.local/bin;
# retaining the IDs, MIME types, Steam URLs and actions also preserves Open With.
python3 - "$source_desktop" "$desktop_dir" "$bin_dir" "${apps[@]}" <<'PY'
import os
import pathlib
import re
import sys
import tempfile

source_dir, desktop_dir, bin_dir = map(pathlib.Path, sys.argv[1:4])
for app in sys.argv[4:]:
    name = 'steam.desktop' if app == 'steam' else f'ai.storyteller.{app}.desktop'
    source, target = source_dir / name, desktop_dir / name
    original = '/usr/bin/steam' if app == 'steam' else app
    launcher = str(bin_dir / app)
    content, count = re.subn(r'^Exec=' + re.escape(original) + r'(?=\s|$)',
                             lambda _: 'Exec=' + launcher, source.read_text(), flags=re.M)
    if count < 1 or not re.search(r'^\[Desktop Entry\]\n(?:.*\n)*?Exec=' + re.escape(launcher) + r'\b', content):
        raise SystemExit(f'Unexpected desktop entry: {source}')
    content = '# Managed by linux-setup app_scaling\n' + content
    fd, name = tempfile.mkstemp(prefix='.app-scaled-', suffix='.desktop', dir=desktop_dir)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(content)
        os.chmod(name, 0o644)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
PY
if command -v desktop-file-validate >/dev/null 2>&1; then
    for app in "${apps[@]}"; do
        if [[ "$app" == steam ]]; then
            entry="$desktop_dir/steam.desktop"
        else
            entry="$desktop_dir/ai.storyteller.$app.desktop"
        fi
        desktop-file-validate "$entry"
    done
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$desktop_dir" >/dev/null 2>&1 || true
fi
echo '✓ Steam UI and 13 ArtCraft apps: app-only 1.5 scaling installed (games unchanged).'
