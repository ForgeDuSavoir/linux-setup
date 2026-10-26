#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
AGENT_DIR="${HOME}/.pi/agent"
SESSION_DIR="${HOME}/.local/share/filmcraft-ai"
DESKTOP_DIR="${HOME}/.local/share/applications"
MIME_DIR="${HOME}/.local/share/mime"
BIN_DIR="${HOME}/.local/bin"
SKILL_DIR="${HOME}/.agents/skills/filmcraft"

for tool in filmcraft filmcraft-cli pi kitty node update-mime-database xdg-mime; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "✗ $tool is required for FilmCraft + assistant." >&2
        exit 1
    fi
done

mkdir -p "$AGENT_DIR" "$SESSION_DIR/.pi" "$DESKTOP_DIR" "$MIME_DIR/packages" "$BIN_DIR" "$SKILL_DIR/references"
chmod 700 "$SESSION_DIR/.pi"
install -m 0755 "$SCRIPT_DIR/launch_filmcraft_ai.sh" "$BIN_DIR/filmcraft-ai"
install -m 0755 "$SCRIPT_DIR/filmcraft-ai-session" "$BIN_DIR/filmcraft-ai-session"
install -m 0644 "$SCRIPT_DIR/../skills/filmcraft/SKILL.md" "$SKILL_DIR/SKILL.md"
install -m 0644 "$SCRIPT_DIR/../skills/filmcraft/references/interface.md" "$SKILL_DIR/references/interface.md"

# FilmCraft is disabled for ordinary Pi sessions. The trusted dedicated session
# folder enables only the bridge, leaving the existing PhotoCraft setup intact.
node - "$AGENT_DIR/mcp.json" "$SESSION_DIR/.pi/mcp.json" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
function merge(file, servers) {
    let config = {};
    try { config = JSON.parse(fs.readFileSync(file, 'utf8')); }
    catch (err) { if (err.code !== 'ENOENT') throw err; }
    if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error(`Invalid MCP config: ${file}`);
    config.mcpServers ??= {};
    if (!config.mcpServers || typeof config.mcpServers !== 'object' || Array.isArray(config.mcpServers)) throw new Error(`Invalid mcpServers: ${file}`);
    Object.assign(config.mcpServers, servers);
    const tmp = path.join(path.dirname(file), `.mcp.${process.pid}.tmp`);
    try {
        fs.writeFileSync(tmp, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
        fs.renameSync(tmp, file);
    } finally { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); }
}
merge(process.argv[2], {
    filmcraft_live: {
        command: 'filmcraft-cli',
        args: ['mcp', '--bridge', '127.0.0.1:9876'],
        enabled: false,
        description: 'FilmCraft live desktop via localhost; unauthenticated, enable only for dedicated Pi sessions'
    }
});
merge(process.argv[3], {
    filmcraft_live: {enabled: true},
    photocraft: {enabled: false},
    photocraft_live: {enabled: false}
});
NODE

install -m 0644 "$SCRIPT_DIR/filmcraft-mime.xml" "$MIME_DIR/packages/filmcraft-ai.xml"
update-mime-database "$MIME_DIR"

# This .desktop entry handles projects only; keep the native FilmCraft launcher
# installed so Thunar's "Open With" can still open projects without assistance.
node - "$SCRIPT_DIR/filmcraft-ai.desktop" "$DESKTOP_DIR/filmcraft-ai.desktop" "$BIN_DIR/filmcraft-ai" <<'NODE'
const fs = require('node:fs');
const [source, target, launcher] = process.argv.slice(2);
if (/\s/.test(launcher)) throw new Error('Desktop Exec requires a launcher path without whitespace');
fs.writeFileSync(target, fs.readFileSync(source, 'utf8').replace('@FILMCRAFT_AI_LAUNCHER@', launcher), {mode: 0o644});
NODE
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$DESKTOP_DIR/filmcraft-ai.desktop"
fi
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
xdg-mime default filmcraft-ai.desktop application/x-filmcraft

echo '✓ FilmCraft MCP, skill, launcher and .fcproj default installed.'
echo "  Pi will ask you to trust $SESSION_DIR on first use; approve only after reviewing its .pi/mcp.json."
