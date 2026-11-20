#!/usr/bin/env python3
"""R4 real Rust/frozen Python CLI differential, private status and sender only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'target/release/agora-notify'
ORACLE=ROOT.parent/'tools/runtime-migration/oracles/configs/session-manager/agora-notify.py'
A='11111111-1111-1111-1111-111111111111'
B='22222222-2222-2222-2222-222222222222'
STATUS={'context_confirmed':True,'displayed_context':A,'active_session_id':A,'sessions':[{'id':A}]}

def cases():
    rows=[]
    def add(name,args,**kw):rows.append({'name':name,'args':args,**kw})
    add('capture_session',['capture'])
    add('capture_unowned',['capture'],status={'context_confirmed':True,'displayed_context':'neutral','active_session_id':None})
    for context in ['global','neutral','session:'+A,'','unknown','session:'+A.upper(),'session:notuuid','session:'+A+'\n']:
        add('capture_inherited_'+repr(context),['capture'],context=context,status='broken')
    for status in [{},[],{'context_confirmed':False},{'context_confirmed':1},dict(STATUS,active_session_id=B),dict(STATUS,sessions=[]),dict(STATUS,displayed_context='unknown'),dict(STATUS,displayed_context='session:'+A),dict(STATUS,sessions=None),'broken']:
        add('bad_status_'+repr(status),['capture'],status=status)
    for code in [1,9]:add('failed_status_'+str(code),['capture'],status_exit=code)
    for args in [[],['capture','extra'],['capture','--bad'],['send'],['send','--global'],['send','--bad','x'],['send','x','y','z'],['send','--global','--context','global','x'],['send','-u','bad','x'],['send','-t','1.1','x']]:add('syntax_'+repr(args),args)
    for args in [['send','hello'],['send','hello','body'],['send','--','$(literal); x','Body "quoted"'],['send','--global','hello'],['send','--context','session:'+A,'hello'],['send','--urgency=critical','--app-name=Pi','-t-1','-r0','summary'],['send','summary','-aliteral','body','-u','low'],['send','--app','test','--expire','1_000','--replace','+0009','x'],['send','-t','+0000010','-r','4294967295','x'],['send','-t','999999999999999999999999999999','x'],['send','--context','neutral','--context','global','x'],['send','--global','--global','x'],['send','--','-a','-u']]:
        add('send_'+repr(args),args)
    for value in ['-1','4294967296','99999999999999999999999999']:
        add('replace_out_of_range_'+value,['send','-r',value,'hello'])
    for value in ['','unknown','session:bad','session:'+A.upper()]:add('bad_explicit_'+repr(value),['send','--context',value,'x'])
    for value in ['global','neutral','session:'+A,'bad','']:
        add('send_inherited_'+repr(value),['send','x'],context=value)
        add('global_beats_inherited_'+repr(value),['send','--global','x'],context=value)
        add('explicit_beats_inherited_'+repr(value),['send','--context','neutral','x'],context=value)
    for value in [1,9]:add('sender_failure_'+str(value),['send','--global','x'],sender_exit=value)
    for args in [['send','-'],['send','-1'],['send','-.5'],['send','-1.5'],['send','--context','-1.5','x'],['send','--app-name','-','x']]:add('numeric_or_dash_'+repr(args),args)
    return rows

class Environment:
    def __init__(self,directory,row):
        self.root=Path(directory);binary=self.root/'.local/bin';binary.mkdir(parents=True)
        status=binary/'session-desktop';status.write_text('''#!/usr/bin/python3
import os,sys
from pathlib import Path
r=Path(os.environ['HOME']);p=r/'captures';p.write_text(p.read_text()+'status\\n' if p.exists() else 'status\\n');print((r/'status').read_text());sys.exit(int(os.environ.get('STATUS_EXIT','0')))
''');status.chmod(0o700)
        sender=binary/'notify-send';sender.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
with (Path(os.environ['HOME'])/'sent').open('a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
sys.exit(int(os.environ.get('SENDER_EXIT','0')))
''');sender.chmod(0o700)
        value=row.get('status',STATUS);(self.root/'status').write_text(value if isinstance(value,str) else json.dumps(value))
        self.env={'HOME':str(self.root),'PATH':str(binary),'STATUS_EXIT':str(row.get('status_exit',0)),'SENDER_EXIT':str(row.get('sender_exit',0))}
        if 'context' in row:self.env['AGORA_NOTIFICATION_CONTEXT']=row['context']
    def call(self,command,args):
        result=subprocess.run([*command,*args],env=self.env,capture_output=True,text=True,timeout=4)
        return {'code':result.returncode,'stdout':result.stdout,'captures':(self.root/'captures').read_text() if (self.root/'captures').exists() else '',
                'sent':(self.root/'sent').read_text() if (self.root/'sent').exists() else ''}

class Parity(unittest.TestCase):
    def test_cli_cases(self):
        rows=cases()
        for row in rows:
            with self.subTest(name=row['name']),tempfile.TemporaryDirectory(prefix='r4-py-') as p,tempfile.TemporaryDirectory(prefix='r4-rust-') as r:
                self.assertEqual(Environment(p,row).call([sys.executable,str(ORACLE)],row['args']),Environment(r,row).call([str(BIN)],row['args']),row['name'])
        print(f'R4: {len(rows)} CLI differential scenarios passed against frozen Python.')
    def test_capture_then_switch_send_never_recaptures(self):
        with tempfile.TemporaryDirectory(prefix='r4-once-') as directory:
            e=Environment(directory,{'args':[]});snapshot=e.call([str(BIN)],['capture'])['stdout'].strip()
            (e.root/'status').write_text(json.dumps(dict(STATUS,displayed_context=B,active_session_id=B,sessions=[{'id':B}])))
            result=e.call([str(BIN)],['send','--context',snapshot,'synthetic'])
            self.assertEqual(result['code'],0);self.assertEqual(result['captures'],'status\n');self.assertIn('string:x-agora-context:session:'+A,json.loads(result['sent'])[1])

if __name__=='__main__':unittest.main()
