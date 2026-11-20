#!/usr/bin/env python3
"""Compatibility entry point for the R8 native cohort coordinator; plan by default."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_cohort_installer',HERE.parents[1]/'runtime/install_desktop.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
# Historical test/admin helpers remain pure installer utilities, never Python runtime imports.
shell_pid=module.shell_pid
desktop_snapshot=module.desktop_snapshot
write_json=module.write_json
run=module.run
if __name__=='__main__':
    try:module.main()
    except (OSError,RuntimeError,ValueError,KeyError,module.subprocess.SubprocessError) as e:raise SystemExit(f'Navigation cohort stopped: {e}; inspect backup, no automatic rollback.')
