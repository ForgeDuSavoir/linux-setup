#!/usr/bin/env python3
"""Project Firefox launchers and private profiles, without launching a browser."""
import json
import os
from pathlib import Path
import shutil
import signal
import time
import re
import subprocess
import tempfile
import uuid

PROJECTS = Path.home() / 'Obsidian/Agora/2 Projects'
WRAPPER = Path(__file__).with_name('agora-project-firefox.sh')
entries = {}
for project in PROJECTS.iterdir():
    if not project.is_dir() or project.is_symlink():
        continue
    entry = project / '.session-manager/apps/firefox.desktop'
    assert entry.is_file() and not entry.is_symlink(), project
    subprocess.run(['desktop-file-validate', str(entry)], check=True)
    data = entry.read_text()
    assert 'Name=Firefox\nGenericName=Web Browser\n' in data
    match = re.search(r'^Exec=agora-project-firefox ([0-9a-f-]+) %u$', data, re.M)
    assert match, entry
    identity = str(uuid.UUID(match.group(1)))
    assert identity == match.group(1) and identity not in entries.values()
    assert 'TryExec=agora-project-firefox\n' in data
    entries[project.name] = identity
assert len(entries) >= 10, entries

with tempfile.TemporaryDirectory(prefix='project-firefox-') as tmp:
    root = Path(tmp)
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    fake = bin_dir / 'firefox'
    fake.write_text('#!/usr/bin/python3\nimport json,os,sys\n'
                    'with open(os.environ["TEST_FIREFOX_LOG"],"w") as f: json.dump(sys.argv[1:],f)\n')
    fake.chmod(0o700)
    log = root / 'invocation.json'
    data = root / 'private-data'
    env = {**os.environ, 'HOME': str(root), 'XDG_DATA_HOME': str(data),
           'PATH': f'{bin_dir}:/usr/bin:/bin', 'TEST_FIREFOX_LOG': str(log)}
    one = entries['Artcraft']
    url = 'https://example.org/?q=a b&other=\\$(touch /tmp/never-run)'
    subprocess.run(['/bin/bash', str(WRAPPER), one, url], env=env, check=True)
    profile = data / 'agora-project-firefox' / one / 'firefox-profile'
    assert profile.is_dir() and profile.stat().st_mode & 0o777 == 0o700
    assert json.loads(log.read_text()) == [
        '--no-remote', '--profile', str(profile), '--new-window', url]
    two = entries['session-manager']
    subprocess.run(['/bin/bash', str(WRAPPER), two], env=env, check=True)
    assert (profile.parent.parent / two / 'firefox-profile').is_dir()
    assert json.loads(log.read_text()) == [
        '--no-remote', '--profile', str(profile.parent.parent / two / 'firefox-profile'), '--new-window']
    log.unlink()
    invalid = subprocess.run(['/bin/bash', str(WRAPPER), '../unsafe'], env=env, capture_output=True)
    assert invalid.returncode != 0 and not log.exists()
    (data / 'agora-project-firefox' / entries['linux-setup']).symlink_to(root)
    invalid = subprocess.run(['/bin/bash', str(WRAPPER), entries['linux-setup']], env=env, capture_output=True)
    assert invalid.returncode != 0 and not log.exists()

# Exercise the actual XDG resolver using a separate owned daemon and fixture data.
with tempfile.TemporaryDirectory(prefix='project-firefox-ipc-') as tmp:
    root = Path(tmp)
    source = root / 'projects'
    config = root / 'config/session-manager'
    runtime = root / 'runtime'
    data = root / 'data/applications'
    bin_dir = root / 'bin'
    for directory in (source, config, runtime, data, bin_dir, root / 'state', root / 'empty-data'):
        directory.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    (config / 'config-v2.toml').write_text(
        f'schema_version = 2\nproject_source = {json.dumps(str(source))}\n')
    (data / 'firefox.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Firefox\nExec=firefox %u\n')
    executable = bin_dir / 'agora-project-firefox'
    executable.write_bytes(WRAPPER.read_bytes())
    executable.chmod(0o700)
    for name in entries:
        folder = source / name / '.session-manager/apps'
        folder.mkdir(parents=True)
        for file in (PROJECTS / name / '.session-manager/apps').iterdir():
            shutil.copyfile(file, folder / file.name)
    env = {'HOME': str(root), 'PATH': f'{bin_dir}:/usr/bin:/bin',
           'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_STATE_HOME': str(root / 'state'),
           'XDG_RUNTIME_DIR': str(runtime), 'XDG_DATA_HOME': str(root / 'data'),
           'XDG_DATA_DIRS': str(root / 'empty-data'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
           'LANG': 'C.UTF-8'}
    manager = Path.home() / '.local/bin/session-manager'
    daemon = subprocess.Popen([str(manager), 'daemon'], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        socket = runtime / 'session-manager/ipc-v2.sock'
        for _ in range(100):
            if socket.exists():
                break
            if daemon.poll() is not None:
                raise RuntimeError('fixture daemon exited: ' + daemon.stderr.read())
            time.sleep(0.05)
        else:
            raise RuntimeError('fixture daemon did not start')
        def request(*args):
            result = subprocess.run([str(manager), '--json', *args], env=env,
                                    check=True, capture_output=True, text=True, timeout=35)
            return json.loads(result.stdout)
        neutral = next(app for app in request('application', 'list')['applications'] if app['id'] == 'firefox.desktop')
        assert neutral['origin'] == 'installed'
        for name, profile_id in entries.items():
            request('session', 'start', name)
            browser = next(app for app in request('application', 'list')['applications']
                           if app['id'] == 'firefox.desktop')
            assert browser['origin'] == 'project' and browser['name'] == 'Firefox'
            assert browser['exec'] == f'agora-project-firefox {profile_id} %u'
    finally:
        if daemon.poll() is None:
            daemon.send_signal(signal.SIGTERM)
            daemon.wait(timeout=10)

print(f'{len(entries)} unique project Firefox desktop entries; private profiles and XDG overrides verified.')
