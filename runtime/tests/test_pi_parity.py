#!/usr/bin/env python3
"""R5 black-box oracle parity. Private HOME and fake core/capture/terminal only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'target/release/session-pi'
ORACLE=ROOT.parent/'tools/runtime-migration/oracles/configs/session-manager/session-pi.py'
A='11111111-1111-1111-1111-111111111111'
B='22222222-2222-2222-2222-222222222222'
TAG='session:'+A

FAKE="""#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
w=json.loads(Path(os.environ['PI_WORLD']).read_text())
kind=Path(sys.argv[0]).name
record=[kind,sys.argv[1:]]
if kind=='agora-notify':
    record.append(os.environ.get('AGORA_NOTIFICATION_CONTEXT'))
if kind=='launch-terminal-command':
    record.extend([os.environ.get('AGORA_NOTIFICATION_CONTEXT'),os.environ.get('PI_KEEP')])
with open(os.environ['PI_LOG'],'a') as f:f.write(json.dumps(record)+'\\n')
if kind=='session-manager':
    assert sys.argv[1:] in [['--json','session','list'],['--json','project','list']]
    project=sys.argv[2]=='project'
    if w.get('project_code' if project else 'query_code'):sys.exit(1)
    print('not-json' if w.get('invalid_json') else json.dumps(w['projects' if project else 'state']))
elif kind=='agora-notify':
    assert sys.argv[1:]==['capture'] and 'AGORA_NOTIFICATION_CONTEXT' not in os.environ
    time.sleep(w.get('capture_wait',0))
    if w.get('capture_bytes'):
        sys.stdout.buffer.write(b'\\xff');sys.exit(0)
    print(w.get('capture','global'))
    sys.exit(w.get('capture_code',0))
else:
    assert kind=='launch-terminal-command'
    sys.exit(w.get('terminal_code',0))
