#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
AGENT_DIR="${HOME}/.pi/agent"
MCP_CONFIG="${AGENT_DIR}/mcp.json"
LAUNCHER="${HOME}/.local/bin/photocraft-ai"
WORKSPACE="${HOME}/Pictures/PhotoCraft-AI"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/photocraft"
TOKEN_FILE="${STATE_DIR}/control.token"

for tool in pi photocraft photocraft-cli node; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "✗ $tool is required to configure PhotoCraft MCP." >&2
        exit 1
    fi
done

mkdir -p "$AGENT_DIR" "${HOME}/.local/bin" "$WORKSPACE" "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [[ -e "$TOKEN_FILE" ]]; then
    chmod 600 "$TOKEN_FILE"
fi
install -m 0755 "${SCRIPT_DIR}/launch_photocraft_ai.sh" "$LAUNCHER"
SKILL_DIR="${HOME}/.agents/skills/photocraft"
mkdir -p "$SKILL_DIR"
install -m 0644 "${SCRIPT_DIR}/skills/photocraft/SKILL.md" "${SKILL_DIR}/SKILL.md"

# Merge our entries instead of replacing other Pi servers or storing credentials in Git.
node - "$MCP_CONFIG" "$WORKSPACE" "$TOKEN_FILE" <<'NODE'
const fs = require('node:fs');
const path = require('node:path');
const [configPath, workspace, tokenFile] = process.argv.slice(2);
let config = {};
try {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
} catch (err) {
    if (err.code !== 'ENOENT') throw err;
}
if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error('Invalid Pi MCP configuration');
config.mcpServers ??= {};
if (typeof config.mcpServers !== 'object' || Array.isArray(config.mcpServers)) throw new Error('Invalid mcpServers');
config.mcpServers.photocraft = {
    command: 'photocraft-cli',
    args: ['mcp', '--automation-read-root', workspace, '--automation-write-root', workspace],
    description: 'PhotoCraft headless document editing within the PhotoCraft-AI workspace'
};
config.mcpServers.photocraft_live = {
    command: 'photocraft-cli',
    args: ['mcp', '--bridge', '127.0.0.1:7878', '--control-token-file', tokenFile],
    enabled: false,
    description: 'PhotoCraft live desktop session started with photocraft-ai'
};
const tmp = path.join(path.dirname(configPath), `.mcp.json.${process.pid}.tmp`);
try {
    fs.writeFileSync(tmp, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
    fs.renameSync(tmp, configPath);
} finally {
    if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
}
NODE

echo "✓ PhotoCraft MCP configured in $MCP_CONFIG (headless enabled; live bridge disabled)."
echo "✓ PhotoCraft skill installed in $SKILL_DIR."
echo "  Start a live session with photocraft-ai; enable photocraft_live in Pi's /mcp when needed."
