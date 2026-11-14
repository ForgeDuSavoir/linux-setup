#!/usr/bin/env python3
"""Show Session Manager's current applications in Rofi and launch a selected desktop entry."""

import html
import json
from pathlib import Path
import subprocess
import sys

MANAGER = Path.home() / ".local/bin/session-manager"
THEME = Path.home() / ".config/rofi/project-launcher.rasi"


def query(*args):
    result = subprocess.run([str(MANAGER), "--json", *args], check=True, capture_output=True, text=True, timeout=35)
    return json.loads(result.stdout)


def desktop_metadata(app, project=None):
    # Read presentation metadata through the desktop library, never execute Exec.
    # Core eligibility/overrides remain authoritative: this cannot add an app.
    from gi.repository import Gio
    if app["origin"] == "installed":
        entry = Gio.DesktopAppInfo.new(app["id"])
    elif app["origin"] == "project" and project is not None:
        path = project / ".session-manager/apps" / app["id"]
        entry = None if path.is_symlink() else Gio.DesktopAppInfo.new_from_filename(str(path))
    else:
        entry = None
    if entry is None:
        return {"name": app["name"], "generic": "", "keywords": [], "comment": ""}
    return {"name": entry.get_name(), "generic": entry.get_generic_name() or "",
            "keywords": entry.get_keywords() or [], "comment": entry.get_description() or ""}


def clean_text(value):
    return "".join(char if ord(char) >= 32 and ord(char) != 127 else " " for char in value)


def menu_rows(applications, metadata=None):
    rows = []
    for app in applications:
        info = metadata(app) if metadata else {"name": app["name"], "generic": "", "keywords": [], "comment": ""}
        label = html.escape(clean_text(info["name"]))
        if info["generic"]:
            label += " <span weight='light' size='small'><i>(" + html.escape(clean_text(info["generic"])) + ")</i></span>"
        # Rofi's meta field is searchable but not rendered. Match drun's extra
        # metadata without putting keywords or raw desktop-entry IDs in labels.
        search = clean_text(" ".join(value for value in [info["generic"], info["comment"], *info["keywords"], app["id"]] if value))
        fields = ["meta", search]
        icon = app.get("icon") or ""
        if icon and not any(ord(char) < 32 for char in icon):
            fields += ["icon", icon]
        rows.append(label + "\0" + "\x1f".join(fields))
    return "\n".join(rows) + ("\n" if rows else "")


def selected_project_path():
    state = query("session", "list")
    active = state.get("active_session_id")
    session = next((item for item in state["sessions"] if item["id"] == active), None)
    if session is None:
        return None
    projects = query("project", "list")["projects"]
    return next((Path(item["path"]) for item in projects if item["name"] == session["project_name"]), None)


def launch_command(app):
    entry_id = app["id"]
    if not entry_id.endswith(".desktop") or "/" in entry_id or "\\" in entry_id or entry_id in (".", ".."):
        raise ValueError("invalid desktop-entry ID")
    if app["origin"] == "installed":
        return ["gtk-launch", entry_id]
    if app["origin"] != "project":
        raise ValueError("unknown application origin")
    project = selected_project_path()
    if project is None:
        raise ValueError("project was removed; reopen the launcher")
    entry = project / ".session-manager" / "apps" / entry_id
    if entry.is_symlink() or not entry.is_file():
        raise ValueError("project desktop entry is no longer available")
    return ["gio", "launch", str(entry)]


def launch_browser():
    applications = query("application", "list")["applications"]
    browser = next((app for app in applications if app["id"] == "firefox.desktop"), None)
    if browser is None:
        raise ValueError("Firefox is unavailable in the current context")
    subprocess.run(launch_command(browser), check=True, timeout=30)
    return 0


def main():
    if sys.argv[1:] == ["--browser"]:
        return launch_browser()
    if sys.argv[1:]:
        raise ValueError("usage: session-app-launcher [--browser]")
    applications = query("application", "list")["applications"]
    if not applications:
        return 0
    project = selected_project_path() if any(app["origin"] == "project" for app in applications) else None
    choice = subprocess.run(
        ["rofi", "-dmenu", "-markup-rows", "-i", "-no-custom", "-show-icons", "-format", "i", "-theme", str(THEME), "-p", "Apps"],
        input=menu_rows(applications, lambda app: desktop_metadata(app, project)),  text=True, capture_output=True, check=False,
    )
    if choice.returncode != 0:
        return 0  # Escape or an empty selection changes nothing.
    index = int(choice.stdout.strip())
    if not 0 <= index < len(applications):
        raise ValueError("invalid launcher selection")
    subprocess.run(launch_command(applications[index]), check=True, timeout=30)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"Session application launcher: {error}", file=sys.stderr)
        sys.exit(1)
