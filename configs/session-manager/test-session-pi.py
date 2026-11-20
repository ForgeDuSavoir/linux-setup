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

# Launch metadata is literal argv as well as environment (terminal servers may
# retain their own environment). No actual terminal/helper is executed here.
A='session:11111111-1111-1111-1111-111111111111'
B='session:22222222-2222-2222-2222-222222222222'
import subprocess
for output,expected in [(A,A),(B,'global'),('invalid','global'),('neutral','global')]:
    with patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],0,output,'')):
        assert module.capture_context(A,{})==expected
for error in [subprocess.TimeoutExpired('fake',2),subprocess.CalledProcessError(1,'fake'),FileNotFoundError()]:
    with patch.object(module.subprocess,'run',side_effect=error):
        assert module.capture_context(A,{})=='global'
with patch.object(module,'launch_plan',return_value=([str(module.TERMINAL),'/fixture','pi'],A)),patch.object(module.sys,'argv',['session-pi']),patch.dict(os.environ,{'AGORA_NOTIFICATION_CONTEXT':B}),patch.object(module.subprocess,'run') as run:
    def capture(expected,env):
        assert expected==A and 'AGORA_NOTIFICATION_CONTEXT' not in env
        return A
    with patch.object(module,'capture_context',side_effect=capture): module.main()
    command=run.call_args.args[0]
    assert command==[str(module.TERMINAL),'/fixture','env','AGORA_NOTIFICATION_CONTEXT='+A,'pi']
    assert run.call_args.kwargs['env']['AGORA_NOTIFICATION_CONTEXT']==A
print('Historical Pi launch context: expected UUID, literal env argv, stale-parent removal and safe global fallback passed.')

# Exercise the replacement, not just the historical import oracle above.
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2]/'runtime/tests/test_pi_parity.py'),run_name='__main__')
