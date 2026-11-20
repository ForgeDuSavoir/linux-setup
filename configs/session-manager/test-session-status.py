#!/usr/bin/env python3
"""Read-only desktop confirmation with owned state, mock core and compositor."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

source = Path(__file__).with_name('session-desktop.py')
os.environ['SESSION_COLUMNS_SCRIPT'] = str(source.parents[1] / 'hypr/files/Scripts/workspace-columns.py')
spec = importlib.util.spec_from_file_location('desktop_status', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
UUID = '12345678-1234-1234-1234-123456789abc'
with tempfile.TemporaryDirectory() as directory:
    module.columns.RUNTIME = Path(directory)
    module.columns.STATE = Path(directory) / 'columns.json'
    reply = {'sessions': [{'id': UUID}], 'active_session_id': UUID, 'revision': 3}
    monitor = {'focused': True, 'activeWorkspace': {'id': 3}, 'specialWorkspace': {'name': ''}}
    def request(*args):
        assert args == ('list',)
        return dict(reply)
    with patch.object(module, 'request', side_effect=request), \
         patch.object(module.columns, 'query', return_value=[monitor]), \
         patch.object(module.columns, 'dispatch', side_effect=AssertionError('no dispatch allowed')), \
         patch.object(module.columns, 'load', side_effect=AssertionError('no automatic migration')):
        assert not module.status()['context_confirmed']
        assert not module.columns.STATE.exists()
        state = {'version': 2, 'owners': {'1': 'neutral', '2': UUID}}
        module.columns.STATE.write_text(json.dumps(state))
        before = module.columns.STATE.read_bytes()
        assert module.status()['context_confirmed']
        assert module.status()['displayed_context'] == UUID
        monitor['activeWorkspace']['id'] = 1
        assert not module.status()['context_confirmed']
        reply['active_session_id'] = None
        assert module.status()['context_confirmed']
        monitor['specialWorkspace']['name'] = f'special:sm-{UUID}-ai'
        assert not module.status()['context_confirmed']
        assert module.columns.STATE.read_bytes() == before
        state = {'version': 3, 'order': [1, 2], 'owners': {'1': 'neutral', '2': UUID},
                 'preferred': {}, 'origins': {}, 'next_id': 3}
        module.columns.STATE.write_text(json.dumps(state))
        before = module.columns.STATE.read_bytes()
        monitor['activeWorkspace']['id'] = 2
        monitor['specialWorkspace']['name'] = ''
        reply['active_session_id'] = UUID
        assert module.status()['context_confirmed']
        assert module.status()['displayed_context'] == UUID
        assert module.columns.STATE.read_bytes() == before
print('Desktop status confirms logical/spatial agreement without migration or dispatch: passed.')
