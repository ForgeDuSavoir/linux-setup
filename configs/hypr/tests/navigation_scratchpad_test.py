#!/usr/bin/env python3
"""Navigation consumes a visible scratchpad without changing workspaces/state."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'files/Scripts/workspace-columns.py'
spec = importlib.util.spec_from_file_location('columns', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as directory:
    module.RUNTIME = Path(directory)
    module.STATE = module.RUNTIME / 'state.json'
    for name in ('global', 'session-ai', 'sm-12345678-1234-1234-1234-123456789abc-notes'):
        for args in (['cycle'], ['create-empty'], ['focus-workspace', '2']):
            monitors = [{'focused': True, 'specialWorkspace': {'name': 'special:' + name}}]
            calls = []
            with patch.object(module, 'query', return_value=monitors), \
                 patch.object(module, 'dispatch', side_effect=calls.append), \
                 patch.object(module, 'load', side_effect=AssertionError('must not read state')), \
                 patch.object(sys, 'argv', [str(source), *args]):
                module.main()
            assert calls == [f'hl.dsp.workspace.toggle_special("{name}")']
            assert not module.STATE.exists()
    # A scratchpad on a different monitor must not intercept this monitor's key.
    monitors = [{'focused': False, 'specialWorkspace': {'name': 'special:global'}},
                {'focused': True, 'specialWorkspace': {'name': ''}}]
    with patch.object(module, 'query', return_value=monitors), \
         patch.object(module, 'load', return_value={}), \
         patch.object(module, 'cycle') as cycle, \
         patch.object(module, 'dispatch') as dispatch, \
         patch.object(sys, 'argv', [str(source), 'cycle']):
        module.main()
        cycle.assert_called_once_with({})
        dispatch.assert_not_called()
    # No scratchpad: the requested empty-workspace insertion still runs normally.
    with patch.object(module, 'query', return_value=[{'specialWorkspace': {'name': ''}}]), \
         patch.object(module, 'load', return_value={}), \
         patch.object(module, 'create_empty') as toggle, \
         patch.object(sys, 'argv', [str(source), 'create-empty']):
        module.main()
        toggle.assert_called_once_with({})

print('Navigation hides scratchpads only; otherwise navigation is unchanged: passed.')
