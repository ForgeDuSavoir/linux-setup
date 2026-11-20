#!/usr/bin/env python3
"""Hyprland session adapter, including guarded visible-window/empty-session close."""
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


def request(*args, timeout=35):
    result = subprocess.run([str(MANAGER), "--json", "session", *args],
                            capture_output=True, text=True, check=False, timeout=timeout)
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


def pick_workspace(state, owner):
    owned = [ws for ws in state["order"] if columns.owner_of(state, ws) == owner]
    if owned:
        preferred = state["preferred"].get(owner)
        return (preferred if preferred in owned else owned[0]), False
    return columns.fresh_workspace(state, owner), True


def guard_stop(state, session_id):
    owned = {int(col) for col, value in state["owners"].items() if value == session_id}
    specials = {f"special:sm-{session_id}-{slot}" for slot in SLOTS}
    for client in columns.query("clients"):
        ws = client.get("workspace", {})
        if ws.get("name") in specials or (ws.get("id", 0) > 0 and
                                           ws["id"] in owned):
            raise RuntimeError("session has open windows; stop refused")


def stop_fallback(before, session_id):
    """Select the next opening-order survivor; reject the last graphical session."""
    ids = [item.get("id") for item in before["sessions"]]
    if any(not isinstance(sid, str) or not sid for sid in ids) or len(set(ids)) != len(ids):
        raise RuntimeError("invalid session list")
    if session_id not in ids:
        raise RuntimeError("not_found.session")
    if len(ids) == 1:
        raise RuntimeError("cannot stop the last open session; open another session first")
    if before.get("active_session_id") == session_id:
        return ids[(ids.index(session_id) + 1) % len(ids)]
    return None


def stop_session(state, before, session_id, fallback):
    if fallback is None and columns.owner_of(state, columns.active()) == session_id:
        raise RuntimeError("displayed and logical sessions differ; select the active session before stopping")
    guard_stop(state, session_id)
    if fallback is not None:
        # Switch/focus first: a failed fallback must never delete the current session.
        switched = request("switch", fallback)
        if switched.get("session", {}).get("id") != fallback:
            raise RuntimeError("invalid switch acknowledgement; original session was not stopped")
        target, fresh = pick_workspace(state, fallback)
        # Retain source ownership until stop is acknowledged, including late windows.
        columns.select(state, target, fresh=fresh, cleanup_after=False)
        if columns.active() != target or visible_scratchpad():
            raise RuntimeError("fallback desktop not confirmed; original session was not stopped")
        live = request("list")
        ids = {item["id"] for item in live.get("sessions", [])}
        if (live.get("active_session_id") != fallback
                or fallback not in ids or session_id not in ids):
            raise RuntimeError("sessions changed during fallback; original session was not stopped")
        guard_stop(state, session_id)
    reply = request("stop", session_id)
    if reply.get("stopped_session_id") != session_id:
        raise RuntimeError("invalid stop acknowledgement")
    if fallback is not None:
        after = request("list")
        if (after.get("active_session_id") != fallback
                or any(item["id"] == session_id for item in after.get("sessions", []))):
            raise RuntimeError("stop outcome/selection changed concurrently; inspect session state")
    # A lost reply/invalid acknowledgement never authorizes deleting ownership.
    state["owners"] = {ws: owner for ws, owner in state["owners"].items() if owner != session_id}
    state["order"] = [ws for ws in state["order"] if str(ws) in state["owners"]]
    state["preferred"].pop(session_id, None)
    columns.cleanup(state)

    return reply


def close_current(state, before, special, expected_workspace=None):
    """Never close a residual focus from a hidden workspace/session."""
    current = columns.active()
    owner = columns.owner_of(state, current)
    if (current <= 0 or (expected_workspace is not None and current != expected_workspace)
            or owner != (before.get('active_session_id') or 'neutral')):
        raise RuntimeError('displayed and logical sessions differ; close refused')
    allowed = {'special:global'} | {f'special:sm-{owner}-{slot}' for slot in SLOTS}
    if owner == 'neutral':
        allowed |= {f'special:session-{slot}' for slot in SLOTS}
    if special and special not in allowed:
        raise RuntimeError('scratchpad and displayed session differ; close refused')
    client = columns.query('activewindow')
    workspace = client.get('workspace', {})
    visible_target = (workspace.get('name') == special if special else workspace.get('id') == current)
    address = client.get('address', '')
    if visible_target and re.fullmatch(r'0x[0-9a-fA-F]+', address):
        # Validate native visibility in the SAME evaluation as an explicitly
        # addressed close; never let an implicit last-window target escape scope.
        name = json.dumps(special)
        columns.ctl('eval', f'''
local ws = hl.get_active_workspace()
local sp = hl.get_active_special_workspace()
local w = hl.get_active_window()
if not ws or ws.id ~= {current} or (sp and sp.name or "") ~= {name}
    or not w or w.address ~= "{address}"
    or not w.mapped or not w.visible or not w.workspace
    or ({name} ~= "" and w.workspace.name ~= {name})
    or ({name} == "" and w.workspace.id ~= {current}) then
    error("visible close target changed; close refused")
end
hl.dispatch(hl.dsp.window.close({{ window = "address:{address}" }}))
''')
        return {'closed_window_requested': True}
    if special:
        raise RuntimeError('no confirmed visible scratchpad window; close refused')
    if owner == 'neutral':
        return {'noop': True}  # Unowned desktop is not a logical Neutral instance.
    # Empty workspace != empty session: guard all owned workspaces/scratchpads.
    fallback = stop_fallback(before, owner)
    guard_stop(state, owner)
    live = request('list')
    if live != before or columns.active() != current or visible_scratchpad():
        raise RuntimeError('context changed before empty-session close; close refused')
    return stop_session(state, before, owner, fallback)


