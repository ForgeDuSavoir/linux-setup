#!/usr/bin/env python3
"""Two ordinary Hyprland workspaces per dynamic column.

Odd IDs are the upper row; even IDs are the lower row. Empty rows are logical:
Hyprland may destroy their workspace until it is focused or receives a window.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "hyprland"
STATE = RUNTIME / "workspace-columns.json"


def ctl(*args):
    result = subprocess.run(["hyprctl", *map(str, args)], text=True, capture_output=True, check=True)
    if result.stdout.startswith("error:"):
        raise RuntimeError(result.stdout)
    return result.stdout


def query(name):
    return json.loads(ctl(name, "-j"))


def dispatch(expression):
    ctl("dispatch", expression)


def vertical_dispatch(expression, target_row):
    """Set the style only for this compositor-side switch, then restore it.

    Hyprland starts the outgoing and incoming workspace animations during
    hl.dispatch; both read the style at that point. No timer or global style
    change survives the dispatch, so column changes retain their slide style.
    """
    direction = "bottom" if target_row == 2 else "top"

    def animation(style):
        return ('hl.animation({ leaf = "workspaces", enabled = true, '
                f'speed = 5, bezier = "wind", style = "{style}" }})')

    code = (
        f'{animation("slidevert " + direction)}; '
        f'local ok, err = pcall(function() hl.dispatch({expression}) end); '
        f'{animation("slide")}; '
        'if not ok then error(err) end'
    )
    ctl("eval", code)


def focus(ws, vertical=False):
    expression = f"hl.dsp.focus({{ workspace = {ws} }})"
    if vertical:
        vertical_dispatch(expression, row_of(ws))
    else:
        dispatch(expression)


def move(ws, address=None, follow=True, vertical=False):
    window = f', window = "address:{address}"' if address else ""
    follow_arg = ", follow = false" if not follow else ""
    expression = f"hl.dsp.window.move({{ workspace = {ws}{window}{follow_arg} }})"
    if vertical and follow:
        vertical_dispatch(expression, row_of(ws))
    else:
        dispatch(expression)


def change_id(old, new):
    dispatch(f"hl.dsp.workspace.change_id({{ workspace = {old}, id = {new} }})")
    for _ in range(40):
        if new in [w["id"] for w in query("workspaces")]:
            return
        time.sleep(0.025)
    raise RuntimeError(f"workspace {old} did not become {new}")


def rename(ws):
    dispatch(f'hl.dsp.workspace.rename({{ workspace = {ws}, name = "{ws}" }})')


def workspace_id(column, row=1):
    return 2 * column - 2 + row


def column_of(ws):
    return (ws + 1) // 2


def row_of(ws):
    return 1 if ws % 2 else 2


def occupied():
    return {w["id"]: w["windows"] for w in query("workspaces") if w["id"] > 0 and w["windows"] > 0}


def occupied_columns(state=None, owner=None):
    columns = sorted({column_of(w) for w in occupied()})
    if state is not None and owner is not None:
        return [col for col in columns if state.get("owners", {}).get(str(col), "neutral") == owner]
    return columns


def owner_of(state, col):
    return state.get("owners", {}).get(str(col), "neutral")


def current_owner(state):
    ws = active()
    return owner_of(state, column_of(ws)) if ws > 0 else "neutral"


def save(state):
    STATE.write_text(json.dumps(state))


def migrate():
    """One-time migration from numbered workspaces and workspace scratchpads."""
    old = {w["id"]: w for w in query("workspaces") if w["id"] > 0 and w["windows"] > 0}
    original_clients = {c["address"] for c in query("clients")}
    old_order_file = RUNTIME / "workspace-order"
    stored = [int(v) for v in old_order_file.read_text().split() if v.isdigit()] if old_order_file.exists() else []
    order = [i for i in stored if i in old] + [i for i in sorted(old) if i not in stored]
    if not order:
        save({"version": 2, "last": {}, "origins": {}})
        return
    active = query("activeworkspace")["id"]
    # Park all old workspaces outside both the source and destination ranges.
    base = max([*old, 2 * len(order)]) + len(order) + 1
    for index, old_id in enumerate(order):
        change_id(old_id, base + index)
    for index, old_id in enumerate(order, 1):
        target = workspace_id(index)
        change_id(base + index - 1, target)
        rename(target)
        old_scratchpad = f"special:workspace-{old_id}"
        for client in query("clients"):
            if client["workspace"]["name"] == old_scratchpad:
                move(target + 1, client["address"], follow=False)
    save({"version": 2, "last": {}, "origins": {}})
    if active in order:
        focus(workspace_id(order.index(active) + 1))
    missing = original_clients - {c["address"] for c in query("clients")}
    if missing:
        raise RuntimeError(f"migration lost windows: {missing}")


def load():
    if not STATE.exists():
        migrate()
    state = json.loads(STATE.read_text())
    if state.get("version") != 2:
        raise RuntimeError("unsupported workspace state; refusing to alter windows")
    # Existing columns and historical scratchpads belong to the neutral context.
    # This metadata upgrade only records ownership; it does not dispatch to Hyprland.
    if "owners" not in state:
        cols = set(occupied_columns())
        if active() > 0:
            cols.add(column_of(active()))
        state["owners"] = {str(col): "neutral" for col in sorted(cols)}
        save(state)
    return state


def compact(state, order=None):
    """Renumber occupied columns without ever assigning an occupied ID."""
    columns = occupied_columns()
    # A registered empty session column must not be reused while that session is open.
    # Preserve unknown, externally focused empty columns as neutral rather than
    # silently assigning their ID to another session during compaction.
    reserved = {int(c) for c in state.get("owners", {})}
    if "owners" in state:
        reserved |= {column_of(w["id"]) for w in query("workspaces") if w["id"] > 0}
    columns = sorted(set(columns) | reserved)
    order = [c for c in (order or columns) if c in columns]
    order += [c for c in columns if c not in order]
    existing = {w["id"] for w in query("workspaces") if w["id"] > 0}
    base = max([*existing, 2 * len(order), 0]) + 2 * len(order) + 2
    parked = []
    for new_col, old_col in enumerate(order, 1):
        for row in (1, 2):
            src = workspace_id(old_col, row)
            if src not in existing:
                continue
            dest = workspace_id(new_col, row)
            if src == dest:
                continue
            temp = base + len(parked)
            change_id(src, temp)
            parked.append((temp, dest))
    for temp, dest in parked:
        change_id(temp, dest)
    for col in range(1, len(order) + 1):
        for row in (1, 2):
            ws = workspace_id(col, row)
            if ws in [w["id"] for w in query("workspaces")]:
                rename(ws)
    previous_last = state["last"]
    state["last"] = {str(index): previous_last.get(str(col), 1) for index, col in enumerate(order, 1)}
    if "owners" in state:
        previous_owners = state["owners"]
        state["owners"] = {str(index): previous_owners.get(str(col), "neutral")
                           for index, col in enumerate(order, 1)}
    if "preferred" in state:
        state["preferred"] = {owner: order.index(col) + 1 for owner, col in state["preferred"].items()
                              if col in order}
    previous_origins = state["origins"]
    state["origins"] = {addr: order.index(col) + 1 for addr, col in previous_origins.items() if col in order}
    save(state)
    return {old: index for index, old in enumerate(order, 1)}


def active():
    return query("activeworkspace")["id"]


def cycle(state):
    current = column_of(active())
    cols = occupied_columns(state, current_owner(state))
    if not cols:
        return
    next_col = next((col for col in cols if col > current), cols[0])
    row = state["last"].get(str(next_col), 1)
    focus(workspace_id(next_col, row))
    state["last"][str(next_col)] = row
    save(state)


def toggle_row(state):
    current = active()
    if current <= 0:
        return
    col, row = column_of(current), 3 - row_of(current)
    focus(workspace_id(col, row), vertical=True)
    state["last"][str(col)] = row
    save(state)


def move_row(state):
    client = query("activewindow")
    ws = client.get("workspace", {}).get("id", 0)
    if ws <= 0:
        return
    col, row = column_of(ws), 3 - row_of(ws)
    move(workspace_id(col, row), vertical=True)
    state["last"][str(col)] = row
    save(state)


def move_next(state):
    client = query("activewindow")
    ws, address = client.get("workspace", {}).get("id", 0), client.get("address")
    if ws <= 0 or not address:
        return
    col, row = column_of(ws), row_of(ws)
    clients = query("clients")
    # A column may have one window on each line. In that case the focused
    # line has only one window, but the column is not empty after isolation.
    count = sum(c["workspace"]["id"] > 0 and column_of(c["workspace"]["id"]) == col for c in clients)
    if count > 1:
        order = sorted(set(occupied_columns()) | {int(c) for c in state.get("owners", {})})
        temp_col = max([*order, col]) + len(order) + 2
        move(workspace_id(temp_col, row))
        # If the source line is now empty, its column should reopen on the
        # other (occupied) line rather than on an empty workspace.
        if workspace_id(col, row) not in occupied():
            state["last"][str(col)] = 3 - row
        order.insert(order.index(col) + 1, temp_col)
        state["last"][str(temp_col)] = row
        if "owners" in state:
            state["owners"][str(temp_col)] = owner_of(state, col)
        state["origins"][address] = col
        compact(state, order)
        return
    cols = occupied_columns(state, owner_of(state, col))
    origin = state["origins"].get(address, col)
    targets = [c for c in cols if c != col]
    if not targets:
        return
    target = next((c for c in targets if c > origin), targets[0])
    move(workspace_id(target, state["last"].get(str(target), 1)))
    state["origins"].pop(address, None)
    compact(state)


def closed(state, closed_ws):
    if closed_ws <= 0:
        return
    for _ in range(40):
        if not any(c["workspace"]["id"] == closed_ws for c in query("clients")):
            break
        time.sleep(0.05)
    else:
        return
    col, row = column_of(closed_ws), row_of(closed_ws)
    counts = occupied()
    if closed_ws in counts:
        return
    other = workspace_id(col, 3 - row)
    if other in counts:
        if active() == closed_ws:
            focus(other, vertical=True)
            state["last"][str(col)] = 3 - row
        save(state)
        return
    cols = occupied_columns(state, owner_of(state, col))
    if active() == closed_ws and cols:
        target = next((c for c in reversed(cols) if c < col), None)
        target = target if target is not None else next((c for c in cols if c > col), None)
        if target:
            focus(workspace_id(target, state["last"].get(str(target), 1)))
    if "owners" in state and any(owner_of(state, c) == owner_of(state, col)
                                  for c in occupied_columns() if c != col):
        state["owners"].pop(str(col), None)
    if occupied_columns() or state.get("owners"):
        compact(state)
    else:
        save(state)


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load()
        command = sys.argv[1] if len(sys.argv) > 1 else ""
        if command == "cycle":
            cycle(state)
        elif command == "toggle-row":
            toggle_row(state)
        elif command == "move-row":
            move_row(state)
        elif command == "move-next":
            move_next(state)
        elif command == "closed" and len(sys.argv) == 3:
            closed(state, int(sys.argv[2]))
        elif command == "focus-column" and len(sys.argv) == 3:
            col = int(sys.argv[2])
            if col in occupied_columns(state, current_owner(state)):
                focus(workspace_id(col, state["last"].get(str(col), 1)))
        elif command == "migrate":
            pass  # load() performed the one-time migration.
        else:
            raise SystemExit("usage: workspace-columns.py cycle|toggle-row|move-row|move-next|closed ID|focus-column ID|migrate")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"workspace-columns: {exc}", file=sys.stderr)
        sys.exit(1)
