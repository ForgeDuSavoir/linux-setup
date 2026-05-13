#!/usr/bin/env bash

set -euo pipefail

GTK_THEME="adw-gtk3-dark"
ICON_THEME="Papirus-Dark"
CURSOR_THEME="Bibata-Modern-Classic"
CURSOR_SIZE="24"

GTK3_CONFIG="${HOME}/.config/gtk-3.0/settings.ini"
GTK4_CONFIG="${HOME}/.config/gtk-4.0/settings.ini"

echo "==> Applying theme..."

mkdir -p "${HOME}/.config/gtk-3.0"
mkdir -p "${HOME}/.config/gtk-4.0"

cat > "${GTK3_CONFIG}" <<EOF
[Settings]
gtk-theme-name=${GTK_THEME}
gtk-icon-theme-name=${ICON_THEME}
gtk-cursor-theme-name=${CURSOR_THEME}
gtk-cursor-theme-size=${CURSOR_SIZE}
gtk-application-prefer-dark-theme=true
EOF

cat > "${GTK4_CONFIG}" <<EOF
[Settings]
gtk-theme-name=${GTK_THEME}
gtk-icon-theme-name=${ICON_THEME}
gtk-cursor-theme-name=${CURSOR_THEME}
gtk-cursor-theme-size=${CURSOR_SIZE}
gtk-application-prefer-dark-theme=true
EOF

echo "==> Applying cursor theme with gsettings if available..."

if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.interface gtk-theme "${GTK_THEME}" || true
    gsettings set org.gnome.desktop.interface icon-theme "${ICON_THEME}" || true
    gsettings set org.gnome.desktop.interface cursor-theme "${CURSOR_THEME}" || true
    gsettings set org.gnome.desktop.interface cursor-size "${CURSOR_SIZE}" || true
    gsettings set org.gnome.desktop.interface color-scheme "prefer-dark" || true
fi

echo ""
echo "Add this to your Hyprland config if it is not already present:"
echo "env = XCURSOR_THEME,${CURSOR_THEME}"
echo "env = XCURSOR_SIZE,${CURSOR_SIZE}"

echo ""
echo "✓ Theme applied successfully."
echo "You may need to log out and back in for all applications to use the new cursor/theme."
