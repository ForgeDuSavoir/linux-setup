#!/usr/bin/env python3
"""Current installer acceptance targets the native cohort, not a retired Python copy."""
import runpy
import sys
from pathlib import Path
tests=Path(__file__).resolve().parents[3]/'runtime/tests'
sys.path.insert(0,str(tests))
runpy.run_path(str(tests/'test_desktop_cohort.py'),run_name='__main__')
