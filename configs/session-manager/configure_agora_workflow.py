#!/usr/bin/env python3
"""Create owner-supplied Agora workflow settings; never overwrite an existing file."""
import json
import os
from pathlib import Path
import sys
import tomllib


def configure(config, supplied=None):
    if config.is_symlink():
        raise ValueError(f'refusing a symlinked configuration: {config}')
    if config.exists():
        with config.open('rb') as file:
            data = tomllib.load(file)
        value = data.get('agora_root')
        if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_dir():
            raise ValueError(f'correct agora_root in {config}: an existing absolute directory is required')
        return False
    if supplied is None or not supplied:
        raise ValueError('set AGORA_ROOT to your existing Agora directory for first-time configuration')
    path = Path(supplied)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('AGORA_ROOT must be an existing absolute directory')
    config.parent.mkdir(parents=True, exist_ok=True)
    # Literal TOML string avoids shell expansion and JSON-only Unicode escapes.
    value = str(path)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('AGORA_ROOT must not contain control characters')
    quoted = json.dumps(value, ensure_ascii=False)
    with config.open('x', encoding='utf-8') as file:
        os.fchmod(file.fileno(), 0o600)
        file.write(f'agora_root = {quoted}\n')
    return True


def main():
    root = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    if not root.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    config = root / 'agora-workflow/config.toml'
    created = configure(config, os.environ.get('AGORA_ROOT'))
    print(f'{"Created" if created else "Preserved"} {config}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'Agora workflow configuration: {error}', file=sys.stderr)
        sys.exit(1)
