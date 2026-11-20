#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
app_list="$script_dir/../../scripts/artcraft-release-sync/artcraft-apps.list"
source_bin=${APP_SCALING_SYSTEM_BIN_DIR:-/usr/bin}
source_desktop=${APP_SCALING_DESKTOP_SOURCE_DIR:-/usr/share/applications}
bin_dir="$HOME/.local/bin"
desktop_dir="$HOME/.local/share/applications"
launcher="$bin_dir/scaled-app-launcher"

if [[ $# -eq 1 && "$1" == --vlc-only ]]; then
    apps=(vlc)
elif [[ $# -eq 0 ]]; then
    mapfile -t apps < "$app_list"
    if (( ${#apps[@]} != 13 )); then
        echo "Expected 13 ArtCraft applications in $app_list" >&2
        exit 1
    fi
    apps+=(steam)
    [[ ! -x "$source_bin/vlc" ]] || apps+=(vlc)
else
    echo "Usage: $0 [--vlc-only]" >&2
    exit 2
fi
if [[ -L "$launcher" || ( -e "$launcher" && ! -f "$launcher" ) ]]; then
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
    if [[ "$app" != steam && "$app" != vlc ]]; then
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
for app in "${apps[@]}"; do
    if [[ "$app" == steam || "$app" == vlc ]]; then
        if [[ ! -f "$source_desktop/$app.desktop" ]] || ! grep -q "^Exec=/usr/bin/$app " "$source_desktop/$app.desktop"; then
            echo "Missing or unexpected desktop entry: $app" >&2; exit 1
        fi
        if [[ -L "$desktop_dir/$app.desktop" ]] || { [[ -e "$desktop_dir/$app.desktop" ]] && ! grep -q '^# Managed by linux-setup app_scaling$' "$desktop_dir/$app.desktop"; }; then
            echo "Refusing personal/symlinked override: $app" >&2; exit 1
        fi
    fi
done

for location in "$bin_dir" "$desktop_dir" "${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/app-scaling-upgrades"; do
    [[ "$location" == /* ]] || { echo "Installation/state paths must be absolute" >&2; exit 1; }
    while [[ "$location" != / ]]; do
        [[ ! -L "$location" ]] || { echo "Refusing a symlinked destination ancestor: $location" >&2; exit 1; }
        location="$(dirname -- "$location")"
    done
done
mkdir -p "$bin_dir" "$desktop_dir"
# Retain originals before updating the shared wrapper/selected entries. No GUI.
backup_root="${XDG_STATE_HOME:-$HOME/.local/state}/linux-setup/app-scaling-upgrades"
[[ "$backup_root" == /* ]] || { echo "XDG_STATE_HOME must be absolute" >&2; exit 1; }
backup=""
if [[ -f "$launcher" ]] && ! cmp -s "$script_dir/launch_scaled_app.sh" "$launcher"; then
    mkdir -p "$backup_root"
    backup="$(mktemp -d "$backup_root/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX")"
    chmod 700 "$backup"
    cp -p "$launcher" "$backup/scaled-app-launcher"
    for app in "${apps[@]}"; do
        if [[ "$app" == steam || "$app" == vlc ]]; then name="$app.desktop"; else name="ai.storyteller.$app.desktop"; fi
        [[ ! -f "$desktop_dir/$name" ]] || cp -p "$desktop_dir/$name" "$backup/$name"
    done
    echo "Private scaling backup: $backup"
fi
tmp="$(mktemp "$bin_dir/.scaled-launcher.XXXXXXXX")"
trap 'rm -f -- "$tmp"' EXIT
install -m 0755 "$script_dir/launch_scaled_app.sh" "$tmp"
mv -fT -- "$tmp" "$launcher"
trap - EXIT
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
    name = f'{app}.desktop' if app in ('steam', 'vlc') else f'ai.storyteller.{app}.desktop'
    source, target = source_dir / name, desktop_dir / name
    original = f'/usr/bin/{app}' if app in ('steam', 'vlc') else app
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
        if [[ "$app" == steam || "$app" == vlc ]]; then
            entry="$desktop_dir/$app.desktop"
        else
            entry="$desktop_dir/ai.storyteller.$app.desktop"
        fi
        desktop-file-validate "$entry"
    done
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$desktop_dir" >/dev/null 2>&1 || true
fi
echo "✓ Application-only scaling installed: ${apps[*]} (no app launched/restarted)."
