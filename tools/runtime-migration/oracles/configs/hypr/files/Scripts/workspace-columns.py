#!/usr/bin/env python3
"""Ordered, single workspaces per session (the filename is kept for existing installs).

Workspace IDs are opaque stable identities. List order, not ID arithmetic, defines
"next" and insertion. Upgrading old two-row metadata never dispatches or moves windows.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "hyprland"
STATE = RUNTIME / "workspace-columns.json"
MAX_ID = 2147483646


def ctl(*args):
    result = subprocess.run(["hyprctl", *map(str, args)], text=True, capture_output=True, check=True)
    if any(text.lstrip().lower().startswith("error") for text in (result.stdout, result.stderr)):
        raise RuntimeError(result.stdout)
    return result.stdout


def query(name):
    return json.loads(ctl(name, "-j"))


def dispatch(expression):
    ctl("dispatch", expression)


def focus(ws):
    dispatch(f"hl.dsp.focus({{ workspace = {ws} }})")


def focus_empty(ws):
    ctl("eval", f'if hl.get_workspace({ws}) then error("workspace target already exists") end; '
        f'hl.dispatch(hl.dsp.focus({{ workspace = {ws} }}))')


def move_empty(ws, address):
    if not re.fullmatch(r"[0-9a-fA-Fx]+", address):
        raise RuntimeError("unsafe window address")
    ctl("eval", f'if hl.get_workspace({ws}) then error("workspace target already exists") end; '
        f'hl.dispatch(hl.dsp.window.move({{ workspace = {ws}, window = "address:{address}" }}))')


def move(ws, address=None, follow=True):
    if address and not re.fullmatch(r"[0-9a-fA-Fx]+", address):
        raise RuntimeError("unsafe window address")
    window = f', window = "address:{address}"' if address else ""
    follow_arg = ", follow = false" if not follow else ""
    dispatch(f"hl.dsp.window.move({{ workspace = {ws}{window}{follow_arg} }})")


def active():
    return query("activeworkspace")["id"]


def occupied():
    return {c["workspace"]["id"] for c in query("clients") if c.get("workspace", {}).get("id", 0) > 0}


def visible():
    return ({m.get("activeWorkspace", {}).get("id", 0) for m in query("monitors")} | {active()}) - {0}


def owner_of(state, ws):
    return state.get("owners", {}).get(str(ws), "neutral")


def current_owner(state):
    return owner_of(state, active())


def validate(state):
    if state.get("version") != 3:
        raise RuntimeError("unsupported workspace state")
    order = state.get("order")
    owners = state.get("owners")
    if (not isinstance(order, list) or not isinstance(owners, dict)
            or any(type(ws) is not int or not 0 < ws <= MAX_ID for ws in order)
            or len(set(order)) != len(order) or set(owners) != {str(ws) for ws in order}
            or any(not isinstance(owner, str) or not owner for owner in owners.values())
            or not isinstance(state.get("preferred"), dict)

            or type(state.get("next_id")) is not int or not 0 < state["next_id"] <= MAX_ID + 1):
        raise RuntimeError("invalid workspace state")
    for owner, ws in state["preferred"].items():
        if type(ws) is not int or ws not in order or owner_of(state, ws) != owner:
            raise RuntimeError("invalid preferred workspace")

    return state


def save(state):
    validate(state)
    fd, name = tempfile.mkstemp(prefix=".workspace-list-", dir=STATE.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, STATE)
    finally:
        Path(name).unlink(missing_ok=True)


def project_state(raw, existing):
    """Pure projection: split old columns into their actual IDs, keeping UUID owners."""
    if raw is None:
        return {"version": 3, "order": sorted(existing),
                "owners": {str(ws): "neutral" for ws in sorted(existing)},
                "preferred": {}, "next_id": max({0, *existing}) + 1}
    if raw.get("version") == 3:
        # Retire address-based provenance from earlier desktop metadata.
        return validate({key: value for key, value in raw.items() if key != "origins"})
    if raw.get("version") != 2:
        raise RuntimeError("unsupported workspace state")
    owners = raw.get("owners", {})
    cols = sorted({(ws + 1) // 2 for ws in existing} | {int(col) for col in owners})
    state = {"version": 3, "order": [], "owners": {}, "preferred": {}}
    choices = {}
    for col in cols:
        members = [ws for ws in (2 * col - 1, 2 * col) if ws in existing]
        if not members:  # Preserve one empty anchor until normal cleanup/navigation.
            members = [2 * col - 2 + raw.get("last", {}).get(str(col), 1)]
        state["order"].extend(members)
        for ws in members:
            state["owners"][str(ws)] = owners.get(str(col), "neutral")
        preferred = 2 * col - 2 + raw.get("last", {}).get(str(col), 1)
        choices[col] = preferred if preferred in members else members[0]
    state["preferred"] = {owner: choices[col] for owner, col in raw.get("preferred", {}).items()
                          if col in choices and state["owners"][str(choices[col])] == owner}

    state["next_id"] = max({0, *state["order"]}) + 1
    return validate(state)


def read_state():
    existing = {w["id"] for w in query("workspaces") if w["id"] > 0}
    raw = json.loads(STATE.read_text()) if STATE.exists() else None
    state = project_state(raw, existing)
    # A manually focused/created workspace is unowned, never adopted by a session.
    for ws in sorted(existing - set(state["order"])):
        state["order"].append(ws)
        state["owners"][str(ws)] = "neutral"
    state["next_id"] = max(state["next_id"], max({0, *existing}) + 1)
    return validate(state)


def load():
    state = read_state()
    save(state)
    return state


def cleanup(state):
    """Forget empty departed workspaces, including a session's last empty anchor.

    Hyprland destroys the actual empty workspace when it is left. Never change
    another monitor's visible empty workspace or stop a logical core session.
    """
    keep = occupied() | visible()
    state["order"] = [ws for ws in state["order"] if ws in keep]
    state["owners"] = {str(ws): owner_of(state, ws) for ws in state["order"]}
    state["preferred"] = {owner: ws for owner, ws in state["preferred"].items()
                          if ws in keep and str(ws) in state["owners"]}

    save(state)


def fresh_workspace(state, owner, after=None):
    existing = {w["id"] for w in query("workspaces") if w["id"] > 0}
    ws = max(state["next_id"], max({0, *existing, *state["order"]}) + 1)
    if ws > MAX_ID:
        raise RuntimeError("workspace ID limit exceeded")
    index = state["order"].index(after) + 1 if after in state["order"] else len(state["order"])
    state["next_id"] = ws + 1
    state["order"].insert(index, ws)
    state["owners"][str(ws)] = owner
    return ws


def discard_reservation(state, ws):
    # A failed/uncertain native acknowledgement must never adopt foreign windows.
    state["order"].remove(ws)
    state["owners"].pop(str(ws), None)
    state["preferred"] = {owner: value for owner, value in state["preferred"].items() if value != ws}

    save(state)


def select(state, ws, fresh=False, cleanup_after=True):
    # Persist ownership before focus so asynchronous compositor events see it.
    state["preferred"][owner_of(state, ws)] = ws
    save(state)
    try:
        if fresh:
            focus_empty(ws)
        else:
            focus(ws)
    except (RuntimeError, OSError, subprocess.CalledProcessError):
        if fresh:
            discard_reservation(state, ws)
        raise
    if cleanup_after:
        cleanup(state)


def cycle(state):
    current = active()
    if current <= 0:
        return
    cleanup(state)
    targets = [ws for ws in state["order"] if owner_of(state, ws) == owner_of(state, current)]
    if current in targets:
        select(state, targets[(targets.index(current) + 1) % len(targets)])


def create_empty(state):
    """Create after an occupied workspace, or leave an empty one for its predecessor."""
    current = active()
    if current <= 0:
        return
    cleanup(state)
    if current not in occupied():
        previous = [ws for ws in state["order"][:state["order"].index(current)]
                    if owner_of(state, ws) == owner_of(state, current)]
        if previous:
            select(state, previous[-1])
        return
    ws = fresh_workspace(state, owner_of(state, current), after=current)
    select(state, ws, fresh=True)


def movement_source(state):
    client = query("activewindow")
    ws, address = client.get("workspace", {}).get("id", 0), client.get("address")
    if ws <= 0 or not address:
        return None
    cleanup(state)
    return ws, address


def transfer(state, source, address, target, fresh=False):
    if source == target or owner_of(state, source) != owner_of(state, target):
        raise RuntimeError("unsafe workspace transfer")
    state["preferred"][owner_of(state, target)] = target
    save(state)
    try:
        if fresh:
            move_empty(target, address)
        else:
            move(target, address)
    except (RuntimeError, OSError, subprocess.CalledProcessError):
        if fresh:
            discard_reservation(state, target)
        raise
    cleanup(state)


def isolate_or_previous(state):
    source = movement_source(state)
    if source is None:
        return
    ws, address = source
    count = sum(c["workspace"]["id"] == ws for c in query("clients"))
    if count > 1:
        target = fresh_workspace(state, owner_of(state, ws), after=ws)
        transfer(state, ws, address, target, fresh=True)
        return
    occupied_ids = occupied()
    previous = [item for item in state["order"][:state["order"].index(ws)]
                if item in occupied_ids and owner_of(state, item) == owner_of(state, ws)]
    if previous:
        transfer(state, ws, address, previous[-1])


def move_next(state):
    source = movement_source(state)
    if source is None:
        return
    ws, address = source
    targets = [item for item in state["order"] if owner_of(state, item) == owner_of(state, ws)]
    if len(targets) > 1:
        target = targets[(targets.index(ws) + 1) % len(targets)]
        transfer(state, ws, address, target)


def closed(state, ws):
    if ws <= 0 or str(ws) not in state["owners"]:
        return
    for _ in range(40):
        if not any(c["workspace"]["id"] == ws for c in query("clients")):
            break
        time.sleep(0.05)
    else:
        return
    counts = occupied()
    if ws in counts:
        return
    candidates = [item for item in state["order"] if item in counts and owner_of(state, item) == owner_of(state, ws)]
    if active() == ws and candidates:
        index = state["order"].index(ws)
        previous = [item for item in state["order"][:index] if item in candidates]
        select(state, previous[-1] if previous else candidates[0])
    else:
        cleanup(state)  # Keep a visible empty workspace if this is the last one.


def snapshot():
    """Read-only ordered view for the bar, with the focused empty workspace included."""
    state = read_state()
    current = active()
    keep = occupied() | visible()
    rows = [ws for ws in state["order"] if ws in keep and owner_of(state, ws) == owner_of(state, current)]
    return {"active_workspace_id": current,
            "workspaces": [{"id": ws, "name": str(index)} for index, ws in enumerate(rows, 1)]}


def dismiss_scratchpad():
    """Consume navigation by hiding the focused monitor's special workspace."""
    monitors = query("monitors")
    monitor = next((item for item in monitors if item.get("focused")), None)
    if monitor is None and len(monitors) == 1:
        monitor = monitors[0]
    if monitor is None:
        raise RuntimeError("cannot determine focused monitor; refusing navigation")
    name = monitor.get("specialWorkspace", {}).get("name", "")
    if not name:
        return False
    if not re.fullmatch(r"special:[A-Za-z0-9_-]{1,100}", name):
        raise RuntimeError("unsafe special workspace name; refusing navigation")
    dispatch(f'hl.dsp.workspace.toggle_special("{name[len("special:"):]}")')
    return True


