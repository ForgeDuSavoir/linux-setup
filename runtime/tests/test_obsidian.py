#!/usr/bin/env python3
"""Actual ELF resolution on synthetic registry/projects. Never launch real Obsidian."""
import copy,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BIN=ROOT/'target/release/session-obsidian';DRIVER=ROOT/'target/release/examples/obsidian-fixture'
A='0123456789abcdef';P='fedcba9876543210';S='11111111-1111-1111-1111-111111111111'
STATE={'active_session_id':S,'displayed_context':S,'context_confirmed':True,'sessions':[{'id':S,'source':{'kind':'project','project_name':'P'}}]}
HELPER="""#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
h=Path(os.environ['HOME']);w=json.loads((h/'world').read_text());tool=Path(sys.argv[0]).name
with (h/'calls').open('a') as f:f.write(tool+'\\n')
if tool=='session-desktop':
 assert sys.argv[1:]==['status']
 if w.get('timeout'):time.sleep(3)
 p=h/'count';n=int(p.read_text()) if p.exists() else 0;p.write_text(str(n+1))
 states=w['states'];print('bad' if w.get('bad_status') else json.dumps(states[min(n,len(states)-1)]))
else:
 assert sys.argv[1:]==['--json','project','list']
 if w.get('bad_core'):sys.exit(4)
 print(json.dumps(w['catalogue']))
"""
cases=[
 ('project',{},P),('no marker',{'no_project_marker':1},A),('unregistered project',{'unregister_project':1},A),
 ('ancestor only',{'unregister_project':1,'ancestor':1},A),('duplicate project',{'duplicate_project':1},A),
 ('wrong project ID',{'bad_project_id':1},A),('missing project',{'missing_project':1},A),
 ('unconfirmed',{'states':[dict(STATE,context_confirmed=False)]},A),
 ('neutral',{'states':[dict(STATE,sessions=[{'id':S,'source':{'kind':'neutral'}}])]},A),
 ('no session',{'states':[{'active_session_id':None,'displayed_context':'neutral','context_confirmed':True,'sessions':[]}]},A),
 ('changed',{'states':[STATE,dict(STATE,context_confirmed=False)]},A),
 ('bad status',{'bad_status':1},A),('bad catalogue',{'bad_core':1},A),('timeout',{'timeout':1},A),
 ('missing helper',{'missing_helper':1},A),('no Agora config needed for project',{'no_config':1},P),
 ('unregistered Agora',{'unregister_project':1,'unregister_agora':1},None),
 ('ambiguous Agora',{'unregister_project':1,'duplicate_agora':1},None),
 ('missing Agora marker',{'unregister_project':1,'no_agora_marker':1},None),
 ('bad registry',{'bad_registry':1},None),('missing registry',{'missing_registry':1},None),
 ('symlink registry',{'symlink_registry':1},None),('oversized registry',{'oversized_registry':1},None),
 ('symlink project marker',{'symlink_marker':1},A),('relative config',{'relative_config':1},None),
]
with tempfile.TemporaryDirectory(prefix='obsidian-route-') as d:
 for i,(name,w,expected) in enumerate(cases):
    h=Path(d)/str(i);h.mkdir();c=h/'config';(c/'obsidian').mkdir(parents=True);(c/'agora-workflow').mkdir()
    agora=h/"Agora 'quotes' % é";agora.mkdir();project=agora/"Projects/P $()";project.mkdir(parents=True)
    if not w.get('no_project_marker') and not w.get('symlink_marker'):(project/'.obsidian').mkdir()
    if w.get('symlink_marker'):(project/'.obsidian').symlink_to(c,target_is_directory=True)
    if not w.get('no_agora_marker'):(agora/'.obsidian').mkdir()
    if not w.get('no_config'):(c/'agora-workflow/config.toml').write_text('agora_root = '+json.dumps(str(agora)))
    rows={}
    if not w.get('unregister_agora'):rows[A]={'path':str(agora)}
    if not w.get('unregister_project'):rows['invalid' if w.get('bad_project_id') else P]={'path':str(project)}
    if w.get('duplicate_project'):rows['aaaaaaaaaaaaaaaa']={'path':str(project)}
    if w.get('duplicate_agora'):rows['bbbbbbbbbbbbbbbb']={'path':str(agora)}
    if w.get('ancestor'):rows['cccccccccccccccc']={'path':str(agora/'Projects')}
    r=c/'obsidian/obsidian.json'
    if not w.get('missing_registry'):
        r.write_text('invalid' if w.get('bad_registry') else json.dumps({'vaults':rows,'private-preference':'untouched'}))
        if w.get('symlink_registry'):r.rename(c/'registry');r.symlink_to(c/'registry')
        if w.get('oversized_registry'):r.write_bytes(b'x'*(4*1024*1024+1))
    before=r.read_bytes() if r.exists() else None
    if w.get('missing_project'):project.rename(agora/'Projects/Unavailable')
    world={'states':copy.deepcopy(w.get('states',[STATE,STATE])),'catalogue':{'projects':[{'name':'P','path':str(project)}]},**w}
    (h/'world').write_text(json.dumps(world));b=h/'.local/bin';b.mkdir(parents=True)
    for tool in ['session-desktop','session-manager']:
        p=b/tool;p.write_text(HELPER);p.chmod(0o700)
    if w.get('missing_helper'):(b/'session-desktop').unlink()
    env={**os.environ,'HOME':str(h),'XDG_CONFIG_HOME':'relative' if w.get('relative_config') else str(c),'AGORA_NOTIFICATION_CONTEXT':'global'}
    result=subprocess.run([str(BIN),'--print-uri'],env=env,capture_output=True,text=True,timeout=8)
    if expected:assert result.returncode==0 and result.stdout.strip()=='obsidian://open?vault='+expected,(name,result.stderr,result.stdout)
    else:assert result.returncode!=0 and not result.stdout,(name,result.stdout)
    assert (r.read_bytes() if r.exists() else None)==before
    assert not list(h.rglob('app-usage.json'))
 args=['obsidian://open?vault=Other&file=a%20b',"/a 'quotes' % é ; $().md"]
 r=subprocess.run([str(DRIVER),*args],capture_output=True,text=True,check=True)
 assert json.loads(r.stdout)==args
 for arg in ['--help','--version']:
    r=subprocess.run([str(BIN),arg],env={'HOME':'','PATH':'/nonexistent'},capture_output=True,text=True);assert r.returncode==0
 fake=Path(d)/'fake';record=Path(d)/'argv';fake.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["ARGV_RECORD"]).write_text(json.dumps(sys.argv[1:]));sys.exit(int(os.environ.get("EXIT","0")))\n');fake.chmod(0o700)
 for code in [0,7]:
    r=subprocess.run([str(DRIVER),'launch',str(fake),*args],env={**os.environ,'ARGV_RECORD':str(record),'EXIT':str(code)},capture_output=True,text=True)
    assert r.returncode==(0 if code==0 else 1) and json.loads(record.read_text())==args
print(f'Obsidian: {len(cases)} actual ELF project/Agora/error resolution cases, readonly registry, explicit bypass, literal launcher/failure and help/version passed; no GUI.')
