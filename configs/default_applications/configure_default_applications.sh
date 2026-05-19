#!/usr/bin/env bash

set -euo pipefail

echo "==> Configuring default applications..."

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

echo "==> Setting Mousepad as default text editor..."

xdg-mime default org.xfce.mousepad.desktop text/plain
xdg-mime default org.xfce.mousepad.desktop application/x-shellscript
xdg-mime default org.xfce.mousepad.desktop application/json
xdg-mime default org.xfce.mousepad.desktop text/markdown

echo "==> Setting Alacritty as default terminal..."

if command -v alacritty >/dev/null 2>&1; then
    mkdir -p "${HOME}/.local/bin"

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
    fish -c 'set -Ux EDITOR mousepad'
    fish -c 'set -Ux VISUAL mousepad'
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

echo "==> Setting Obsidian as default Markdown editor..."

xdg-mime default obsidian.desktop text/markdown

echo "✓ Default applications configured successfully."