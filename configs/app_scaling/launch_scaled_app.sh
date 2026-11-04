#!/usr/bin/env bash
# Installed as ~/.local/bin/<app> for Steam and the 13 ArtCraft GUI programs.
set -euo pipefail

app=${0##*/}
source_dir=${APP_SCALING_SYSTEM_BIN_DIR:-/usr/bin}
case "$app" in
    steam)
        # Steam's UI setting; do not set GDK/QT/Winit scaling for its games.
        export STEAM_FORCE_DESKTOPUI_SCALING=1.5
        ;;
    photocraft|lightcraft|filmcraft|designcraft|vectorcraft|pdfcraft|effectcraft|wordcraft|deckcraft|gridcraft|cadcraft|soundcraft|figcraft)
        # Winit uses this only for its X11/XWayland backend.
        export WINIT_X11_SCALE_FACTOR=1.5
        ;;
    *)
        printf 'Unsupported scaled application: %s\n' "$app" >&2
        exit 2
        ;;
esac
exec "$source_dir/$app" "$@"
