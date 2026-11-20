#!/usr/bin/env python3
"""R1 timings on the same R0 world, never the real desktop; output is synthetic."""
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from test_workspace_cli import Cli,BIN,DATA
from test_workspace_parity import FIXTURE,ORACLE

ROOT=Path(__file__).resolve().parents[1]

def measure(command,env,n=31):
    values=[]
    for _ in range(n):
        start=time.perf_counter()
        # communicate with pipes avoids wait(timeout)'s polling-backoff bias.
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=5)
        values.append((time.perf_counter()-start)*1000)
    return {'samples':n,'median_ms':round(statistics.median(values),3),'p95_ms':round(sorted(values)[int(n*.95)],3)}

def main():
    fixture=Cli('test_snapshot_read_only');fixture.setUp()
    try:
        before=fixture.state.read_bytes()
        result={'version':1,'recorded_at':'2026-11-19','world':'tools/runtime-migration/fixtures.json',
            'method':'warm process wall time, 31 samples; snapshot uses the identical private Python fake hyprctl for both implementations; not live desktop latency',
            'python_process_start':measure([sys.executable,'-c','pass'],fixture.env),
            'rust_process_version':measure([str(BIN),'--version'],fixture.env),
            'python_snapshot_cli_fake_native':measure([sys.executable,str(ORACLE),'snapshot'],fixture.env),
            'rust_snapshot_cli_fake_native':measure([str(BIN),'snapshot'],fixture.env)}
        assert fixture.state.read_bytes()==before
        # R0 create path: same two owners/IDs and occupied clients; fake guarded eval.
        desktop=DATA['desktop'];native=DATA['native']
        world={'active':1,'focused':'0xa','clients':native['clients'],'ws':[1,2],'other_visible':[],'events':[]}
        info=json.loads(subprocess.check_output([str(FIXTURE)],input=json.dumps({'state':desktop,'raw':desktop,'world':world,'steps':[{'op':'create-empty'}]}),text=True))
        assert info['ok'] and info['world']['active']==3
        result['same_r0_create_outcome']={'active_workspace':3,'order':info['state']['order'],'native_dispatches':len(info['codes'])}
        print(json.dumps(result,indent=2))
    finally:fixture.doCleanups()

if __name__=='__main__':main()
