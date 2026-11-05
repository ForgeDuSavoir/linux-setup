#!/usr/bin/env python3
"""Hyprland client for Session Manager. No window move/close operation is issued."""
import fcntl
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys

COLUMNS = Path(os.environ.get("SESSION_COLUMNS_SCRIPT", str(
    Path.home() / ".config/hypr/Scripts/workspace-columns.py")))
spec = importlib.util.spec_from_file_location("workspace_columns", COLUMNS)
columns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(columns)
MANAGER = Path(os.environ.get("SESSION_MANAGER_BIN", str(Path.home() / ".local/bin/session-manager")))
SLOTS = ("ai", "notes", "tasks", "4", "5")


def request(*args):
    result = subprocess.run([str(MANAGER), "--json", "session", *args],
                            capture_output=True, text=True, check=False, timeout=35)
    try:
        payload = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError("invalid Session Manager reply") from exc
    if result.returncode:
        raise RuntimeError(payload.get("code", "session request failed"))
    return payload


def visible_scratchpad():
    monitors = columns.query("monitors")
    if len(monitors) != 1:
        raise RuntimeError("desktop integration requires one monitor; refusing to change context")
    return monitors[0].get("specialWorkspace", {}).get("name", "")


def hide_scratchpad(name):
    if not name:
        return
    # Do not interpolate an arbitrary compositor name into a Lua dispatcher.
    if not re.fullmatch(r"special:[A-Za-z0-9_-]{1,100}", name):
        raise RuntimeError("unsafe special workspace name; refusing to change context")
    columns.dispatch(f'hl.dsp.workspace.toggle_special("{name[len("special:"):]}")')
    if visible_scratchpad():
        raise RuntimeError("scratchpad did not hide; refusing to change context")


def pick_column(state, owner):
    owned = sorted(int(col) for col, value in state["owners"].items() if value == owner)
    if owned:
        # Prefer the last visited column; retain an empty column even if Hyprland
        # destroyed the underlying workspace when focus moved elsewhere.
        preferred = state.setdefault("preferred", {}).get(owner)
        return preferred if preferred in owned else owned[0]
    existing = [w["id"] for w in columns.query("workspaces") if w["id"] > 0]
    col = max([0, *map(int, state["owners"]), *(columns.column_of(i) for i in existing)]) + 1
    state["owners"][str(col)] = owner
    state["last"][str(col)] = 1
    return col


def guard_stop(state, session_id):
    owned = {int(col) for col, value in state["owners"].items() if value == session_id}
    specials = {f"special:sm-{session_id}-{slot}" for slot in SLOTS}
    for client in columns.query("clients"):
        ws = client.get("workspace", {})
        if ws.get("name") in specials or (ws.get("id", 0) > 0 and
                                           columns.column_of(ws["id"]) in owned):
            raise RuntimeError("session has open windows; stop refused")


def invoke(action, value=None):
    columns.RUNTIME.mkdir(parents=True, exist_ok=True)
    with (columns.RUNTIME / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not columns.STATE.exists():
            # First menu action after login: register existing columns as neutral
            # without running the historical workspace/window migration.
            existing = {columns.column_of(w["id"]) for w in columns.query("workspaces")
                        if w["id"] > 0}
            if columns.active() > 0:
                existing.add(columns.column_of(columns.active()))
            columns.save({"version": 2, "last": {}, "origins": {},
                          "owners": {str(c): "neutral" for c in sorted(existing)}})
        state = columns.load()
        special = visible_scratchpad()
        before = request("list")
        if not isinstance(before.get("sessions"), list):
            raise RuntimeError("invalid session list")
        current = columns.active()
        if current > 0:
            owner = columns.owner_of(state, columns.column_of(current))
            state.setdefault("preferred", {})[owner] = columns.column_of(current)
        if action not in ("start", "switch", "stop", "deactivate"):
            raise RuntimeError("usage: session-desktop.py start NAME|switch UUID|deactivate|stop UUID")
        # Hiding is reversible and does not move/close its windows. The shared
        # workspace lock also prevents a scratchpad shortcut racing this action.
        hide_scratchpad(special)
        if action == "stop":
            if value not in {s["id"] for s in before["sessions"]}:
                raise RuntimeError("not_found.session")
            guard_stop(state, value)
            reply = request("stop", value)
            if reply.get("stopped_session_id") != value:
                raise RuntimeError("invalid stop acknowledgement")
            # No windows remain in the scoped columns/scratchpads at this check.
            for col, owner in list(state["owners"].items()):
                if owner == value:
                    state["owners"].pop(col)
            state.get("preferred", {}).pop(value, None)
            if before.get("active_session_id") == value:
                target = pick_column(state, "neutral")
                columns.save(state)
                columns.focus(columns.workspace_id(target, state["last"].get(str(target), 1)))
            else:
                columns.save(state)
            return reply
        if action == "start":
            reply = request("start", value)
            owner = reply["session"]["id"]
            # New UUID always receives a fresh, empty column, not the current one.
        elif action == "switch":
            if value not in {s["id"] for s in before["sessions"]}:
                raise RuntimeError("not_found.session")
            reply = request("switch", value)
            owner = value
        elif action == "deactivate":
            reply = request("deactivate")
            owner = "neutral"
        else:
            raise RuntimeError("usage: session-desktop.py start NAME|switch UUID|deactivate|stop UUID")
        target = pick_column(state, owner)
        state["preferred"][owner] = target
        columns.save(state)
        columns.focus(columns.workspace_id(target, state["last"].get(str(target), 1)))
        return reply


def main():
    args = sys.argv[1:]
    if len(args) == 1 and args[0] == "deactivate":
        reply = invoke(args[0])
    elif len(args) == 2 and args[0] in ("start", "switch", "stop"):
        reply = invoke(args[0], args[1])
    else:
        raise RuntimeError("usage: session-desktop.py start NAME|switch UUID|deactivate|stop UUID")
    print(json.dumps(reply, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"session-desktop: {exc}", file=sys.stderr)
        sys.exit(1)
