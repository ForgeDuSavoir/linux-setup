#!/usr/bin/env python3
"""Add missing repository Thunar actions without replacing the user's actions."""

import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from xml.etree import ElementTree as ET

# These two workflow actions must follow the configured default terminal even
# when older user configs hard-code Kitty or Alacritty. Other actions are left alone.
SYNC_COMMAND_IDS = {"1779962885996697-1", "1793116800000000-1"}


def action_ids(xml):
    root = ET.fromstring(xml)
    if root.tag != "actions":
        raise ValueError("Expected an <actions> root in Thunar uca.xml")
    ids = [a.findtext("unique-id") for a in root.findall("action")]
    if any(not uid for uid in ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate unique-id in Thunar uca.xml")
    return ids


def merge(source, target):
    source_xml = source.read_text(encoding="utf-8")
    source_ids = action_ids(source_xml)
    snippets = re.findall(r"<action>[\s\S]*?</action>", source_xml)
    if len(snippets) != len(source_ids):
        raise ValueError("Could not read all template actions")
    by_id = {uid: snippet for uid, snippet in zip(source_ids, snippets)}
    if target.is_symlink():
        raise ValueError(f"Refusing symbolic link: {target}")
    if target.exists():
        original = target.read_text(encoding="utf-8")
        installed_ids = action_ids(original)
        installed_snippets = re.findall(r"<action>[\s\S]*?</action>", original)
        if len(installed_ids) != len(installed_snippets):
            raise ValueError("Could not read all installed actions")
        updated = original
        for uid, snippet in zip(installed_ids, installed_snippets):
            if uid not in SYNC_COMMAND_IDS or uid not in by_id:
                continue
            old_command = re.search(r"<command>[\s\S]*?</command>", snippet)
            new_command = re.search(r"<command>[\s\S]*?</command>", by_id[uid])
            if not old_command or not new_command:
                raise ValueError(f"Missing command for Thunar action {uid}")
            replacement = snippet.replace(old_command.group(), new_command.group(), 1)
            updated = updated.replace(snippet, replacement, 1)
        missing = [by_id[uid] for uid in source_ids if uid not in installed_ids]
        if missing:
            closing = updated.rfind("</actions>")
            if closing < 0:
                raise ValueError("Missing </actions> in Thunar uca.xml")
            updated = updated[:closing].rstrip() + "\n" + "\n".join(missing) + "\n" + updated[closing:]
        if updated == original:
            print("✓ Thunar custom actions already installed; existing edits preserved.")
            return
        mode = stat.S_IMODE(target.stat().st_mode)
    else:
        updated = source_xml
        mode = 0o600
    action_ids(updated)  # Validate before replacing anything.
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".uca-", suffix=".xml", dir=target.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(updated)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"✓ Thunar custom actions updated: {target}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: merge_uca.py <template-uca.xml> <user-uca.xml>")
    try:
        merge(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, ET.ParseError) as exc:
        raise SystemExit(f"✗ Could not update Thunar custom actions: {exc}") from None
