#!/usr/bin/env python3
"""Scratchpad routing tests with fake IPC, never a live compositor or daemon."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / "files/Scripts/scratchpad.sh"
SESSION = "12345678-1234-1234-1234-123456789abc"

with tempfile.TemporaryDirectory(prefix="scratchpad-test-") as temp:
    root = Path(temp)
    manager = root / "session-manager"
    manager.write_text("#!/bin/sh\nprintf '%s\\n' \"$SESSION_REPLY\"\n")
    manager.chmod(0o700)
    hyprctl = root / "hyprctl"
    hyprctl.write_text("""#!/bin/sh
case "$1" in
  activewindow) printf '{"workspace":{"name":"1"}}\\n' ;;
  activeworkspace) printf '{"id":1}\\n' ;;
  dispatch) printf '%s\\n' "$2" >> "$HYPR_LOG" ;;
  *) exit 8 ;;
esac
""")
    hyprctl.chmod(0o700)
    log = root / "commands"
    env = {**os.environ, "PATH": str(root) + ":/usr/bin:/bin",
           "HOME": str(root), "SESSION_MANAGER_BIN": str(manager),
           "HYPR_LOG": str(log), "XDG_RUNTIME_DIR": str(root)}

    def run(action, slot, active=None, valid=True):
        env["SESSION_REPLY"] = json.dumps({"active_session_id": active,
                                              "sessions": [{"id": SESSION}]} if valid else {"code": "unavailable"})
        result = subprocess.run(["/bin/bash", str(SOURCE), action, slot],
                                env=env, capture_output=True, text=True)
        commands = log.read_text().splitlines() if log.exists() else []
        log.unlink(missing_ok=True)
        return result, commands

    for slot, label in [("1", "ai"), ("2", "notes"), ("3", "tasks"), ("4", "4"), ("5", "5")]:
        result, commands = run("toggle", slot, SESSION)
        assert result.returncode == 0, result.stderr
        assert commands == [f'hl.dsp.workspace.toggle_special("sm-{SESSION}-{label}")']
        result, commands = run("toggle", slot)
        assert result.returncode == 0, result.stderr
        assert commands == [f'hl.dsp.workspace.toggle_special("session-{label}")']
    result, commands = run("move", "2", SESSION)
    assert result.returncode == 0, result.stderr
    assert commands == [f'hl.dsp.window.move({{ workspace = "special:sm-{SESSION}-notes" }})']
    result, commands = run("toggle", "global")
    assert result.returncode == 0 and commands == ['hl.dsp.workspace.toggle_special("global")']
    for active, valid in [("bad-id", True), (SESSION, False)]:
        result, commands = run("move", "1", active, valid)
        assert result.returncode != 0 and not commands

print("Session UUID scratchpads and legacy neutral scratchpads route without a live desktop.")
