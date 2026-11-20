#!/usr/bin/env python3
"""R0 frozen-oracle smoke contracts; no unmocked external command is allowed."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ORACLES = HERE / 'oracles'
FIXTURE = json.loads((HERE / 'fixtures.json').read_text())
CONTROLLER = 'configs/hypr/files/Scripts/workspace-columns.py'


def load(relative):
    path = ORACLES / relative
    spec = importlib.util.spec_from_file_location('r0_' + path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Baseline(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='runtime-r0-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'HOME': str(self.root), 'XDG_RUNTIME_DIR': str(self.root / 'runtime'),
                               'XDG_CONFIG_HOME': str(self.root / 'config'),
                               'SESSION_COLUMNS_SCRIPT': str(ORACLES / CONTROLLER)}).start()
        patch('subprocess.run', side_effect=AssertionError('unmocked external process forbidden')).start()
        patch('subprocess.Popen', side_effect=AssertionError('unmocked child spawn forbidden')).start()
        patch('os.execvp', side_effect=AssertionError('unmocked process replacement forbidden')).start()

    def desktop(self):
        module = load('configs/session-manager/session-desktop.py')
        module.columns.RUNTIME.mkdir(parents=True)
        module.columns.STATE.write_text(json.dumps(FIXTURE['desktop']))
        module.columns.query = lambda key: copy.deepcopy(FIXTURE['native'][key])
        module.request = lambda *args: copy.deepcopy(FIXTURE['sessions'])
        return module

    def test_frozen_hashes(self):
        manifest = json.loads((ORACLES / 'manifest.json').read_text())
        self.assertEqual(len(manifest['files']), 8)
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((ORACLES / item['source']).read_bytes()).hexdigest(), item['sha256'])

    def test_controller_snapshot_is_semantically_stable_and_does_not_save(self):
        module = self.desktop().columns
        before = module.STATE.read_bytes()
        self.assertEqual(module.snapshot(), FIXTURE['snapshot'])
        self.assertEqual(module.STATE.read_bytes(), before)

    def test_desktop_status_confirmed_and_mismatch(self):
        module = self.desktop()
        before = module.columns.STATE.read_bytes()
        self.assertTrue(module.status()['context_confirmed'])
        module.request = lambda *args: {**copy.deepcopy(FIXTURE['sessions']), 'active_session_id': None}
        self.assertFalse(module.status()['context_confirmed'])
        self.assertEqual(module.columns.STATE.read_bytes(), before)

    def test_startup_marker_read_only_and_identity_validation(self):
        module = load('configs/session-manager/session-startup.py')
        module.columns.RUNTIME.mkdir(parents=True)
        module.marker_path().write_text(json.dumps(FIXTURE['marker']))
        self.assertEqual(module.read_marker(), FIXTURE['marker'])
        self.assertEqual(module.session_ids(FIXTURE['sessions']), list(FIXTURE['desktop']['owners'].values()))
        with self.assertRaises(RuntimeError):
            module.session_ids({'sessions': [{'id': 'A'}, {'id': 'A'}]})
        # Never call initialize()/main(): those intentionally stop/start sessions.

    def test_notify_inherited_context_and_literal_send(self):
        module = load('configs/session-manager/agora-notify.py')
        context = 'session:' + FIXTURE['sessions']['active_session_id']
        with patch.dict(os.environ, {'AGORA_NOTIFICATION_CONTEXT': context}):
            self.assertEqual(module.capture(), context)
        calls = []
        def run(command, **options):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(module.subprocess, 'run', side_effect=run):
            module.main(['send', '--context', context, 'synthetic $(not-a-command)', 'body'])
        self.assertEqual(calls[0][-3:], ['--', 'synthetic $(not-a-command)', 'body'])
        self.assertIn('string:x-agora-context:' + context, calls[0])

    def test_pi_neutral_directory_and_tagged_terminal_arguments(self):
        module = load('configs/session-manager/session-pi.py')
        agora = self.root / 'synthetic agora'; agora.mkdir()
        config = module.workflow_config(); config.parent.mkdir(parents=True)
        config.write_text('agora_root = ' + json.dumps(str(agora)))
        module.query = lambda *args: copy.deepcopy(FIXTURE['sessions'])
        command, context = module.launch_plan()
        self.assertEqual(command[1:], [str(agora), 'pi'])
        self.assertEqual(context, 'session:' + FIXTURE['sessions']['active_session_id'])
        calls = []
        def run(command, **options):
            calls.append((command, options))
            return subprocess.CompletedProcess(command, 0, context + '\n', '')
        with patch.object(module.subprocess, 'run', side_effect=run), patch.object(sys, 'argv', ['session-pi']):
            module.main()
        self.assertEqual(calls[-1][0][2:], ['env', 'AGORA_NOTIFICATION_CONTEXT=' + context, 'pi'])

    def test_photocraft_mask_metadata_without_images_or_gui(self):
        module = load('scripts/photocraft-thumbnail/photocraft-thumbnail.py')
        with ZipFile(module.MASK_TEMPLATE) as template:
            reference = json.loads(template.read('mask.json'))
        document = {'format_version': reference['format_version'], 'document': {
            'size': {'width': 1920, 'height': 1080}, 'layers': [{'name': 'bottom'}, {'name': 'top'}]}}
        source, target = self.root / 'source.pcraft', self.root / 'masked.pcraft'
        with ZipFile(source, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(document))
        module.apply_reference_mask(source, target, 'top', 'bottom')
        with ZipFile(target) as archive:
            result = json.loads(archive.read('manifest.json'))
            self.assertEqual(result['document']['layers'][1]['mask'], reference['mask'])
            self.assertNotIn('mask', result['document']['layers'][0])
        # No ffmpeg/photocraft-cli or real document was used.

    def test_filmcraft_signature_and_validation_before_external_processes(self):
        module = load('scripts/filmcraft-patch-desktop-audio/filmcraft-patch-desktop-audio.py')
        self.assertEqual(list(module.signature(FIXTURE['clip'])), FIXTURE['clip_signature'])
        with patch.object(sys, 'argv', ['filmcraft-patch-desktop-audio', str(self.root / 'absent.mkv'), str(self.root / 'absent.fcproj')]):
            with self.assertRaisesRegex(RuntimeError, 'introuvable'):
                module.main()
        # Full rational/publish/failure scenarios belong to R7, not claimed here.


if __name__ == '__main__':
    unittest.main()
