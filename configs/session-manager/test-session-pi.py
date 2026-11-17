#!/usr/bin/env python3
"""Session Pi routing with fake API; never start a terminal or Pi."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('session_pi', Path(__file__).with_name('session-pi.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as directory:
    project = Path(directory) / "Project with spaces and 'quotes'"
    project.mkdir()
    agora = Path(directory) / 'User-selected Agora'
    agora.mkdir()
    config = Path(directory) / 'config/agora-workflow/config.toml'
    config.parent.mkdir(parents=True)
    config.write_text('agora_root = ' + json.dumps(str(agora)) + '\n')
    session = {'id': 'session-uuid', 'source': {'kind': 'project', 'project_name': project.name}}
    state = {'active_session_id': session['id'], 'sessions': [session]}
    projects = {'projects': [{'name': project.name, 'path': str(project)}]}
    def query(*args):
        return state if args == ('session', 'list') else projects
    with patch.object(module, 'query', side_effect=query), patch.dict(os.environ, {'XDG_CONFIG_HOME': str(config.parent.parent)}):
        command = module.launch_command()
        assert command == [str(module.TERMINAL), str(project), 'pi']
        assert not (project / 'AGENTS.md').exists()
        assert 'yazi' not in str(command)
        state['active_session_id'] = None
        assert module.launch_command() == [str(module.TERMINAL), str(agora), 'pi']
        session['source'] = {'kind': 'neutral'}
        state['active_session_id'] = session['id']
        assert module.launch_command() == [str(module.TERMINAL), str(agora), 'pi']
        session['source'] = {'kind': 'project', 'project_name': project.name}
        state['active_session_id'] = None
        config.unlink()
        try:
            module.launch_command()
            raise AssertionError('missing configuration must not select an invented root')
        except ValueError as error:
            assert 'configure agora_root' in str(error)
        for content in ['invalid = [', 'agora_root = "relative"', 'agora_root = 12', 'agora_root = "/missing-agora-test-directory"']:
            config.write_text(content)
            try:
                module.launch_command()
                raise AssertionError('invalid neutral configuration must fail')
            except ValueError:
                pass
        config.unlink()
        state['active_session_id'] = session['id']
        projects['projects'] = []
        try:
            module.launch_command()
            raise AssertionError('must refuse missing project')
        except ValueError:
            pass

with patch.object(module, 'query', side_effect=RuntimeError('daemon unavailable')):
    try:
        module.launch_command()
        raise AssertionError('daemon failure must not silently select Agora')
    except RuntimeError:
        pass

print('Pi routing: active project, neutral Agora, no Yazi and no fallback on API failure: passed.')
