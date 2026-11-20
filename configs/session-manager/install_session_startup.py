#!/usr/bin/env python3
"""Update startup only within an already native cohort; first activation is coordinated."""
import importlib.util
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('startup_cohort_installer',HERE.parents[1]/'runtime/install_desktop.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if __name__=='__main__':
    args=sys.argv[1:]
    if not any(a in args for a in ['--allow-notification-history-reset','--offline','--restore','--stage']):args=['--startup-only',*args]
    try:module.main(args)
    except (OSError,RuntimeError,ValueError,KeyError,module.subprocess.SubprocessError) as e:raise SystemExit(f'Startup cohort stopped: {e}; inspect backup, no automatic rollback.')
