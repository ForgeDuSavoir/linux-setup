#!/usr/bin/env python3
"""Static caller/import audit only; never import runtime modules or read HOME data."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TERMS = ('workspace-columns.py', 'session-desktop', 'session-startup', 'agora-notify',
         'session-pi', 'photocraft-thumbnail', 'filmcraft-patch-desktop-audio',
         'SESSION_COLUMNS_SCRIPT')
SUFFIXES = {'.py', '.sh', '.lua', '.qml', '.ts', '.desktop'}


def main():
    hits = []
    for directory in ('configs', 'scripts', 'packages'):
        for path in sorted((REPO / directory).rglob('*')):
            relative = path.relative_to(REPO)
            if (not path.is_file() or path.is_symlink() or path.suffix not in SUFFIXES
                    or any(part in ('target', 'node_modules', '.git', '.session-manager', '__pycache__')
                           for part in relative.parts)):
                continue
            found = [{'line': number, 'text': line.strip()}
                     for number, line in enumerate(path.read_text().splitlines(), 1)
                     if any(term in line for term in TERMS)]
            if not found:
                continue
            kind = ('test' if 'tests' in relative.parts or path.name.startswith(('test', 'scratchpad_session_test'))
                    else 'installer' if path.name.startswith(('install', 'configure')) else 'runtime')
            hits.append({'path': relative.as_posix(), 'kind': kind, 'references': found})
    print(json.dumps({'version': 1, 'method': 'literal references; dynamic imports require the reviewed README map',
                      'files': hits}, indent=2))


if __name__ == '__main__':
    main()
