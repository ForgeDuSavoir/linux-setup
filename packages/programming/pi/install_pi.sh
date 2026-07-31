#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Pi"
PACKAGE_NAME="@earendil-works/pi-coding-agent"
APP_COMMAND="pi"
PACKAGE_MANAGER="npm"
INSTALL_COMMAND="sudo npm install -g --ignore-scripts ${PACKAGE_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/pi.desktop"
SOURCE_DESKTOP_FILE="$SCRIPT_DIR/pi.desktop"
LAUNCHER_FILE="$BIN_DIR/pi-launcher"
SOURCE_LAUNCHER_FILE="$SCRIPT_DIR/launch_pi.sh"
EXTERNAL_EDITOR_FILE="$BIN_DIR/pi-external-editor"
SOURCE_EXTERNAL_EDITOR_FILE="$SCRIPT_DIR/launch_external_editor.sh"
AGENT_DIR="$HOME/.pi/agent"
EXTENSIONS_DIR="$AGENT_DIR/extensions"
KEYBINDINGS_FILE="$AGENT_DIR/keybindings.json"
SETTINGS_FILE="$AGENT_DIR/settings.json"
SOURCE_KEYBINDINGS_FILE="$SCRIPT_DIR/keybindings.json"
FOOTER_EXTENSION_FILE="$EXTENSIONS_DIR/persistent_footer.ts"
SOURCE_FOOTER_EXTENSION_FILE="$SCRIPT_DIR/persistent_footer.ts"
LEGACY_HEADER_EXTENSION_FILE="$EXTENSIONS_DIR/persistent_header.ts"

echo "==> Installing ${APP_NAME}..."

if [[ -n "${APP_COMMAND}" ]] && command -v "$APP_COMMAND" >/dev/null 2>&1; then
    echo "✓ ${APP_NAME} is already installed."
else
    if [[ -z "${PACKAGE_MANAGER}" ]]; then
        echo "✗ PACKAGE_MANAGER is not set."
        exit 1
    fi

    if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
        echo "✗ ${PACKAGE_MANAGER} is required to install ${APP_NAME}."
        echo "Install ${PACKAGE_MANAGER} first, then run this script again."
        exit 1
    fi

    if [[ -z "${INSTALL_COMMAND}" ]]; then
        echo "✗ INSTALL_COMMAND is not set."
        exit 1
    fi

    eval "$INSTALL_COMMAND"

    if command -v "$APP_COMMAND" >/dev/null 2>&1; then
        echo "✓ ${APP_NAME} installed successfully."
    else
        echo "✗ ${APP_NAME} installation failed."
        exit 1
    fi
fi

if [[ ! -f "$SOURCE_DESKTOP_FILE" ]]; then
    echo "✗ Desktop entry source file is missing: $SOURCE_DESKTOP_FILE"
    exit 1
fi

if [[ ! -f "$SOURCE_LAUNCHER_FILE" ]]; then
    echo "✗ Launcher source file is missing: $SOURCE_LAUNCHER_FILE"
    exit 1
fi

if [[ ! -f "$SOURCE_EXTERNAL_EDITOR_FILE" ]]; then
    echo "✗ External editor launcher source file is missing: $SOURCE_EXTERNAL_EDITOR_FILE"
    exit 1
fi

if [[ ! -f "$SOURCE_FOOTER_EXTENSION_FILE" ]]; then
    echo "✗ Footer extension source file is missing: $SOURCE_FOOTER_EXTENSION_FILE"
    exit 1
fi

if [[ ! -f "$SOURCE_KEYBINDINGS_FILE" ]]; then
    echo "✗ Keybindings source file is missing: $SOURCE_KEYBINDINGS_FILE"
    exit 1
fi

echo "==> Installing ${APP_NAME} launchers..."
mkdir -p "$BIN_DIR"
install -m 0755 "$SOURCE_LAUNCHER_FILE" "$LAUNCHER_FILE"
install -m 0755 "$SOURCE_EXTERNAL_EDITOR_FILE" "$EXTERNAL_EDITOR_FILE"

echo "==> Installing ${APP_NAME} footer extension..."
mkdir -p "$EXTENSIONS_DIR"
rm -f "$LEGACY_HEADER_EXTENSION_FILE"
install -m 0644 "$SOURCE_FOOTER_EXTENSION_FILE" "$FOOTER_EXTENSION_FILE"

echo "==> Installing ${APP_NAME} keybindings..."
mkdir -p "$AGENT_DIR"
install -m 0644 "$SOURCE_KEYBINDINGS_FILE" "$KEYBINDINGS_FILE"

echo "==> Configuring ${APP_NAME} terminal rendering..."
node - "$SETTINGS_FILE" <<'NODE'
const fs = require("node:fs");
const settingsPath = process.argv[2];
let settings = {};

try {
    settings = JSON.parse(fs.readFileSync(settingsPath, "utf8"));
} catch (error) {
    if (error.code !== "ENOENT") throw error;
}

settings.terminal = { ...settings.terminal, clearOnShrink: true };
fs.writeFileSync(settingsPath, `${JSON.stringify(settings, null, 2)}\n`);
NODE

echo "==> Installing ${APP_NAME} desktop entry..."
mkdir -p "$DESKTOP_DIR"
install -m 0644 "$SOURCE_DESKTOP_FILE" "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo "✓ ${APP_NAME} desktop entry installed successfully."
