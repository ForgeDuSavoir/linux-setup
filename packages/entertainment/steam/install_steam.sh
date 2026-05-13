#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Steam"

echo "==> Installing ${APP_NAME} and gaming dependencies..."

if ! command -v pacman >/dev/null 2>&1; then
    echo "✗ pacman is required."
    exit 1
fi

echo "==> Installing AMD / Vulkan / Steam dependencies..."

sudo pacman -S --needed --noconfirm \
    steam \
    mesa \
    lib32-mesa \
    vulkan-radeon \
    lib32-vulkan-radeon \
    vulkan-icd-loader \
    lib32-vulkan-icd-loader \
    vulkan-tools \
    gamemode \
    lib32-gamemode \
    mangohud \
    lib32-mangohud \
    xdg-desktop-portal \
    protonplus \
    wine \
    winetricks \
    protontricks \
    lutris \
    goverlay \
    heroic-games-launcher-bin \
    prismlauncher \
    jdk21-openjdk \
    gamescope

echo "==> Checking Steam user data directory..."

STEAM_DATA="$HOME/.local/share/Steam"
STEAM_LINK="$HOME/.steam/steam"

mkdir -p "$HOME/.steam"
mkdir -p "$HOME/.local/share"

if [[ -e "$STEAM_LINK" && ! -L "$STEAM_LINK" ]]; then
    echo "⚠ Existing $STEAM_LINK is not a symlink."
    echo "Moving it to ${STEAM_LINK}.backup"
    mv "$STEAM_LINK" "${STEAM_LINK}.backup.$(date +%Y%m%d-%H%M%S)"
fi

if [[ -L "$STEAM_LINK" ]]; then
    TARGET="$(readlink "$STEAM_LINK")"

    if [[ "$TARGET" != "$STEAM_DATA" ]]; then
        echo "⚠ Existing Steam symlink points to: $TARGET"
        echo "Recreating symlink..."
        rm "$STEAM_LINK"
        ln -s "$STEAM_DATA" "$STEAM_LINK"
    fi
else
    ln -s "$STEAM_DATA" "$STEAM_LINK"
fi

mkdir -p "$STEAM_DATA"

echo "==> Verifying Vulkan..."

if command -v vulkaninfo >/dev/null 2>&1; then
    if vulkaninfo --summary >/dev/null 2>&1; then
        echo "✓ Vulkan seems to work."
    else
        echo "⚠ Vulkan is installed, but vulkaninfo failed."
        echo "Steam may still launch, but games using Proton may have issues."
    fi
fi

echo "✓ ${APP_NAME} and gaming dependencies installed successfully."
echo
echo "You can now try launching Steam with:"
echo "steam"
