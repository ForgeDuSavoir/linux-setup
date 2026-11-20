#!/usr/bin/env python3
"""Real private core catalog: local OBS replaces, not adds to, the generic entry."""
import importlib.util,json,os,sys,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'runtime/tests'))
from cohort_fixture import Fixture,CORE
def applications(env):return json.loads(subprocess.check_output([str(CORE),'--json','application','list'],env=env,text=True))['applications']
spec=importlib.util.spec_from_file_location('obs_profiles',HERE/'install_project_launchers.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='obs-catalog-') as d:
 f=Fixture(Path(d))
 try:
    home=f.root;source=home/'projects';data=Path(f.env['XDG_DATA_HOME']);apps=data/'applications';apps.mkdir(parents=True,exist_ok=True)
    generic=b'[Desktop Entry]\nName=OBS Studio\nType=Application\nExec=obs\nIcon=com.obsproject.Studio\n'
    (apps/'com.obsproject.Studio.desktop').write_bytes(generic)
    for name,command,_,_ in m.PROFILES.values():
        (source/name).mkdir();b=home/'.local/bin'/command;b.write_text('#!/bin/sh\nexit 0\n');b.chmod(0o755)
    base=home/'backups';base.mkdir()
    with patch.dict(os.environ,f.env,clear=True):m.apply(m.plan(home,source,list(m.PROFILES),True),base)
    f.start()
    # Neutral keeps generic OBS; no special FDS/Gaming entries were installed globally.
    rows=[a for a in applications(f.env) if a['id']=='com.obsproject.Studio.desktop']
    assert len(rows)==1 and rows[0]['name']=='OBS Studio',rows
    for name,command,_,_ in m.PROFILES.values():
        f.core('start','--project',name)
        rows=[a for a in applications(f.env) if a['id']=='com.obsproject.Studio.desktop']
        assert len(rows)==1,rows
        assert rows[0]['origin']=='project' and rows[0]['exec']=='/usr/bin/env -- '+m.quote(home/'.local/bin'/command),rows
        assert not list((source/name).rglob('app-usage.json'))
    assert (apps/'com.obsproject.Studio.desktop').read_bytes()==generic
 finally:f.close()
print('OBS private core: one same-ID project override in FDS/QMK, unchanged generic OBS in Neutral; no application launch or usage mutation.')
