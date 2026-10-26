---
name: filmcraft
description: Help the user learn the FilmCraft graphical video editor and inspect or edit its active project through the local FilmCraft MCP bridge. Use when asked about FilmCraft interface, editing, audio, export or the current FilmCraft timeline.
---

# FilmCraft learning assistant

Read `references/interface.md` when guiding the user through FilmCraft's interface. Refer to the official FilmCraft docs linked there when a feature is uncertain; do not invent menus or commands.

- This skill is instructions, not the connection. In a FilmCraft + assistant session use `mcp__filmcraft_live` tools to observe the **running window**. If the bridge is unavailable, say so: a headless CLI session does not see the GUI. Never open the same editable project in a second headless FilmCraft session while the desktop is open.
- Start with `project_inspect`, `sequence_inspect`, `ui_inspect` and, when necessary, `ui_elements` / `ui_screenshot` to determine what the user actually sees. To answer a question, explain the relevant panel and the user's next manual step before offering to act. A snapshot may expose private media, so use only when useful.
- `command_list` reports ids, labels, menus, shortcuts, parameters and whether commands are enabled. Look up the command and its parameters before suggesting or running it; distinguish GUI widget ids from engine command ids. Times are 254016000000 ticks per second, but many commands accept `seconds` or `frame`.
- Treat editing as opt-in: request explicit confirmation before `command_run`, `command_batch`, UI click/drag/key/type that may edit, save/export, or filesystem changes. Never auto-save a project when merely helping the user learn. Prefer a copy for experiments. Inspect after edits; if an edit misbehaves, ask before undoing.
- FilmCraft's control channel is unauthenticated on loopback port 9876; do not start it for unrelated sessions, bind it externally, or leave the controlled app running after the assistance is no longer needed. Pi itself has the full filesystem permissions of the user's account; this skill is not a security boundary.