"""

def execute(program,world,root,args=()):
    fixture=root/'world';fixture.write_text(json.dumps(world))
    log=root/'log';log.unlink(missing_ok=True)
    env={'HOME':str(root),'XDG_CONFIG_HOME':str(root/'config'),'PATH':'/usr/bin:/bin',
         'PI_WORLD':str(fixture),'PI_LOG':str(log),'AGORA_NOTIFICATION_CONTEXT':'session:'+B,
         'PI_KEEP':'literal $value; no shell','PYTHONDONTWRITEBYTECODE':'1'}
    env.update(world.get('environment',{}))
    result=subprocess.run([*program,*args],env=env,capture_output=True,text=True,timeout=8)
    records=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result,records

def main():
    count=0
    with tempfile.TemporaryDirectory(prefix='r5-parity-') as directory:
        root=Path(directory);bin=root/'.local/bin';bin.mkdir(parents=True)
        project=root/"Project with 'quotes' ; $() é";project.mkdir()
        agora=root/'Explicit Agora é';agora.mkdir()
        config=root/'config/agora-workflow/config.toml';config.parent.mkdir(parents=True)
        (root/'.config').symlink_to(root/'config',target_is_directory=True)
        for name in ['session-manager','agora-notify','launch-terminal-command']:
            f=bin/name;f.write_text(FAKE);f.chmod(0o700)
        link=root/'linked';link.symlink_to(project,target_is_directory=True)
        normal={'state':{'active_session_id':A,'sessions':[{'id':A,'source':{'kind':'project','project_name':project.name}}]},
                'projects':{'projects':[{'name':project.name,'path':str(project)}]},'capture':TAG}
        cases=[]
        def add(name,patch=None,args=(),config_value='default',expected_ok=True):
            world=copy.deepcopy(normal)
            if patch:patch(world)
            cases.append((name,world,args,config_value,expected_ok))
        add('active project')
        add('explicit agora',args=('--agora',))
        add('explicit bypass unavailable daemon',lambda w:w.update(query_code=1),('--agora',))
        add('unowned',lambda w:w.update(state={'active_session_id':None,'sessions':[]},capture='neutral'))
        add('neutral UUID',lambda w:w['state']['sessions'][0].update(source={'kind':'neutral'}))
        add('inactive sessions',lambda w:w['state'].update(active_session_id=None))
        add('project does not need Agora config',config_value=None)
        for value in ['global','neutral','session:'+B,'invalid','session:ABCDEFAB-ABCD-ABCD-ABCD-ABCDEFABCDEF','session:'+A+'\nextra','',TAG+' \n']:
            add('capture '+repr(value),lambda w,v=value:w.update(capture=v))
            add('explicit capture '+repr(value),lambda w,v=value:w.update(capture=v),('--agora',))
        add('capture invalid UTF-8',lambda w:w.update(capture_bytes=True))
        add('capture failure',lambda w:w.update(capture_code=1))
        add('capture timeout',lambda w:w.update(capture_wait=2.3))
        add('terminal fails',lambda w:w.update(terminal_code=3),expected_ok=False)
        for option in ['--unknown','--help','--agora=1','anything']:
            add('bad option '+option,args=(option,),expected_ok=False)
        add('extra options',args=('--agora','--agora'),expected_ok=False)
        add('daemon fails',lambda w:w.update(query_code=1),expected_ok=False)
        add('bad JSON',lambda w:w.update(invalid_json=True),expected_ok=False)
        add('project query fails',lambda w:w.update(project_code=1),expected_ok=False)
        add('missing project',lambda w:w['projects'].update(projects=[]),expected_ok=False)
        add('missing active',lambda w:w['state'].update(active_session_id=B),expected_ok=False)
        for source in [{},{'kind':'unknown'},{'kind':'neutral','extra':True},{'kind':'project'},{'kind':'project','project_name':12}]:
            add('invalid source '+repr(source),lambda w,s=source:w['state']['sessions'][0].update(source=s),expected_ok=False)
        for path in ['relative',str(root/'missing'),str(config),str(link),str(link)+'/']:
            add('invalid project path '+path,lambda w,p=path:w['projects']['projects'][0].update(path=p),expected_ok=False)
        add('normalized project path',lambda w:w['projects']['projects'][0].update(path=str(project)+'/./'))
        for value in [None,'not = [','agora_root=12','agora_root="relative"','agora_root="/does-not-exist-r5"','agora_root='+json.dumps(str(link))]:
            add('invalid config '+repr(value),args=('--agora',),config_value=value,expected_ok=False)
        add('default XDG Agora',lambda w:w.update(environment={'XDG_CONFIG_HOME':''}),('--agora',))
        add('unowned missing config',lambda w:w.update(state={'active_session_id':None,'sessions':[]}),config_value=None,expected_ok=False)
        add('Neutral missing config',lambda w:w['state']['sessions'][0].update(source={'kind':'neutral'}),config_value=None,expected_ok=False)
        add('TOML literal config',args=('--agora',),config_value="agora_root = '"+str(agora)+"'\n# comment\n[other]\nkeep=true\n")
        add('relative XDG project unaffected',lambda w:w.update(environment={'XDG_CONFIG_HOME':'relative'}))
        add('relative XDG Agora refused',lambda w:w.update(environment={'XDG_CONFIG_HOME':'relative'}),('--agora',),expected_ok=False)
        for name,world,args,content,ok in cases:
            config.unlink(missing_ok=True)
            if content is not None:config.write_text('agora_root='+json.dumps(str(agora))+'\n' if content=='default' else content)
            old,old_calls=execute(['/usr/bin/python3',str(ORACLE)],world,root,args)
            new,new_calls=execute([str(BIN)],world,root,args)
            assert (old.returncode==0)==ok,(name,old.stderr)
            assert (new.returncode==0)==ok,(name,new.stderr)
            assert old_calls==new_calls,(name,old_calls,new_calls,new.stderr)
            terminals=[row for row in new_calls if row[0]=='launch-terminal-command']
            if terminals:
                assert len(terminals)==1
                row=terminals[0];assert row[1][1]=='env' and row[1][3]=='pi'
                assert row[1][2]=='AGORA_NOTIFICATION_CONTEXT='+row[2] and row[3]=='literal $value; no shell'
                assert next(r for r in new_calls if r[0]=='agora-notify')[2] is None
            count+=1
        # Missing helper is a conservative global origin, never a launch failure.
        helper=bin/'agora-notify';helper.rename(bin/'capture-disabled')
        world=copy.deepcopy(normal)
        old,old_calls=execute(['/usr/bin/python3',str(ORACLE)],world,root)
        new,new_calls=execute([str(BIN)],world,root)
        assert old.returncode==new.returncode==0 and old_calls==new_calls
        assert new_calls[-1][2]=='global'
        (bin/'capture-disabled').rename(helper)
        terminal=bin/'launch-terminal-command';terminal.rename(bin/'terminal-disabled')
        old,old_calls=execute(['/usr/bin/python3',str(ORACLE)],world,root)
        new,new_calls=execute([str(BIN)],world,root)
        assert old.returncode==new.returncode==1 and old_calls==new_calls
        (bin/'terminal-disabled').rename(terminal)
        # Entry points keep their existing public command names; no desktop writes.
        keybind=(ROOT.parent/'configs/hypr/files/keybinds.lua').read_text()
        assert 'mainMod .. " + P"' in keybind and '$HOME/.local/bin/session-pi' in keybind
        entry=(ROOT.parent/'configs/session-manager/session-pi.desktop').read_text()
        assert '\nExec=session-pi --agora\n' in entry
        version=subprocess.run([str(BIN),'--version'],env={'PATH':'/usr/bin:/bin'},capture_output=True,text=True)
        assert version.returncode==0 and '(Rust; captured launch origin)' in version.stdout
        # Documented stricter v3 envelopes: old parser ignored malformed inactive rows.
        for mutate in [
            lambda w:w['state'].pop('active_session_id'),
            lambda w:w['state']['sessions'].append(copy.deepcopy(w['state']['sessions'][0])),
            lambda w:w['state']['sessions'].append({'id':B,'source':{'kind':'neutral','extra':1}})
        ]:
            world=copy.deepcopy(normal);mutate(world)
            result,calls=execute([str(BIN)],world,root)
            assert result.returncode==1 and not any(row[0]=='launch-terminal-command' for row in calls)
        print(f'R5: {count} differential CLI cases + 3 strict-v3 refusals passed; missing helper/terminal, literal cwd/env/argv, frozen origin, no real Pi.')
if __name__=='__main__':main()
