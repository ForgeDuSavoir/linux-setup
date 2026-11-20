#!/usr/bin/env python3
"""Startup handoff belongs to the same native cohort; no isolated Python replacement."""
import runpy
import sys
from pathlib import Path
tests=Path(__file__).resolve().parents[2]/'runtime/tests'
sys.path.insert(0,str(tests))
runpy.run_path(str(tests/'test_desktop_cohort.py'),run_name='__main__')
