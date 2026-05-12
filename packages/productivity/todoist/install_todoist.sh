#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Todoist"
FLATPAK_ID="com.todoist.Todoist"
REMOTE_NAME="flathub"
REMOTE_URL="https://flathub.org/repo/flathub.flatpakrepo"

echo "==> Installing ${APP_NAME}..."

if ! command -v flatpak >/dev/null 2>&1; then
    echo "==> Installing Flatpak..."
    sudo pacman -S --needed --noconfirm flatpak
fi

if ! flatpak remotes --columns=name | grep -qx "$REMOTE_NAME"; then
    echo "==> Adding Flathub remote..."
    flatpak remote-add --if-not-exists "$REMOTE_NAME" "$REMOTE_URL"
fi

if flatpak list --app --columns=application | grep -qx "$FLATPAK_ID"; then
    echo "✓ ${APP_NAME} is already installed."
    exit 0
fi

flatpak install -y "$REMOTE_NAME" "$FLATPAK_ID"

echo "✓ ${APP_NAME} installed successfully."
