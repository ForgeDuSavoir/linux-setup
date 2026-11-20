#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
tmp=$(mktemp -d -t app-scaling-test-XXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
export HOME="$tmp/home" APP_SCALING_SYSTEM_BIN_DIR="$tmp/system/bin"
export APP_SCALING_DESKTOP_SOURCE_DIR="$tmp/system/share/applications"
export XDG_STATE_HOME="$tmp/state" XDG_CACHE_HOME="$tmp/cache"
mkdir -p "$APP_SCALING_SYSTEM_BIN_DIR" "$APP_SCALING_DESKTOP_SOURCE_DIR"
mapfile -t apps < "$script_dir/../../scripts/artcraft-release-sync/artcraft-apps.list"
for app in "${apps[@]}" steam; do
    printf '#!/usr/bin/env bash\nprintf "%%s\\n" "${WINIT_X11_SCALE_FACTOR-unset}" "${STEAM_FORCE_DESKTOPUI_SCALING-unset}" "$@" > "$TEST_APP_LOG"\n' > "$APP_SCALING_SYSTEM_BIN_DIR/$app"
    chmod +x "$APP_SCALING_SYSTEM_BIN_DIR/$app"
    if [[ "$app" != steam ]]; then
        printf '[Desktop Entry]\nName=%s\nType=Application\nExec=%s %%F\n' "$app" "$app" > "$APP_SCALING_DESKTOP_SOURCE_DIR/ai.storyteller.$app.desktop"
    fi
done
cp /usr/share/applications/steam.desktop "$APP_SCALING_DESKTOP_SOURCE_DIR/steam.desktop"
cp /usr/share/applications/vlc.desktop "$APP_SCALING_DESKTOP_SOURCE_DIR/vlc.desktop"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$QT_QPA_PLATFORM" "$QT_SCALE_FACTOR" "$QT_AUTO_SCREEN_SCALE_FACTOR" "$QT_SCREEN_SCALE_FACTORS" "$@" > "$TEST_APP_LOG"\n' > "$APP_SCALING_SYSTEM_BIN_DIR/vlc"
chmod +x "$APP_SCALING_SYSTEM_BIN_DIR/vlc"
"$script_dir/install_app_scaling.sh"
checksums=$(sha256sum "$HOME"/.local/share/applications/*.desktop)
"$script_dir/install_app_scaling.sh"
[[ "$checksums" == "$(sha256sum "$HOME"/.local/share/applications/*.desktop)" ]]

export TEST_APP_LOG="$tmp/launch.log"
"$HOME/.local/bin/filmcraft" 'project with spaces.fcproj'
mapfile -t lines < "$TEST_APP_LOG"
[[ "${lines[0]}" == 1.5 && "${lines[1]}" == unset && "${lines[2]}" == 'project with spaces.fcproj' ]]
"$HOME/.local/bin/photocraft" 'document with spaces.pcraft'
mapfile -t lines < "$TEST_APP_LOG"
[[ "${lines[0]}" == 1.5 && "${lines[1]}" == unset && "${lines[2]}" == 'document with spaces.pcraft' ]]
"$HOME/.local/bin/steam" 'steam://open/games'
mapfile -t lines < "$TEST_APP_LOG"
[[ "${lines[0]}" == unset && "${lines[1]}" == 1.5 && "${lines[2]}" == 'steam://open/games' ]]

for app in "${apps[@]}"; do
    entry="$HOME/.local/share/applications/ai.storyteller.$app.desktop"
    rg -q '^Exec='"$HOME"'/.local/bin/'"$app"' %F$' "$entry"
    ! rg -q '^Exec=/usr/bin/' "$entry"
    desktop-file-validate "$entry"
done
entry="$HOME/.local/share/applications/steam.desktop"
[[ $(rg -c '^Exec=' "$entry") -eq $(rg -c '^Exec=' "$APP_SCALING_DESKTOP_SOURCE_DIR/steam.desktop") ]]
! rg -q '^Exec=/usr/bin/steam' "$entry"
rg -q '^Exec='"$HOME"'/.local/bin/steam steam://open/games$' "$entry"
rg -q '^MimeType=x-scheme-handler/steam;' "$entry"
desktop-file-validate "$entry"
# VLC overrides inherited automatic/per-screen factors; filenames stay literal.
QT_QPA_PLATFORM=wayland QT_SCALE_FACTOR=2 QT_AUTO_SCREEN_SCALE_FACTOR=1 QT_SCREEN_SCALE_FACTORS=2 \
    "$HOME/.local/bin/vlc" --started-from-file "clip with 'quotes' ; \$().mp4"
mapfile -t lines < "$TEST_APP_LOG"
[[ "${lines[0]}" == xcb && "${lines[1]}" == 1.5 && "${lines[2]}" == 0 && "${lines[3]}" == 1 ]]
[[ "${lines[4]}" == --started-from-file && "${lines[5]}" == "clip with 'quotes' ; \$().mp4" ]]
entry="$HOME/.local/share/applications/vlc.desktop"
rg -q '^Exec='"$HOME"'/.local/bin/vlc --started-from-file %U$' "$entry"
[[ $(rg '^MimeType=' "$entry") == "$(rg '^MimeType=' "$APP_SCALING_DESKTOP_SOURCE_DIR/vlc.desktop")" ]]
desktop-file-validate "$entry"
# A targeted installation doesn't rewrite other applications' desktop entries.
before=$(sha256sum "$HOME/.local/share/applications/steam.desktop" "$HOME/.local/share/applications/ai.storyteller.filmcraft.desktop")
"$script_dir/install_app_scaling.sh" --vlc-only
[[ "$before" == "$(sha256sum "$HOME/.local/share/applications/steam.desktop" "$HOME/.local/share/applications/ai.storyteller.filmcraft.desktop")" ]]
rm "$entry"; printf 'personal desktop\n' > "$entry"
if "$script_dir/install_app_scaling.sh" --vlc-only; then echo 'Personal override overwritten' >&2; exit 1; fi
[[ $(<"$entry") == 'personal desktop' ]]
echo '✓ Isolated scaling: ArtCraft/Steam unchanged, VLC Qt factors/literal paths/MIME, targeted install/idempotence/personal guard; no real apps.'
