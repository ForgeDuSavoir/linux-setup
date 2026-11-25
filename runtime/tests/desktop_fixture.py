"""Shared private fake core/native model for Rust CLI and frozen Python oracle."""
import copy
import json
import re
import subprocess
from pathlib import Path

SLOTS=['ai','notes','tasks','4','5']
def initial(sessions=('A','B','C'),selected='B'):
    return {'sessions':list(sessions),'selected':selected,'revision':0,
            'active':ord(selected)-ord('A')+2 if selected else 1,
            'clients':[{'address':'legacy','workspace':{'id':1,'name':'1'}}],
            'special':'','events':[],'codes':[],'flags':{},'window':{}}
def state(world):
    return {'version':3,'order':[1,*range(2,2+len(world['sessions']))],
            'owners':{'1':'neutral',**{str(i):sid for i,sid in enumerate(world['sessions'],2)}},
            'preferred':{},'next_id':len(world['sessions'])+2}
class Backend:
    def __init__(self,world):self.w=world
    def request(self,*args):
        w=self.w;f=w['flags'];w['events'].append(['request',list(args)])
        if args==('list',):
            w['_lists']=w.get('_lists',0)+1
            if f.get('after_focus_none') and any(e[0]=='focus' for e in w['events']):w['selected']=None
            revision=w['revision']+(1 if f.get('second_list_revision') and w['_lists']==2 else 0)
            return {'sessions':[{'id':sid,'source':w.get('sources',{}).get(sid,{'kind':'neutral'})} for sid in w['sessions']], 'active_session_id':w['selected'],'revision':revision}
        if args[0]=='switch':
            if f.get('fail_switch'):raise RuntimeError('not_found.session')
            w['selected']=args[1];w['revision']+=1
            return {'session':{'id':'wrong' if f.get('invalid_switch') else w['selected']}}
        if args[0]=='stop':
            if f.get('fail_stop'):raise RuntimeError('stop rejected')
            w['sessions'].remove(args[1]);w['revision']+=1
            if w['selected']==args[1] or f.get('after_stop_none'):w['selected']=None
            if f.get('lost_reply'):raise RuntimeError('transport.uncertain')
            return {'stopped_session_id':args[1]}
        if args[0]=='start':
            sid='D';w['sessions'].append(sid);w['selected']=sid;w['revision']+=1
            source={'kind':'neutral'} if args[1]=='--neutral' else {'kind':'project','project_name':args[2]}
            w.setdefault('sources',{})[sid]=source
            return {'session':{'id':sid,'source':source,'number':1}}
        if args[0]=='deactivate':
            w['selected']=None;w['revision']+=1;return {'active_session_id':None}
        raise AssertionError(args)
    def query(self,key):
        self.w['_native_seen']=True
        w=self.w
        if key=='monitors':return copy.deepcopy(w.get('monitors',[{'focused':True,'activeWorkspace':{'id':w['active']},'specialWorkspace':{'name':w['special']}}]))
        if key=='clients':return copy.deepcopy(w['clients'])
        if key=='workspaces':return [{'id':ws} for ws in sorted({w['active'],1,*(c['workspace']['id'] for c in w['clients'] if c['workspace']['id']>0)})]
        if key=='activeworkspace':return {'id':w['active']}
        if key=='activewindow':return copy.deepcopy(w['window'])
        raise AssertionError(key)
    def focus(self,ws):
        w=self.w;f=w['flags'];w['events'].append(['focus',ws])
        if f.get('fail_focus'):raise RuntimeError('focus failed')
        if not f.get('silent_focus'):w['active']=ws
        if f.get('late_window'):
            ws=f.get('late_window_ws',3);w['clients'].append({'workspace':{'id':ws,'name':str(ws)}})
    def ctl(self,*args):
        kind,code=args;self.w['codes'].append([kind,code]);f=self.w['flags']
        if 'toggle_special' in code:
            self.w['events'].append(['hide',code]);self.w['special']='';return 'ok'
        if 'window.close' in code:
            window=copy.deepcopy(self.w['window']);window.setdefault('mapped',True);window.setdefault('visible',True)
            if f.get('native_address'):window['address']=f['native_address']
            if f.get('native_invisible'):window['visible']=False
            # JSON is converted explicitly to Lua scalars/tables, not evaluated as Lua.
            def lua(v):
                if v is None:return 'nil'
                if isinstance(v,bool):return str(v).lower()
                if isinstance(v,(int,float)):return str(v)
                if isinstance(v,str):return json.dumps(v)
                return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
            special={'name':self.w['special']} if self.w['special'] else None
            prefix='local w='+lua(window)+'; local ws='+lua({'id':f.get('native_ws',self.w['active'])})+';local sp='+lua(special)+''';local calls=0
hl={get_active_workspace=function() return ws end,get_active_special_workspace=function() return sp end,get_active_window=function() return w end,
dsp={window={close=function(opts) assert(opts.window=='address:'..w.address); return opts end}},dispatch=function(opts) calls=calls+1 end}
'''
            result=subprocess.run(['/usr/bin/lua','-'],input=prefix+code+'\nassert(calls==1)\n',text=True,capture_output=True,timeout=2)
            if result.returncode:raise RuntimeError('visible close target changed; close refused')
            self.w['events'].append(['close',window['address']]);return 'ok'
        ws=int(re.search(r'workspace = (\d+)',code).group(1))
        if kind=='eval' and f.get('fresh_race'):raise RuntimeError('workspace target already exists')
        self.focus(ws);return 'ok'

def cli(kind):
    import os,sys
    path=Path(os.environ['DESKTOP_WORLD']);world=json.loads(path.read_text());b=Backend(world)
    try:
        if kind=='core':
            assert sys.argv[1:3]==['--json','session'];value=b.request(*sys.argv[3:]);print(json.dumps(value))
        else:
            args=sys.argv[1:]
            print(json.dumps(b.query(args[0])) if args[0] not in ('dispatch','eval') else b.ctl(*args))
    except RuntimeError as error:
        print(json.dumps({'code':str(error)}) if kind=='core' else 'error: '+str(error));sys.exit(1 if kind=='core' else 0)
    finally:path.write_text(json.dumps(world))
