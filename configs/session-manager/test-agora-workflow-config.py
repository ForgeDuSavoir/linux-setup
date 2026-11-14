#!/usr/bin/env python3
"""User-chosen Agora configuration tests in temporary directories only."""
import importlib.util
from pathlib import Path
import tempfile
import tomllib

spec = importlib.util.spec_from_file_location('configure_workflow', Path(__file__).with_name('configure_agora_workflow.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config = root / 'config/agora-workflow/config.toml'
    agora = root / 'My Agora "quoted" é'
    agora.mkdir()
    for value in (None, '', 'relative', str(root / 'missing')):
        try:
            module.configure(config, value)
            raise AssertionError('must reject missing or invalid initial path')
        except ValueError:
            pass
        assert not config.exists()
    assert module.configure(config, str(agora))
    data = config.read_bytes()
    assert tomllib.loads(data.decode())['agora_root'] == str(agora)
    assert config.stat().st_mode & 0o777 == 0o600
    assert not module.configure(config, '/ignored-new-location')
    assert config.read_bytes() == data
    config.write_text('agora_root = "relative"')
    try:
        module.configure(config, str(agora))
        raise AssertionError('invalid existing settings must be preserved, not replaced')
    except ValueError:
        pass
    assert config.read_text() == 'agora_root = "relative"'
    config.unlink()
    config.symlink_to(root / 'missing')
    try:
        module.configure(config, str(agora))
        raise AssertionError('must reject symlink configuration')
    except ValueError:
        pass

print('Agora settings: explicit creation, TOML quoting, preservation and validation passed.')
