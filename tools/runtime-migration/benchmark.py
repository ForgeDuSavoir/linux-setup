#!/usr/bin/env python3
"""R0 synthetic timings; optional live probes are strictly read-only, output discarded."""
import argparse
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / 'fixtures.json').read_text())
SOURCE = HERE / 'oracles/configs/hypr/files/Scripts/workspace-columns.py'


def measure(function, samples):
    values = []
    for _ in range(samples):
        start = time.perf_counter()
        function()
        values.append((time.perf_counter() - start) * 1000)
    ordered = sorted(values)
    return {'samples': samples, 'median_ms': round(statistics.median(values), 3),
            'p95_ms': round(ordered[min(len(ordered)-1, int(len(ordered)*0.95))], 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=31)
    parser.add_argument('--live-readonly', action='store_true')
    args = parser.parse_args()
    if not 3 <= args.samples <= 101:
        parser.error('samples must be between 3 and 101')
    results = {'version': 1, 'python': sys.version.split()[0], 'kind': 'R0 baseline, not a Rust comparison'}
    def command(argv):
        # Pipes let communicate() wait on EOF instead of wait(timeout)'s polling
        # backoff (which quantizes short timings). Captured data is not retained.
        subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    results['python_process_start'] = measure(lambda: command([sys.executable, '-c', 'pass']), args.samples)
    if args.live_readonly:
        results['hyprctl_process_and_read_ipc'] = measure(lambda: command(['hyprctl', '-j', 'activeworkspace']), args.samples)
        manager = Path.home() / '.local/bin/session-manager'
        results['core_client_process_and_read_ipc'] = measure(lambda: command([str(manager), '--json', 'session', 'list']), args.samples)
    with tempfile.TemporaryDirectory(prefix='runtime-r0-bench-') as directory:
        root = Path(directory)
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(root)}):
            spec = importlib.util.spec_from_file_location('r0_bench_columns', SOURCE)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.RUNTIME.mkdir()
        world = copy.deepcopy(FIXTURE['native'])
        queries, dispatches = [], []
        def query(name):
            queries.append(name)
            return copy.deepcopy(world[name])
        def ctl(*argv):
            if argv[0] != 'eval':
                raise AssertionError('only a fake allocation eval was expected')
            dispatches.append('guarded allocation')
            world['activeworkspace']['id'] = 3
            world['monitors'][0]['activeWorkspace']['id'] = 3
            world['workspaces'].append({'id': 3})
            return 'ok'
        module.query, module.ctl = query, ctl
        module.STATE.write_text(json.dumps(FIXTURE['desktop']))
        before = module.STATE.read_bytes()
        results['snapshot_in_process_fake_native'] = measure(module.snapshot, args.samples)
        assert module.STATE.read_bytes() == before
        results['snapshot_native_queries_per_call'] = len(queries) // args.samples
        queries.clear()
        def create():
            nonlocal world
            world = copy.deepcopy(FIXTURE['native'])
            state = copy.deepcopy(FIXTURE['desktop'])
            module.create_empty(state)
            assert world['activeworkspace']['id'] == 3
        results['create_empty_in_process_fake_native'] = measure(create, args.samples)
        results['create_empty_native_queries_per_call'] = len(queries) // args.samples
        results['create_empty_native_dispatches_per_call'] = len(dispatches) // args.samples
        # Reproduce the old algorithm without sleeping first: 40 polls x 50 ms
        # even though only one remaining window exists, not the one just closed.
        world = copy.deepcopy(FIXTURE['native']); queries.clear(); waits = []
        original_sleep = module.time.sleep
        try:
            module.time.sleep = waits.append
            module.closed(copy.deepcopy(FIXTURE['desktop']), 1)
        finally:
            module.time.sleep = original_sleep
        results['closed_remaining_window_virtual'] = {'polls': len(queries), 'requested_wait_ms': sum(waits)*1000}
        # One actual private-fixture measurement; never closes a real window.
        results['closed_remaining_window_real_wait'] = measure(lambda: module.closed(copy.deepcopy(FIXTURE['desktop']), 1), 1)
        # A private fd lock demonstrates that handler wait is shared-command latency.
        lock = root / 'private.lock'
        ready = threading.Event()
        def hold():
            with lock.open('w') as stream:
                fcntl.flock(stream, fcntl.LOCK_EX); ready.set(); time.sleep(0.075)
        worker = threading.Thread(target=hold); worker.start(); ready.wait(timeout=2)
        def acquire():
            with lock.open('w') as stream: fcntl.flock(stream, fcntl.LOCK_EX)
        results['private_lock_contended_75ms'] = measure(acquire, 1)
        worker.join()
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
