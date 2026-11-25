#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

configure_file_manager() {
    command -v thunar >/dev/null || { echo 'Thunar must be installed first.' >&2; return 1; }
    command -v xdg-mime >/dev/null || { echo 'xdg-mime is required.' >&2; return 1; }
    local mime info
    for mime in inode/directory application/x-gnome-saved-search; do
        if [[ "$(xdg-mime query default "$mime")" != thunar.desktop ]]; then
            xdg-mime default thunar.desktop "$mime"
        fi
        [[ "$(xdg-mime query default "$mime")" == thunar.desktop ]] || {
            echo "Could not set Thunar as default for $mime." >&2; return 1;
        }
    done
    if command -v gio >/dev/null 2>&1; then
        info="$(LC_ALL=C gio mime inode/directory)"
        if [[ "${info%%$'\n'*}" != *": thunar.desktop" ]]; then
            gio mime inode/directory thunar.desktop
            info="$(LC_ALL=C gio mime inode/directory)"
            [[ "${info%%$'\n'*}" == *": thunar.desktop" ]] || {
                echo 'GIO directory default does not resolve to Thunar.' >&2; return 1;
            }
        fi
    fi
    echo '✓ Default file manager: Thunar (inode/directory).'
}

configure_text_editor() {
    command -v mousepad >/dev/null || { echo 'Mousepad must be installed first.' >&2; return 1; }
    command -v xdg-mime >/dev/null || return 1
    local config="${XDG_CONFIG_HOME:-${HOME}/.config}"
    local state="${XDG_STATE_HOME:-${HOME}/.local/state}"
    [[ "$config" == /* && "$state" == /* ]] || { echo 'Absolute XDG paths required.' >&2; return 1; }
    local path backup base="${state}/linux-setup/default-editor-upgrades"
    for path in "$config/mimeapps.list" "$config/fish/conf.d/agora-editor.fish"; do
        [[ ! -L "$path" && ( ! -e "$path" || -f "$path" ) ]] || { echo "Unsafe editor settings target: $path" >&2; return 1; }
    done
    if [[ -f "$config/fish/conf.d/agora-editor.fish" ]] && ! grep -qFx '# Managed by linux-setup default editor setup.' "$config/fish/conf.d/agora-editor.fish"; then
        echo 'Personal editor snippet exists; inspect before replacing.' >&2; return 1
    fi
    mkdir -p -- "$base"
    backup="$(mktemp -d "$base/$(date -u +%Y%m%dT%H%M%S)-XXXXXXXX")"
    chmod 700 "$backup"
    for path in mimeapps.list fish/conf.d/agora-editor.fish; do
        if [[ -f "$config/$path" ]]; then
            mkdir -p -- "$backup/$(dirname "$path")"
            cp -p -- "$config/$path" "$backup/$path"
            chmod 600 "$backup/$path"
        fi
    done
    printf 'Editor: Mousepad\n' > "$backup/change.txt"
    local mime
    for mime in text/plain text/markdown; do
        xdg-mime default org.xfce.mousepad.desktop "$mime"
        [[ "$(xdg-mime query default "$mime")" == org.xfce.mousepad.desktop ]] || return 1
    done
    if command -v fish >/dev/null 2>&1; then
        mkdir -p -- "$config/fish/conf.d"
        local temporary
        temporary="$(mktemp "$config/fish/conf.d/agora-editor.fish.tmp.XXXXXXXX")"
        printf '# Managed by linux-setup default editor setup.\nset -gx EDITOR mousepad\nset -gx VISUAL mousepad\n' > "$temporary"
        chmod 600 "$temporary"
        mv -f -- "$temporary" "$config/fish/conf.d/agora-editor.fish"
    fi
    if command -v pi >/dev/null 2>&1; then
        python3 "${SCRIPT_DIR}/../../packages/programming/pi/install_external_editor.py" --apply
    fi
    echo "Private editor backup: $backup"
    echo '✓ Default text/Markdown editor: Mousepad.'
}

# Narrow, idempotent setup: no app launch/quit, preferences, custom actions,
# browser/editor/terminal defaults or unrelated MIME associations are changed.
if [[ "$#" == 1 && "$1" == --file-manager-only ]]; then
    configure_file_manager
    exit 0
elif [[ "$#" == 1 && "$1" == --editor-only ]]; then
    configure_text_editor
    exit 0
elif [[ "$#" != 0 ]]; then
    echo "Usage: $0 [--file-manager-only | --editor-only]" >&2
    exit 2
fi
TERMINAL_LAUNCHER_SOURCE="${SCRIPT_DIR}/launch_terminal_command.sh"
TERMINAL_LAUNCHER_TARGET="${HOME}/.local/bin/launch-terminal-command"

echo "==> Configuring default applications..."

echo "==> Setting Firefox as default browser..."

xdg-settings set default-web-browser firefox.desktop || true
xdg-mime default firefox.desktop x-scheme-handler/http
xdg-mime default firefox.desktop x-scheme-handler/https

echo "==> Setting Thunar as default file manager..."

configure_file_manager

echo "==> Setting Mousepad as default plain-text and Markdown editor..."
configure_text_editor

echo "==> Installing default terminal launcher..."

if [[ ! -f "${TERMINAL_LAUNCHER_SOURCE}" ]]; then
    echo "✗ Default terminal launcher source is missing: ${TERMINAL_LAUNCHER_SOURCE}"
    exit 1
fi

mkdir -p "${HOME}/.local/bin"
install -m 0755 "${TERMINAL_LAUNCHER_SOURCE}" "${TERMINAL_LAUNCHER_TARGET}"

echo "==> Setting Kitty as default terminal..."

if command -v kitty >/dev/null 2>&1; then
    cat > "${HOME}/.local/bin/x-terminal-emulator" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-e" ]]; then
    shift
fi
exec kitty "$@"
EOF

    chmod +x "${HOME}/.local/bin/x-terminal-emulator"

    echo "==> Configuring Thunar 'Open Terminal Here' with Kitty..."

    mkdir -p "${HOME}/.local/share/xfce4/helpers"
    rm -f "${HOME}/.local/share/xfce4/helpers/alacritty.desktop"

    cat > "${HOME}/.local/share/xfce4/helpers/kitty.desktop" <<'EOF'
[Desktop Entry]
NoDisplay=true
Version=1.0
Type=X-XFCE-Helper
Name=Kitty
X-XFCE-Category=TerminalEmulator
X-XFCE-Commands=kitty
X-XFCE-CommandsWithParameter=kitty --directory %s
EOF

    mkdir -p "${HOME}/.config/xfce4"

    cat > "${HOME}/.config/xfce4/helpers.rc" <<'EOF'
TerminalEmulator=kitty
EOF


else
    echo "⚠ Kitty is not installed."
fi

echo "==> Setting shell environment variables..."

if command -v fish >/dev/null 2>&1; then
    fish -c 'set -Ux TERMINAL kitty'
else
    echo "⚠ Fish is not installed, skipping universal variables."
fi

echo "==> Setting Loupe as default image viewer..."

IMAGE_MIME_TYPES=(
    image/jpeg
    image/png
    image/webp
    image/gif
    image/bmp
    image/tiff
    image/svg+xml
    image/avif
)

for mime in "${IMAGE_MIME_TYPES[@]}"; do
    xdg-mime default org.gnome.Loupe.desktop "$mime"
done
echo "==> Setting VLC as default video player..."

VIDEO_MIME_TYPES=(
    video/mp4
    video/x-matroska
    video/webm
    video/x-msvideo
    video/quicktime
    video/mpeg
)

for mime in "${VIDEO_MIME_TYPES[@]}"; do
    xdg-mime default vlc.desktop "$mime"
done

echo "==> Setting VLC as default audio player..."

AUDIO_MIME_TYPES=(
    audio/mpeg
    audio/flac
    audio/ogg
    audio/wav
    audio/x-wav
    audio/mp4
)

for mime in "${AUDIO_MIME_TYPES[@]}"; do
    xdg-mime default vlc.desktop "$mime"
done

echo "✓ Default applications configured successfully."