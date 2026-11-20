#!/usr/bin/env python3
"""Session lifecycle and single-workspace integration with fake API/compositor only."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import uuid

SOURCE = Path(__file__).with_name('session-desktop.py')
os.environ['SESSION_COLUMNS_SCRIPT'] = str(SOURCE.parents[1] / 'hypr/files/Scripts/workspace-columns.py')
spec = importlib.util.spec_from_file_location('desktop', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix='session-desktop-') as directory:
    root = Path(directory)
    module.columns.RUNTIME = root
    module.columns.STATE = root/'state.json'
    active = [1]
    clients = [{'workspace': {'id':1,'name':'1'}}]
    monitors = [{'focused':True,'activeWorkspace':{'id':1},'specialWorkspace':{'name':''}}]
    sessions = []
    selected = [None]
    events = []
    def query(key):
        return {'clients':clients,'monitors':monitors,
                'workspaces':[{'id':ws} for ws in sorted({active[0],*(c['workspace']['id'] for c in clients if c['workspace']['id']>0)})]}[key]
    def focus(ws):
        events.append(('focus',ws)); active[0]=ws; monitors[0]['activeWorkspace']['id']=ws
    def dispatch(expression):
        assert expression.startswith('hl.dsp.workspace.toggle_special('), expression
        events.append(('hide',expression)); monitors[0]['specialWorkspace']['name']=''
    def request(*args):
        events.append(('request',args))
        if args==('list',): return {'sessions':[{'id':s} for s in sessions],'active_session_id':selected[0]}
        if args in [('start','--neutral'),('start','--project','Project')]:
            sid=str(uuid.UUID(int=len(sessions)+1)); sessions.append(sid); selected[0]=sid
            return {'session':{'id':sid}}
        if args==('deactivate',): selected[0]=None; return {'active_session_id':None}
        if args[0]=='switch' and args[1] in sessions:
            selected[0]=args[1]; return {'session':{'id':args[1]}}
        if args[0]=='stop' and args[1] in sessions:
            sessions.remove(args[1])
            if selected[0]==args[1]: selected[0]=None
            return {'stopped_session_id':args[1]}
        raise AssertionError(args)
    module.columns.query=query; module.columns.active=lambda:active[0]
    module.columns.focus=focus; module.columns.focus_empty=focus; module.columns.dispatch=dispatch; module.request=request

    a=module.invoke('start',{'kind':'project','project_name':'Project'})['session']['id']
    first=active[0]
    assert first==2 and module.columns.load()['owners']=={'1':'neutral','2':a}
    module.invoke('deactivate')
    assert active[0]==1 and selected[0] is None
    assert module.columns.load()['owners']=={'1':'neutral'}, 'departed empty workspace must be forgotten'
    assert sessions==[a], 'empty workspace cleanup must not stop a logical session'
    module.invoke('switch',a)
    assert active[0]>first and module.status()['context_confirmed']
    assert clients==[{'workspace':{'id':1,'name':'1'}}]
    b=module.invoke('start',{'kind':'neutral'})['session']['id']
    ws_b=active[0]
    assert b!=a and module.columns.load()['owners']=={'1':'neutral',str(ws_b):b}
    clients.append({'workspace':{'id':ws_b,'name':str(ws_b)}})
    try: module.invoke('stop',b); raise AssertionError('normal window must block stop')
    except RuntimeError as error: assert 'open windows' in str(error)
    clients.pop()
    clients.append({'workspace':{'id':-9,'name':f'special:sm-{a}-ai'}})
    try: module.invoke('stop',a); raise AssertionError('inactive UUID scratchpad must block stop without a normal workspace')
    except RuntimeError as error: assert 'open windows' in str(error)
    clients.pop()
    monitors[0]['specialWorkspace']['name']='special:global'
    module.invoke('switch',a)
    assert ('hide','hl.dsp.workspace.toggle_special("global")') in events
    assert module.status()['context_confirmed']
    for invalid in ['special:bad"name']:
        monitors[0]['specialWorkspace']['name']=invalid
        before=list(events)
        try: module.invoke('deactivate'); raise AssertionError('unsafe special name')
        except RuntimeError as error: assert 'unsafe special' in str(error)
        assert selected[0]==a and events[len(before):]==[('request',('list',))]
    monitors[0]['specialWorkspace']['name']='special:session-ai'
    module.columns.dispatch=lambda expression:events.append(('failed-hide',expression))
    try: module.invoke('deactivate'); raise AssertionError('failed hide must not mutate logical state')
    except RuntimeError as error: assert 'did not hide' in str(error)
    assert selected[0]==a
    monitors[0]['specialWorkspace']['name']=''; module.columns.dispatch=dispatch
    module.invoke('stop',a)
    assert selected[0]==b and active[0]!=1 and sessions==[b]
    assert module.status()['context_confirmed']
    module.invoke('switch',b)
    before_ws=active[0]
    module.columns.STATE.unlink()  # A graphical restart loses only desktop metadata.
    module.invoke('switch',b)
    assert active[0]>before_ws and module.columns.load()['owners']=={'1':'neutral',str(active[0]):b}
    assert clients==[{'workspace':{'id':1,'name':'1'}}]

    module.columns.focus=lambda ws:(_ for _ in ()).throw(RuntimeError('focus failed'))
    try: module.invoke('deactivate'); raise AssertionError('focus failure must be explicit')
    except RuntimeError as error: assert str(error)=='focus failed'
    assert selected[0] is None and not module.status()['context_confirmed']
    module.columns.focus=focus; module.invoke('deactivate')
    assert module.status()['context_confirmed'] and active[0]==1

    monitors.append({'focused':False,'specialWorkspace':{'name':''}})
    before=(list(events),module.columns.STATE.read_bytes())
    try: module.invoke('start',{'kind':'neutral'}); raise AssertionError('multi-monitor context policy undefined')
    except RuntimeError as error: assert 'one monitor' in str(error)
    assert (events,module.columns.STATE.read_bytes())==before
    monitors.pop()
    for source in ['Project',{'kind':'neutral','project_name':''}]:
        before=list(events)
        try: module.invoke('start',source); raise AssertionError('reject obsolete or open source shapes')
        except RuntimeError as error: assert 'invalid v3' in str(error)
        assert events==before

    errors=[]; started=threading.Event()
    with (root/'workspace-columns.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX); before=list(events)
        def blocked():
            started.set()
            try: module.invoke('deactivate')
            except Exception as error: errors.append(error)
        worker=threading.Thread(target=blocked); worker.start(); assert started.wait(2)
        time.sleep(0.05); assert events==before
        fcntl.flock(lock,fcntl.LOCK_UN)
    worker.join(timeout=3); assert not worker.is_alive() and not errors
print('Single-workspace session routing: empty cleanup, UUID guards, unowned retention, failures and shared lock passed.')
