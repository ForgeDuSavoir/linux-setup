#!/usr/bin/env python3
"""Actual session-files ELF, fake readonly clients/opener, no application launch."""
import copy,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BIN=ROOT/'target/release/session-files'
A='11111111-1111-1111-1111-111111111111';B='22222222-2222-2222-2222-222222222222'
def status(sid=A,kind='project'):
    return {'context_confirmed':True,'active_session_id':sid,'displayed_context':sid or 'neutral',
            'sessions':[] if sid is None else [{'id':sid,'source':{'kind':kind,**({'project_name':'P'} if kind=='project' else {})}}]}
FAKE="""#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
root=Path(os.environ['HOME']);w=json.loads((root/'world').read_text());tool=Path(sys.argv[0]).name
with (root/'calls').open('a') as f:f.write(json.dumps([tool,sys.argv[1:]])+'\\n')
if tool=='session-desktop':
    assert sys.argv[1:]==['status']
    count=root/'count';n=int(count.read_text()) if count.exists() else 0;count.write_text(str(n+1))
    if w.get('timeout')=='status':time.sleep(3)
    if n and w.get('folder_change'):
        p=root/w['folder_name'];p.rename(root/'old-folder')
        if w['folder_change']=='replace':p.mkdir()
    if w.get('status_fail'):sys.exit(3)
    states=w['statuses'];print('bad JSON' if w.get('status_json') else json.dumps(states[min(n,len(states)-1)]))
elif tool=='session-manager':
    assert sys.argv[1:]==['--json','project','list']
    if w.get('timeout')=='catalogue':time.sleep(3)
    if w.get('catalogue_fail'):sys.exit(3)
    print('bad JSON' if w.get('catalogue_json') else json.dumps(w['catalogue']))
else:
    assert tool=='xdg-open'
    (root/'opened').write_text(json.dumps([sys.argv[1:],os.environ.get('DEFAULT_HANDLER')]))
    sys.exit(w.get('opener_fail',0))
"""
def execute(root,w):
    root.mkdir();bin=root/'.local/bin';bin.mkdir(parents=True)
    folder=root/"Project 'quotes' $() é";folder.mkdir()
    world={'statuses':[status(),status()],'catalogue':{'projects':[{'name':'P','path':str(folder)}]},'folder_name':folder.name,**copy.deepcopy(w)}
    if 'path' in w:
        if w['path']=='missing':path=root/'absent'
        elif w['path']=='relative':path=Path('relative')
        elif w['path']=='file':path=root/'world'
        elif w['path']=='link':
            path=root/'linked';path.symlink_to(folder,target_is_directory=True)
        elif w['path']=='denied':path=folder;folder.chmod(0)
        world['catalogue']={'projects':[{'name':'P','path':str(path)}]}
    for name in ['session-desktop','session-manager','xdg-open']:
        p=bin/name;p.write_text(FAKE);p.chmod(0o700)
    if w.get('missing_status'):(bin/'session-desktop').unlink()
    (root/'world').write_text(json.dumps(world))
    env={'HOME':str(root),'PATH':str(bin)+':/usr/bin:/bin','AGORA_NOTIFICATION_CONTEXT':'session:'+B,'DEFAULT_HANDLER':w.get('handler','thunar.desktop')}
    r=subprocess.run([str(BIN),*w.get('args',[])],env=env,capture_output=True,text=True,timeout=9)
    opened=json.loads((root/'opened').read_text()) if (root/'opened').exists() else None
    calls=[json.loads(line) for line in (root/'calls').read_text().splitlines()] if (root/'calls').exists() else []
    assert not list(root.rglob('app-usage.json'))
    return r,opened,calls,folder

cases=[
 ('project',{},'project'),('other default',{'handler':'other.desktop'},'project'),
 ('neutral',{'statuses':[status(kind='neutral')]},'home'),
 ('none',{'statuses':[status(None)]},'home'),
 ('unknown',{'statuses':[dict(status(),context_confirmed=False)]},'home'),
 ('inconsistent',{'statuses':[dict(status(),displayed_context=B)]},'home'),
 ('absent source',{'statuses':[dict(status(),sessions=[{'id':A}])]},'home'),
 ('invalid active',{'statuses':[dict(status(),active_session_id=B)]},'home'),
 ('missing project',{'catalogue':{'projects':[]}},'home'),
 ('bad catalogue shape',{'catalogue':{'projects':[{'name':'P'}]}},'home'),
 ('ambiguous catalogue',{'catalogue':{'projects':[{'name':'P','path':'/one'},{'name':'P','path':'/two'}]}},'home'),
 ('status failure',{'status_fail':True},'home'),('status JSON',{'status_json':True},'home'),
 ('catalogue failure',{'catalogue_fail':True},'home'),('catalogue JSON',{'catalogue_json':True},'home'),
 ('missing helper',{'missing_status':True},'home'),
 ('switch during query',{'statuses':[status(),status(B)]},'home'),
 ('source changes',{'statuses':[status(),status(kind='neutral')]},'home'),
 ('folder removed',{'folder_change':'remove'},'home'),('folder replaced',{'folder_change':'replace'},'home'),
 ('status timeout',{'timeout':'status'},'home'),('catalogue timeout',{'timeout':'catalogue'},'home'),
 ('failed opener',{'opener_fail':7},'project'),
]
for mode in ['missing','relative','file','link']:cases.append(('bad path '+mode,{'path':mode},'home'))
if os.geteuid()!=0:cases.append(('inaccessible',{'path':'denied'},'home'))
with tempfile.TemporaryDirectory(prefix='session-files-') as d:
    root=Path(d)
    for i,(name,w,expected) in enumerate(cases):
        home=root/(str(i)+" Home 'quotes'");r,opened,calls,folder=execute(home,w)
        assert r.returncode==(1 if w.get('opener_fail') else 0),(name,r.stderr)
        assert opened==[[str(folder if expected=='project' else home)],w.get('handler','thunar.desktop')],(name,opened,r.stderr)
        assert sum(row[0]=='xdg-open' for row in calls)==1,(name,calls)
        assert all(row[0] in ['session-desktop','session-manager','xdg-open'] for row in calls)
    for i,args in enumerate([['--version'],['--help'],['-h'],['unexpected-path']]):
        r,opened,calls,_=execute(root/('syntax'+str(i)),{'args':args})
        assert r.returncode==(1 if args==['unexpected-path'] else 0) and opened is None and not calls
print(f'session-files: {len(cases)} actual CLI routing/fallback/opener cases plus help/version/syntax passed; HOME fallbacks, literal paths and alternate default, no GUI.')
