#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
AGENT_DIR="${HOME}/.pi/agent"
SESSION_DIR="${HOME}/.local/share/photocraft-ai"
DESKTOP_DIR="${HOME}/.local/share/applications"
BIN_DIR="${HOME}/.local/bin"

for tool in photocraft photocraft-cli pi kitty node xdg-mime; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "✗ $tool is required for PhotoCraft + assistant." >&2
        exit 1
    fi
done

mkdir -p "$AGENT_DIR" "$SESSION_DIR/.pi" "$DESKTOP_DIR" "$BIN_DIR"
chmod 700 "$SESSION_DIR/.pi"
install -m 0755 "$SCRIPT_DIR/launch_photocraft_ai.sh" "$BIN_DIR/photocraft-ai"
install -m 0755 "$SCRIPT_DIR/photocraft-ai-session" "$BIN_DIR/photocraft-ai-session"

# Global PhotoCraft stays headless; only the dedicated trusted Pi directory
# enables the token-authenticated live bridge.
node - "$SESSION_DIR/.pi/mcp.json" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const file = process.argv[2];
let config = {};
try { config = JSON.parse(fs.readFileSync(file, 'utf8')); }
catch (err) { if (err.code !== 'ENOENT') throw err; }
if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error('Invalid MCP config');
config.mcpServers ??= {};
if (typeof config.mcpServers !== 'object' || Array.isArray(config.mcpServers)) throw new Error('Invalid mcpServers');
Object.assign(config.mcpServers, {
    photocraft_live: {enabled: true},
    photocraft: {enabled: false},
    filmcraft_live: {enabled: false}
});
const tmp = path.join(path.dirname(file), `.mcp.${process.pid}.tmp`);
try {
    fs.writeFileSync(tmp, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
    fs.renameSync(tmp, file);
} finally { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); }
NODE

node - "$SCRIPT_DIR/photocraft-ai.desktop" "$DESKTOP_DIR/photocraft-ai.desktop" "$BIN_DIR/photocraft-ai" <<'NODE'
const fs = require('node:fs');
const [source, target, launcher] = process.argv.slice(2);
if (/\s/.test(launcher)) throw new Error('Desktop Exec requires a launcher path without whitespace');
fs.writeFileSync(target, fs.readFileSync(source, 'utf8').replace('@PHOTOCRAFT_AI_LAUNCHER@', launcher), {mode: 0o644});
NODE
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$DESKTOP_DIR/photocraft-ai.desktop"
fi
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
xdg-mime default photocraft-ai.desktop application/x-photocraft

echo '✓ PhotoCraft + Pi launcher and .pcraft default installed.'
echo "  Pi will ask you to trust $SESSION_DIR on first use; review its .pi/mcp.json first."
