#!/usr/bin/env python3
"""Pure Hyprland stub for the two-row workspace controller."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / "files/Scripts/workspace-columns.py"
spec = importlib.util.spec_from_file_location("columns", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Desktop:
    def __init__(self, clients, active):
        self.clients = clients
        self.ws = {client["workspace"]["id"] for client in clients if client["workspace"]["id"] > 0}
        self.active = active
        self.focused = clients[-1]["address"] if clients else None
        self.ws.add(active)
        self.transitions = []

    def query(self, name):
        if name == "clients":
            return self.clients
        if name == "workspaces":
            return [{"id": ws, "windows": sum(c["workspace"]["id"] == ws for c in self.clients)} for ws in sorted(self.ws)]
        if name == "activeworkspace":
            return {"id": self.active}
        if name == "activewindow":
            return next((c for c in self.clients if c["address"] == self.focused), {})
        raise AssertionError(name)

    def focus(self, ws, vertical=False):
        self.transitions.append(("focus", ws, vertical))
        self.ws.add(ws)
        self.active = ws
        self.focused = next((c["address"] for c in self.clients if c["workspace"]["id"] == ws), None)
        self.ws = {i for i in self.ws if i == ws or any(c["workspace"]["id"] == i for c in self.clients)}

    def move(self, ws, address=None, follow=True, vertical=False):
        self.transitions.append(("move", ws, vertical))
        address = address or self.focused
        client = next(c for c in self.clients if c["address"] == address)
        client["workspace"] = {"id": ws, "name": str(ws)}
        self.ws.add(ws)
        if follow:
            self.focus(ws)
        else:
            self.ws = {i for i in self.ws if i == self.active or any(c["workspace"]["id"] == i for c in self.clients)}

    def change_id(self, old, new):
        assert old in self.ws and new not in self.ws, (old, new, self.ws)
        self.ws.remove(old)
        self.ws.add(new)
        for client in self.clients:
            if client["workspace"]["id"] == old:
                client["workspace"] = {"id": new, "name": str(new)}
        if self.active == old:
            self.active = new


def client(addr, ws, name=None):
    return {"address": addr, "workspace": {"id": ws, "name": name or str(ws)}}


def setup(desktop, path):
    module.RUNTIME = path
    module.STATE = path / "workspace-columns.json"
    module.query = desktop.query
    module.focus = desktop.focus
    module.move = desktop.move
    module.change_id = desktop.change_id
    module.rename = lambda ws: None
    return {"version": 2, "last": {}, "origins": {}}


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    # Migration preserves every window, including a legacy scratchpad window.
    desktop = Desktop([client("a", 1), client("b", 2), client("c", -90, "special:workspace-2")], 2)
    state = setup(desktop, root)
    module.migrate()
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 1, "b": 3, "c": 4}
    assert desktop.active == 3
    before_upgrade = list(desktop.transitions)
    upgraded = module.load()
    assert upgraded["owners"] == {"1": "neutral", "2": "neutral"}
    assert desktop.transitions == before_upgrade  # metadata upgrade cannot dispatch

    # Empty row persists logically, and each column retains its own row.
    module.toggle_row(state)
    assert desktop.active == 4
    assert desktop.transitions[-1] == ("focus", 4, True)
    module.cycle(state)
    assert desktop.active == 1
    assert desktop.transitions[-1] == ("focus", 1, False)
    module.cycle(state)
    assert desktop.active == 4
    assert desktop.transitions[-1] == ("focus", 4, False)
    module.move_row(state)
    assert desktop.active == 3
    assert desktop.transitions[-2] == ("move", 3, True)

    # Split a pair of windows into a new column inserted before old column 2.
    desktop = Desktop([client("a", 1), client("b", 1), client("c", 3)], 1)
    desktop.focused = "b"
    state = setup(desktop, root)
    module.move_next(state)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 1, "b": 3, "c": 5}
    assert sorted(module.occupied_columns()) == [1, 2, 3]
    # Moving the isolated window again joins the next column.
    module.move_next(state)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 1, "b": 3, "c": 3}

    # Regression: a single window on row 2 must be isolated when row 1 of
    # the same column also contains a window. Restore row 1 when returning.
    desktop = Desktop([client("a", 1), client("b", 2), client("c", 3)], 2)
    desktop.focused = "b"
    state = setup(desktop, root)
    state["last"] = {"1": 2, "2": 1}
    module.move_next(state)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 1, "b": 4, "c": 5}
    assert desktop.active == 4
    assert state["last"] == {"1": 1, "2": 2, "3": 1}
    module.cycle(state)
    assert desktop.active == 5
    module.cycle(state)
    assert desktop.active == 1
    # A window that is already alone in its column joins the line last
    # displayed in the next column, not necessarily its own source line.
    desktop = Desktop([client("a", 2), client("b", 3)], 2)
    desktop.focused = "a"
    state = setup(desktop, root)
    state["last"] = {"1": 2, "2": 2}
    module.move_next(state)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 2, "b": 1}
    assert desktop.active == 2

    # Closing one line reveals the other; closing both compacts columns.
    desktop = Desktop([client("a", 1), client("b", 3), client("c", 4), client("d", 5)], 3)
    state = setup(desktop, root)
    desktop.clients = [c for c in desktop.clients if c["address"] != "b"]
    module.closed(state, 3)
    assert desktop.active == 4
    assert desktop.transitions[-1] == ("focus", 4, True)
    desktop.clients = [c for c in desktop.clients if c["address"] != "c"]
    module.closed(state, 4)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {"a": 1, "d": 3}
    assert desktop.active == 1

# Navigation and insertion never target another session's column.
with tempfile.TemporaryDirectory() as directory:
    desktop = Desktop([client("neutral", 1), client("session-a", 3), client("session-b", 3)], 3)
    desktop.focused = "session-b"
    state = setup(desktop, Path(directory))
    state["owners"] = {"1": "neutral", "2": "session-uuid"}
    state["preferred"] = {"session-uuid": 2}
    module.cycle(state)
    assert desktop.active == 3
    desktop.focused = "session-b"
    module.move_next(state)
    assert desktop.clients[0]["workspace"]["id"] == 1
    assert state["owners"] == {"1": "neutral", "2": "session-uuid", "3": "session-uuid"}
    assert state["preferred"]["session-uuid"] == 2
    assert desktop.clients[2]["workspace"]["id"] == 5
    module.cycle(state)
    assert desktop.active == 3
    # A lone session window cannot be merged into the neutral column.
    desktop.focused = "session-b"
    module.move_next(state)
    assert desktop.clients[2]["workspace"]["id"] == 3
    assert desktop.clients[0]["workspace"]["id"] == 1
    # Last session window closes: never fall back to occupied neutral windows.
    desktop.clients = [c for c in desktop.clients if c["address"] == "neutral"]
    desktop.active = 3
    module.closed(state, 3)
    assert desktop.active == 3
    assert "session-uuid" in state["owners"].values()

with tempfile.TemporaryDirectory() as directory:
    desktop = Desktop([client("neutral", 1), client("session-a", 3), client("session-b", 5)], 1)
    state = setup(desktop, Path(directory))
    state["owners"] = {"1": "neutral", "2": "session-uuid", "3": "session-uuid"}
    state["preferred"] = {"neutral": 1, "session-uuid": 3}
    desktop.clients = [c for c in desktop.clients if c["address"] != "session-a"]
    desktop.ws.remove(3)  # Hyprland discards an unfocused, now-empty workspace.
    module.closed(state, 3)
    assert {c["address"]: c["workspace"]["id"] for c in desktop.clients} == {
        "neutral": 1, "session-b": 3}
    assert state["owners"] == {"1": "neutral", "2": "session-uuid"}
    assert state["preferred"] == {"neutral": 1, "session-uuid": 2}
    assert desktop.active == 1

calls = []
module.ctl = lambda *args: calls.append(args)
module.vertical_dispatch("hl.dsp.focus({ workspace = 2 })", 2)
module.vertical_dispatch("hl.dsp.focus({ workspace = 1 })", 1)
for (_, code), direction in zip(calls, ("bottom", "top")):
    vertical = f'style = "slidevert {direction}"'
    horizontal = 'style = "slide"'
    assert code.index(vertical) < code.index("hl.dispatch(") < code.index(horizontal)
    assert "pcall(function()" in code and "if not ok then error(err) end" in code

print("Workspace migration, navigation, animation routing, insertion and closure tests passed.")
