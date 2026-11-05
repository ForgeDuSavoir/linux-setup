#!/usr/bin/env python3
"""Show Session Manager's current applications in Rofi and launch a selected desktop entry."""

import json
from pathlib import Path
import subprocess
import sys

MANAGER = Path.home() / ".local/bin/session-manager"
THEME = Path.home() / ".config/rofi/project-launcher.rasi"


def query(*args):
    result = subprocess.run([str(MANAGER), "--json", *args], check=True, capture_output=True, text=True, timeout=35)
    return json.loads(result.stdout)


def menu_rows(applications):
    rows = []
    for app in applications:
        label = f"{app['name']}  ({app['id']})".replace("\n", " ").replace("\r", " ")
        icon = app.get("icon") or ""
        if icon and not any(ord(char) < 32 for char in icon):
            label += f"\0icon\x1f{icon}"
        rows.append(label)
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


def main():
    applications = query("application", "list")["applications"]
    if not applications:
        return 0
    choice = subprocess.run(
        ["rofi", "-dmenu", "-i", "-no-custom", "-show-icons", "-format", "i", "-theme", str(THEME), "-p", "Apps"],
        input=menu_rows(applications), text=True, capture_output=True, check=False,
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
