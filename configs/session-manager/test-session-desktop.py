#!/usr/bin/env python3
"""Fake desktop and logical daemon for the downstream session client."""
import fcntl
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time

SOURCE = Path(__file__).with_name("session-desktop.py")
os.environ["SESSION_COLUMNS_SCRIPT"] = str(SOURCE.parents[1] / "hypr/files/Scripts/workspace-columns.py")
spec = importlib.util.spec_from_file_location("session_desktop", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SESSION = "12345678-1234-1234-1234-123456789abc"

with tempfile.TemporaryDirectory(prefix="session-desktop-") as temp:
    root = Path(temp)
    module.columns.RUNTIME = root
    module.columns.STATE = root / "workspace-columns.json"
    module.columns.STATE.write_text('{}')
    state = {"version": 2, "last": {}, "origins": {},
             "owners": {"1": "neutral"}, "preferred": {}}
    clients = [{"workspace": {"id": 1, "name": "1"}}]
    monitors = [{"specialWorkspace": {"name": ""}}]
    active_ws = [1]
    sessions = []
    selected = [None]
    events = []
    original_load = module.columns.load
    original_save = module.columns.save
    module.columns.load = lambda: state
    module.columns.save = lambda value: events.append(("save", dict(value["owners"])))
    module.columns.focus = lambda ws: (events.append(("focus", ws)), active_ws.__setitem__(0, ws))
    module.columns.active = lambda: active_ws[0]
    module.columns.query = lambda key: {"clients": clients, "monitors": monitors,
                                         "workspaces": [{"id": active_ws[0]}]}[key]
    def hide(expression):
        events.append(("hide", expression))
        monitors[0]["specialWorkspace"]["name"] = ""
    module.columns.dispatch = hide

    def request(*args):
        events.append(("request", args))
        if args == ("list",):
            return {"sessions": [{"id": item} for item in sessions], "active_session_id": selected[0]}
        if args == ("start", "Project"):
            sessions.append(SESSION)
            selected[0] = SESSION
            return {"session": {"id": SESSION}}
        if args == ("switch", SESSION):
            selected[0] = SESSION
            return {"session": {"id": SESSION}}
        if args == ("deactivate",):
            selected[0] = None
            return {"active_session_id": None}
        if args == ("stop", SESSION):
            sessions.remove(SESSION)
            if selected[0] == SESSION:
                selected[0] = None
            return {"stopped_session_id": SESSION}
        raise AssertionError(args)

    module.request = request
    module.invoke("start", "Project")
    assert state["owners"] == {"1": "neutral", "2": SESSION}
    assert active_ws[0] == 3
    assert clients == [{"workspace": {"id": 1, "name": "1"}}]
    module.invoke("deactivate")
    assert selected == [None] and active_ws[0] == 1
    monitors[0]["specialWorkspace"]["name"] = f"special:sm-{SESSION}-ai"
    before = len(events)
    module.invoke("switch", SESSION)
    assert events[before] == ("request", ("list",))
    assert events[before + 1] == ("hide", f'hl.dsp.workspace.toggle_special("sm-{SESSION}-ai")')
    assert events[before + 2] == ("request", ("switch", SESSION))
    assert active_ws[0] == 3 and monitors[0]["specialWorkspace"]["name"] == ""
    # Even a shared/global scratchpad is hidden before a context change.
    monitors[0]["specialWorkspace"]["name"] = "special:global"
    module.invoke("deactivate")
    assert ("hide", 'hl.dsp.workspace.toggle_special("global")') in events
    module.invoke("switch", SESSION)
    assert active_ws[0] == 3
    monitors[0]["specialWorkspace"]["name"] = 'special:bad"name'
    before = list(events)
    try:
        module.invoke("deactivate")
        raise AssertionError("untrusted compositor name must not enter a dispatcher")
    except RuntimeError as exc:
        assert "unsafe special workspace" in str(exc)
    assert selected[0] == SESSION and not any(event[0] == "hide" for event in events[len(before):])
    monitors[0]["specialWorkspace"]["name"] = "special:session-ai"
    module.columns.dispatch = lambda expression: events.append(("hide", expression))
    try:
        module.invoke("deactivate")
        raise AssertionError("failed hide must not change logical context")
    except RuntimeError as exc:
        assert "did not hide" in str(exc)
    assert selected[0] == SESSION
    monitors[0]["specialWorkspace"]["name"] = ""
    module.columns.dispatch = hide
    clients.append({"workspace": {"id": 3, "name": "3"}})
    before = list(events)
    try:
        module.invoke("stop", SESSION)
        raise AssertionError("stop should refuse an ordinary window")
    except RuntimeError as exc:
        assert "open windows" in str(exc)
    assert events[len(before):] == [("request", ("list",))]
    clients.pop()
    clients.append({"workspace": {"id": -9, "name": f"special:sm-{SESSION}-ai"}})
    monitors[0]["specialWorkspace"]["name"] = f"special:sm-{SESSION}-ai"
    try:
        module.invoke("stop", SESSION)
        raise AssertionError("stop should refuse a hidden scratchpad window")
    except RuntimeError as exc:
        assert "open windows" in str(exc)
    assert monitors[0]["specialWorkspace"]["name"] == "" and sessions == [SESSION]
    clients.pop()
    module.invoke("stop", SESSION)
    assert selected == [None] and state["owners"] == {"1": "neutral"}
    assert active_ws[0] == 1
    monitors.append({"specialWorkspace": {"name": ""}})
    before = list(events)
    try:
        module.invoke("start", "Project")
        raise AssertionError("multiple monitors must fail before any mutation")
    except RuntimeError as exc:
        assert "one monitor" in str(exc)
    assert events == before
    assert all(event[0] != "move" for event in events)

    # The first menu action after login must initialize metadata without
    # invoking the old workspace migration, even with pre-existing windows.
    monitors.pop()
    module.columns.STATE.unlink()
    module.columns.load = original_load
    module.columns.save = original_save
    events.clear()
    module.invoke("start", "Project")
    persisted = module.columns.load()
    assert persisted["owners"] == {"1": "neutral", "2": SESSION}
    assert clients == [{"workspace": {"id": 1, "name": "1"}}]
    module.invoke("deactivate")
    assert active_ws[0] == 1
    # A persisted logical session after a graphical restart has no old
    # workspace mapping. Selecting it allocates an empty column on demand.
    module.columns.STATE.unlink()
    sessions[:] = [SESSION]
    selected[0] = SESSION
    module.invoke("switch", SESSION)
    assert module.columns.load()["owners"] == {"1": "neutral", "2": SESSION}
    assert active_ws[0] == 3
    assert clients == [{"workspace": {"id": 1, "name": "1"}}]
    focus = module.columns.focus
    module.columns.focus = lambda ws: (_ for _ in ()).throw(RuntimeError("focus failed"))
    try:
        module.invoke("deactivate")
        raise AssertionError("a failed focus must not be reported as success")
    except RuntimeError as exc:
        assert str(exc) == "focus failed"
    assert selected[0] is None and module.columns.load()["owners"]["2"] == SESSION
    module.columns.focus = focus
    module.invoke("deactivate")
    assert active_ws[0] == 1

    # The menu must wait for the workspace controller's lock before it reads
    # state or sends any core mutation, not race with a compaction in progress.
    errors = []
    started = threading.Event()
    with (root / "workspace-columns.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before = list(events)
        def invoke_blocked():
            started.set()
            try:
                module.invoke("deactivate")
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=invoke_blocked)
        thread.start()
        assert started.wait(2)
        time.sleep(0.05)
        assert events == before
        fcntl.flock(lock, fcntl.LOCK_UN)
    thread.join(timeout=3)
    assert not thread.is_alive() and not errors
    assert events != before

print("Session desktop isolation, neutral return and window guards passed using fake IPC.")
