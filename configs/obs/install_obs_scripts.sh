#!/usr/bin/env bash
# Update automation only, without replacing OBS settings or restarting OBS.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BIN="${HOME}/.local/bin"
LUA_DIR="${OBS_LUA_DIR:-/usr/share/obs/obs-plugins/frontend-tools/scripts/custom}"
mkdir -p "${BIN}"
for name in obs-post-record obs-post-record-gaming; do
    target="${BIN}/${name}.sh"
    [[ ! -L "${target}" ]] || { echo "Refusing a symlinked target: ${target}" >&2; exit 1; }
    if [[ -f "${target}" ]] && ! cmp -s "${SCRIPT_DIR}/scripts-sh/${name}.sh" "${target}"; then
        backup="$(mktemp "${target}.bak.XXXXXXXX")"
        cp -p -- "${target}" "${backup}"
    fi
    install -m 0755 "${SCRIPT_DIR}/scripts-sh/${name}.sh" "${target}"
done
if [[ -d "${LUA_DIR}" && -w "${LUA_DIR}" ]]; then
    install -m 0644 "${SCRIPT_DIR}/scripts-lua/"*.lua "${LUA_DIR}/"
elif sudo -n true 2>/dev/null; then
    sudo -n install -d "${LUA_DIR}"
    sudo -n install -m 0644 "${SCRIPT_DIR}/scripts-lua/"*.lua "${LUA_DIR}/"
else
    echo 'OBS shell hooks installed. Lua installation requires administrator approval:' >&2
    printf '  sudo install -Dm644 %q %q\n' "${SCRIPT_DIR}/scripts-lua/obs-post-record.lua" "${LUA_DIR}/obs-post-record.lua" >&2
    printf '  sudo install -Dm644 %q %q\n' "${SCRIPT_DIR}/scripts-lua/obs-post-record-gaming.lua" "${LUA_DIR}/obs-post-record-gaming.lua" >&2
    echo 'Do not rely on scoped OBS notifications until Lua hooks are updated and reloaded in OBS.' >&2
    exit 1
fi
echo 'OBS automation installed; reload its Lua scripts in OBS when no recording is running.'
