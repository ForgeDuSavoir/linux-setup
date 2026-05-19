#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Dolphin and Kitty"

echo "==> Uninstalling ${APP_NAME}..."

PACKAGES=(
    dolphin
    dolphin-plugins
    kitty
)

INSTALLED_PACKAGES=()

for package in "${PACKAGES[@]}"; do
    if pacman -Q "$package" >/dev/null 2>&1; then
        INSTALLED_PACKAGES+=("$package")
    fi
done

if [[ ${#INSTALLED_PACKAGES[@]} -eq 0 ]]; then
    echo "✓ Nothing to uninstall."
    exit 0
fi

echo "==> Removing packages:"
printf ' - %s\n' "${INSTALLED_PACKAGES[@]}"

sudo pacman -Rns --noconfirm "${INSTALLED_PACKAGES[@]}"

echo "✓ ${APP_NAME} uninstalled successfully."