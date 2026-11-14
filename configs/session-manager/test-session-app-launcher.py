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
    assert module.menu_rows(apps) == "One Two\0meta\x1fa.desktop\x1ficon\x1ficon\n"
    assert module.menu_rows([]) == ""


def test_metadata(tmp_path):
    app = {"id": "calculator.desktop", "name": "Qalculate!", "origin": "project"}
    folder = tmp_path / '.session-manager/apps'
    folder.mkdir(parents=True)
    (folder / app['id']).write_text('[Desktop Entry]\nType=Application\nName=Qalculate!\nGenericName=Calculator\nKeywords=calculation;arithmetic;\nExec=true\n')
    metadata = module.desktop_metadata(app, tmp_path)
    assert metadata["generic"] == "Calculator"
    row = module.menu_rows([app], lambda _: metadata)
    assert "<i>(Calculator)</i>" in row
    assert "calculation" in row.split("\0meta\x1f")[1]
    malicious = {"name": "<b>&", "generic": "<script>", "comment": "bad\0value", "keywords": []}
    row = module.menu_rows([app], lambda _: malicious)
    assert "&lt;b&gt;&amp;" in row and "&lt;script&gt;" in row
    assert row.count("\0") == 1


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


def test_browser():
    for origin in ("installed", "project"):
        browser = {"id": "firefox.desktop", "origin": origin}
        with patch.object(module, "query", return_value={"applications": [browser]}), \
             patch.object(module, "launch_command", return_value=["fake-launch", origin]) as command, \
             patch.object(module.subprocess, "run") as run:
            assert module.launch_browser() == 0
            command.assert_called_once_with(browser)
            run.assert_called_once_with(["fake-launch", origin], check=True, timeout=30)
    with patch.object(module, "query", return_value={"applications": []}), \
         patch.object(module.subprocess, "run") as run:
        try:
            module.launch_browser()
        except ValueError:
            pass
        else:
            raise AssertionError("missing browser must fail without launching a default profile")
        run.assert_not_called()


if __name__ == "__main__":
    import tempfile
    test_rows()
    test_installed()
    test_browser()
    with tempfile.TemporaryDirectory() as directory:
        test_project(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        test_metadata(Path(directory))
    print("Session application launcher: offline checks passed")