def main():
    args = sys.argv[1:]
    if not (len(args) == 1 and args[0] in ("cycle", "create-empty", "isolate-or-previous", "move-next", "cleanup", "snapshot", "migrate")
            or len(args) == 2 and args[0] in ("closed", "focus-workspace") and args[1].isdigit()):
        raise SystemExit("usage: workspace-columns.py cycle|create-empty|isolate-or-previous|move-next|cleanup|snapshot|migrate|closed ID|focus-workspace ID")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        command = args[0]
        if command in ("cycle", "create-empty", "focus-workspace") and dismiss_scratchpad():
            return
        if command == "snapshot":
            print(json.dumps(snapshot()))
            return
        state = load()
        if command == "cycle":
            cycle(state)
        elif command == "create-empty":
            create_empty(state)
        elif command == "isolate-or-previous":
            isolate_or_previous(state)
        elif command == "move-next":
            move_next(state)
        elif command == "cleanup":
            cleanup(state)
        elif command == "closed":
            closed(state, int(args[1]))
        elif command == "focus-workspace":
            cleanup(state)
            ws = int(args[1])
            if ws in state["order"] and owner_of(state, ws) == current_owner(state):
                select(state, ws)
        # "migrate" only saves the metadata projection. No compositor dispatch.


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"workspace-columns: {exc}", file=sys.stderr)
        sys.exit(1)
