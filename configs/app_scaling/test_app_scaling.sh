#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
tmp=$(mktemp -d -t app-scaling-test-XXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
export HOME="$tmp/home" APP_SCALING_SYSTEM_BIN_DIR="$tmp/system/bin"
export APP_SCALING_DESKTOP_SOURCE_DIR="$tmp/system/share/applications"
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
echo '✓ Isolated scaling test: app-only environment, spaces, Steam desktop actions and idempotence.'
