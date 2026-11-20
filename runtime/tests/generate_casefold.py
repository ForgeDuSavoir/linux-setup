#!/usr/bin/env python3
"""Reproduce embedded Unicode 16 full default folding from the R0 Python baseline.
Development-only data generator; runtime never invokes Python or this script.
Redirect stdout to photocraft-thumbnail/src/casefold.json when regenerating.
"""
import json
import unicodedata
assert unicodedata.unidata_version=='16.0.0','keep Unicode baseline explicit'
print(json.dumps({chr(i):chr(i).casefold() for i in range(0x110000) if chr(i).casefold()!=chr(i)},ensure_ascii=False,separators=(',',':')))
