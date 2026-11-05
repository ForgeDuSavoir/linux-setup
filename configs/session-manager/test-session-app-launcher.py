#!/usr/bin/env python3
"""Offline checks for the Session Manager Rofi bridge; no desktop programs are invoked."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

source = Path(__file__).with_name("session-app-launcher.py")
spec = importlib.util.spec_from_file_location("session_app_launcher", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rows():
    apps = [{"id": "a.desktop", "name": "One\nTwo", "icon": "icon", "origin": "installed"}]
    assert module.menu_rows(apps) == "One Two  (a.desktop)\0icon\x1ficon\n"
    assert module.menu_rows([]) == ""


def test_installed():
    assert module.launch_command({"id": "app.desktop", "origin": "installed"}) == ["gtk-launch", "app.desktop"]
    for ident in ("../bad.desktop", "bad/entry.desktop", "not-a-desktop"):
        try:
            module.launch_command({"id": ident, "origin": "installed"})
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid ID: {ident}")


def test_project(tmp_path):
    entry = tmp_path / ".session-manager/apps/local.desktop"
    entry.parent.mkdir(parents=True)
    entry.write_text("[Desktop Entry]\nType=Application\nName=Local\nExec=true\n")
    with patch.object(module, "selected_project_path", return_value=tmp_path):
        assert module.launch_command({"id": "local.desktop", "origin": "project"}) == ["gio", "launch", str(entry)]
        entry.unlink()
        entry.symlink_to("/tmp/other.desktop")
        try:
            module.launch_command({"id": "local.desktop", "origin": "project"})
        except ValueError:
            pass
        else:
            raise AssertionError("accepted a symlinked local desktop entry")


if __name__ == "__main__":
    import tempfile
    test_rows()
    test_installed()
    with tempfile.TemporaryDirectory() as directory:
        test_project(Path(directory))
    print("Session application launcher: offline checks passed")
