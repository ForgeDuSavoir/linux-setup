#!/usr/bin/env python3
"""Actual targeted visual publish/restore on a private cohort, no real compositor."""
import json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from cohort_fixture import Fixture,installer
policy=sys.argv[1] if len(sys.argv)>1 else 'visuals'
assert policy in ['visuals','inputs']
asset='.config/hypr/'+policy+'.lua'
with tempfile.TemporaryDirectory(prefix=policy+'-cohort-') as d:
 f=Fixture(Path(d));f.start()
 try:
  f.run('--apply','--allow-notification-history-reset');f.reap()
  q=f.root/'.config/quickshell/shell.qml';keys=f.root/'.config/hypr/keybinds.lua';visual=f.root/asset
  visual.write_bytes(b'-- private prior visuals\n')
  before=(q.read_bytes(),keys.read_bytes(),f.state.read_bytes(),f.marker.read_bytes(),f.core('list'),(f.root/'qs.pid').read_text())
  original=installer.files
  def modified():
   assets=original();b,mode=assets[asset];assets[asset]=(b+b'\n-- private visual test\n',mode);return assets
  with patch.dict(os.environ,f.env,clear=True),patch.object(installer,'files',side_effect=modified):installer.apply(reduced=policy)
  assert visual.read_bytes().endswith(b'-- private visual test\n')
  after=(q.read_bytes(),keys.read_bytes(),f.state.read_bytes(),f.marker.read_bytes(),f.core('list'),(f.root/'qs.pid').read_text());assert after==before
  backup=next(p for p in f.backups() if json.loads((p/'manifest.json').read_text()).get('reduced')==policy)
  with patch.dict(os.environ,f.env,clear=True):installer.restore(backup)
  assert not visual.read_bytes().endswith(b'-- private visual test\n')
  assert (q.read_bytes(),keys.read_bytes(),f.state.read_bytes(),f.marker.read_bytes(),f.core('list'),(f.root/'qs.pid').read_text())==before
 finally:f.close()
print('Private '+policy+'-only cohort: targeted apply/restore, unchanged QML/bindings/state/marker/core/shell PID, no live GUI.')
