---
name: photocraft
description: Inspect, edit, and save PhotoCraft image documents through the local PhotoCraft MCP server. Use when asked to automate PhotoCraft files or a live PhotoCraft window.
---

# PhotoCraft with Pi

- Two Pi MCP servers are configured: `photocraft` (headless, on by default) and `photocraft_live` (disabled by default). Never assume a headless document appears in the GUI.
- For a live document, ask the user to launch `photocraft-ai`, enable `photocraft_live` in `/mcp` and disable the headless server if it would be ambiguous. The live server only works while the controlled app is running. Do not use a regular PhotoCraft window as if it were bridged.
- Both modes restrict automation file operations to `~/Pictures/PhotoCraft-AI`. Use relative paths under that directory; work on copies of input documents. Ask before editing or overwriting important work.
- Discover tools in the appropriate `mcp__photocraft` or `mcp__photocraft_live` namespace using Pi's tool search/codemode and inspect their argument schemas before calling them. Typical tools include `doc_open`, `doc_inspect`, `command_list`, `command_run` and `doc_save`. Do not invent command IDs or params; use `command_list` first.
- Inspect the document and layers before editing. Save to a separate `.pcraft` copy and inspect the saved result. UI tools such as `ui_inspect` work only in live mode. On a bridge timeout, inspect state before retrying a mutating operation: the first call may have completed.