def start_arguments(source):
    """Translate a closed v3 source into literal CLI arguments, never a shell."""
    if source == {"kind": "neutral"}:
        return ("--neutral",)
    if (isinstance(source, dict) and set(source) == {"kind", "project_name"}
            and source["kind"] == "project" and isinstance(source["project_name"], str)
            and source["project_name"]):
        return ("--project", source["project_name"])
    raise RuntimeError("invalid v3 launch source")


def invoke(action, value=None):
    if action == "start":
        start_arguments(value)  # Reject old/malformed shapes before any desktop effect.
    columns.RUNTIME.mkdir(parents=True, exist_ok=True)
    with (columns.RUNTIME / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        special = visible_scratchpad()

        before = request("list")
        if not isinstance(before.get("sessions"), list):
            raise RuntimeError("invalid session list")
        fallback = stop_fallback(before, value) if action == "stop" else None
        state = columns.read_state() if action == 'close' else columns.load()
        if action == 'close':
            return close_current(state, before, special, value)
        if action != "stop":
            columns.cleanup(state)
        current = columns.active()
        if current > 0:
            owner = columns.owner_of(state, current)
            state.setdefault("preferred", {})[owner] = current
        if action not in ("start", "switch", "stop", "deactivate"):
            raise RuntimeError("usage: session-desktop start --neutral|start --project NAME|switch UUID|deactivate|stop UUID")
        # Hiding is reversible and does not move/close its windows. The shared
        # workspace lock also prevents a scratchpad shortcut racing this action.
        hide_scratchpad(special)
        if action == "stop":
            return stop_session(state, before, value, fallback)
        if action == "start":
            reply = request("start", *start_arguments(value))
            owner = reply["session"]["id"]
            # New UUID always receives a fresh empty workspace, never current windows.
        elif action == "switch":
            if value not in {s["id"] for s in before["sessions"]}:
                raise RuntimeError("not_found.session")
            reply = request("switch", value)
            owner = value
        elif action == "deactivate":
            reply = request("deactivate")
            owner = "neutral"
        else:
            raise RuntimeError("usage: session-desktop start --neutral|start --project NAME|switch UUID|deactivate|stop UUID")
        target, fresh = pick_workspace(state, owner)
        state["preferred"][owner] = target
        columns.save(state)
        columns.select(state, target, fresh=fresh)
        return reply


def status():
    """Read-only snapshot; never initialize state, hide a popup or change focus."""
    columns.RUNTIME.mkdir(parents=True, exist_ok=True)
    with (columns.RUNTIME / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(columns.STATE.read_text()) if columns.STATE.exists() else {"version": 3, "owners": {}}
        if state.get("version") not in (2, 3):
            raise RuntimeError("unsupported workspace state")
        monitors = columns.query("monitors")
        monitor = next((item for item in monitors if item.get("focused")), None)
        if monitor is None and len(monitors) == 1:
            monitor = monitors[0]
        owner = "unknown"
        if monitor:
            ws = monitor.get("activeWorkspace", {}).get("id", 0)
            if ws > 0:
                owner = columns.owner_of(state, ws if state["version"] == 3 else (ws + 1) // 2)
            special = monitor.get("specialWorkspace", {}).get("name", "")
            scoped = re.fullmatch(r"special:sm-([0-9a-f-]{36})-(ai|notes|tasks|4|5)", special)
            if scoped and scoped.group(1) != owner:
                owner = "unknown"
            elif special.startswith("special:session-") and owner != "neutral":
                owner = "unknown"
        result = request("list")
        if not isinstance(result.get("sessions"), list):
            raise RuntimeError("invalid session list")
        expected = result.get("active_session_id") or "neutral"
        known = owner == "neutral" or any(s["id"] == owner for s in result["sessions"])
        result["displayed_context"] = owner if known else "unknown"
        result["context_confirmed"] = known and owner == expected
        return result


def main():
    args = sys.argv[1:]
    if args == ["status"]:
        reply = status()
    elif len(args) == 1 and args[0] in ("deactivate", "close"):
        reply = invoke(args[0])
    elif len(args) == 2 and args[0] == "close" and args[1].isdigit():
        reply = invoke("close", int(args[1]))
    elif args == ["start", "--neutral"]:
        reply = invoke("start", {"kind": "neutral"})
    elif len(args) == 3 and args[:2] == ["start", "--project"]:
        reply = invoke("start", {"kind": "project", "project_name": args[2]})
    elif len(args) == 2 and args[0] in ("switch", "stop"):
        reply = invoke(args[0], args[1])
    else:
        raise RuntimeError("usage: session-desktop start --neutral|start --project NAME|switch UUID|deactivate|close [WORKSPACE_ID]|stop UUID")
    print(json.dumps(reply, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"session-desktop: {exc}", file=sys.stderr)
        sys.exit(1)
