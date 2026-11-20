#!/usr/bin/env python3
"""Test default-manager-only setup and SUPER+E without launching any GUI."""
import json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
FAKE="""#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['HOME']);p=root/'state';s=json.loads(p.read_text())
name=Path(sys.argv[0]).name;a=sys.argv[1:]
with (root/'calls').open('a') as f:f.write(json.dumps([name,a])+'\\n')
if name=='xdg-mime':
    if a[:2]==['query','default']:print(s['xdg'].get(a[2],''))
    elif a[0]=='default':
        if os.environ.get('FAIL_SET'):sys.exit(9)
        s['xdg'][a[2]]=a[1];p.write_text(json.dumps(s))
    else:raise AssertionError(a)
elif name=='gio':
    assert a[:2]==['mime','inode/directory']
    if len(a)==2:print('Default application for inode/directory: '+s['gio'])
    else:s['gio']=a[2];p.write_text(json.dumps(s))
elif name=='xdg-open':(root/'opened').write_text(json.dumps([os.environ['DEFAULT_HANDLER'],a]))
else:sys.exit('must not start/quit or configure unrelated applications: '+name)
"""
with tempfile.TemporaryDirectory(prefix='default-manager-') as d:
    root=Path(d)/"Home with 'quotes' $value";root.mkdir();bin=root/'bin';bin.mkdir()
    for name in ['thunar','xdg-mime','gio','xdg-open','xdg-settings','xfconf-query','fish','update-desktop-database']:
        p=bin/name;p.write_text(FAKE);p.chmod(0o700)
    env={**os.environ,'HOME':str(root),'XDG_CONFIG_HOME':str(root/'config'),'PATH':str(bin)+':/usr/bin:/bin'}
    state=root/'state'
    initial={'xdg':{'inode/directory':'other.desktop','application/x-gnome-saved-search':'other.desktop','text/plain':'personal.desktop'},'gio':'other.desktop'}
    state.write_text(json.dumps(initial))
    def configure(*args,**extra):
        return subprocess.run(['bash',str(HERE/'configure_default_applications.sh'),*args],env={**env,**extra},capture_output=True,text=True)
    r=configure('--file-manager-only');assert r.returncode==0,r.stderr
    result=json.loads(state.read_text())
    assert result['xdg']['inode/directory']=='thunar.desktop' and result['gio']=='thunar.desktop'
    assert result['xdg']['text/plain']=='personal.desktop'
    before=state.read_bytes();(root/'calls').unlink()
    assert configure('--file-manager-only').returncode==0 and state.read_bytes()==before
    calls=[json.loads(line) for line in (root/'calls').read_text().splitlines()]
    assert all(name in ['xdg-mime','gio'] for name,_ in calls)
    assert not (root/'.local').exists()
    assert configure('--unknown').returncode==2
    state.write_text(json.dumps(initial));assert configure('--file-manager-only',FAIL_SET='1').returncode!=0

    # Load the actual keybindings with a fake compositor API; callbacks never run.
    harness=root/'binding.lua';harness.write_text("""
local proxy
proxy=setmetatable({}, {__index=function() return proxy end,__call=function() return {} end})
local binds={}
hl={bind=function(key,action) assert(not binds[key]);binds[key]=action end,
    dsp=setmetatable({exec_cmd=function(cmd) return {command=cmd} end},{__index=function() return proxy end})}
dofile(arg[1])
assert(binds["SUPER + E"].command==[["$HOME/.local/bin/session-files"]])
io.write(binds["SUPER + E"].command)
""")
    r=subprocess.run(['lua',str(harness),str(HERE.parent/'hypr/files/keybinds.lua')],env=env,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert r.stdout=='"$HOME/.local/bin/session-files"'
print('Default file manager: narrow/idempotent setup, preserved other defaults, failure handling and contextual native SUPER+E binding passed; no GUI.')
