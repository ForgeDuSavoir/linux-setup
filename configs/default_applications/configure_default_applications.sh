#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TERMINAL_LAUNCHER_SOURCE="${SCRIPT_DIR}/launch_terminal_command.sh"
TERMINAL_LAUNCHER_TARGET="${HOME}/.local/bin/launch-terminal-command"
NEOVIM_LAUNCHER_SOURCE="${SCRIPT_DIR}/open_neovim.sh"
NEOVIM_LAUNCHER_TARGET="${HOME}/.local/bin/agora-open-neovim"
NEOVIM_DESKTOP_SOURCE="${SCRIPT_DIR}/agora-neovim.desktop"
NEOVIM_DESKTOP_TARGET="${HOME}/.local/share/applications/agora-neovim.desktop"

echo "==> Configuring default applications..."

if [[ ! -f "${NEOVIM_LAUNCHER_SOURCE}" || ! -f "${NEOVIM_DESKTOP_SOURCE}" ]]; then
    echo "✗ Neovim desktop launcher source files are missing." >&2
    exit 1
fi

mkdir -p "${HOME}/.local/bin" "${HOME}/.local/share/applications"
install -m 0755 "${NEOVIM_LAUNCHER_SOURCE}" "${NEOVIM_LAUNCHER_TARGET}"
install -m 0644 "${NEOVIM_DESKTOP_SOURCE}" "${NEOVIM_DESKTOP_TARGET}"
update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true

echo "==> Setting Firefox as default browser..."

xdg-settings set default-web-browser firefox.desktop || true
xdg-mime default firefox.desktop x-scheme-handler/http
xdg-mime default firefox.desktop x-scheme-handler/https

echo "==> Setting Thunar as default file manager..."

xdg-mime default thunar.desktop inode/directory
xdg-mime default thunar.desktop application/x-gnome-saved-search

if command -v gio >/dev/null 2>&1; then
    gio mime inode/directory thunar.desktop || true
fi

echo "==> Setting Neovim as default plain-text and Markdown editor..."

xdg-mime default agora-neovim.desktop text/plain
xdg-mime default agora-neovim.desktop text/markdown

echo "==> Installing default terminal launcher..."

if [[ ! -f "${TERMINAL_LAUNCHER_SOURCE}" ]]; then
    echo "✗ Default terminal launcher source is missing: ${TERMINAL_LAUNCHER_SOURCE}"
    exit 1
fi

mkdir -p "${HOME}/.local/bin"
install -m 0755 "${TERMINAL_LAUNCHER_SOURCE}" "${TERMINAL_LAUNCHER_TARGET}"

echo "==> Setting Alacritty as default terminal..."

if command -v alacritty >/dev/null 2>&1; then
    cat > "${HOME}/.local/bin/x-terminal-emulator" <<'EOF'
#!/usr/bin/env bash
exec alacritty "$@"
EOF

    chmod +x "${HOME}/.local/bin/x-terminal-emulator"

    echo "==> Configuring Thunar 'Open Terminal Here' with Alacritty..."

    mkdir -p "${HOME}/.local/share/xfce4/helpers"

    cat > "${HOME}/.local/share/xfce4/helpers/alacritty.desktop" <<'EOF'
[Desktop Entry]
NoDisplay=true
Version=1.0
Type=X-XFCE-Helper
Name=Alacritty
X-XFCE-Category=TerminalEmulator
X-XFCE-Commands=alacritty
X-XFCE-CommandsWithParameter=alacritty --working-directory %s
EOF

    mkdir -p "${HOME}/.config/xfce4"

    cat > "${HOME}/.config/xfce4/helpers.rc" <<'EOF'
TerminalEmulator=alacritty
EOF


else
    echo "⚠ Alacritty is not installed."
fi

echo "==> Setting shell environment variables..."

if command -v fish >/dev/null 2>&1; then
    fish -c 'set -Ux TERMINAL alacritty'
    fish -c 'set -Ux EDITOR nvim'
    fish -c 'set -Ux VISUAL nvim'
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