"""R3 fake startup core/native/bar model. No actual desktop service or GUI."""
import json
from pathlib import Path
from desktop_fixture import Backend as DesktopBackend,initial,state

class Backend(DesktopBackend):
    def query(self,key):
        if key=='instances':self.w['_native_seen']=True;return self.w.get('instances',[{'instance':self.w['instance']}])
        return super().query(key)
    def request(self,*args,**kwargs):
        w=self.w;f=w['flags']
        if args==('list',) and f.get('read_errors'):
            error=f['read_errors'].pop(0);w['events'].append(['request',['list']])
            raise RuntimeError(error)
        if args==('start','--neutral'):
            w['events'].append(['request',list(args)]);w['generation']=w.get('generation',0)+1
            sid='new-'+str(w['generation']);w['sessions'].append(sid);w['selected']=sid;w['revision']+=1
            if f.get('inject_session'):w['sessions'].append('concurrent');w['selected']='concurrent'
            return {'session':{'id':sid,'source':{'kind':'neutral'},'number':1,'name':'Neutral-1'}}
        reply=super().request(*args)
        if args==('list',):
            for row in reply['sessions']:
                if row['id'].startswith('new-'):row.update(number=1,name='Neutral-1')
        return reply

def cli(kind):
    import os,sys,fcntl
    path=Path(os.environ['DESKTOP_WORLD']);w=json.loads(path.read_text());b=Backend(w)
    try:
        if kind=='core':
            assert sys.argv[1:3]==['--json','session'];print(json.dumps(b.request(*sys.argv[3:])))
        elif kind=='native':
            args=sys.argv[1:];print(json.dumps(b.query(args[0])) if args[0] not in ('dispatch','eval') else b.ctl(*args))
        elif kind=='bar':
            marker=Path(os.environ['XDG_RUNTIME_DIR'])/'hyprland/session-startup.json'
            phase=json.loads(marker.read_text()).get('phase','invalid') if marker.exists() else 'absent'
            w.setdefault('bar_phases',[]).append(phase)
            with (marker.parent/'workspace-columns.lock').open('a') as stream:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        elif kind=='log':w['logs']=w.get('logs',0)+1
        else:raise AssertionError(kind)
    except RuntimeError as error:
        print(json.dumps({'code':str(error)}) if kind=='core' else 'error: '+str(error));sys.exit(1 if kind=='core' else 0)
    finally:path.write_text(json.dumps(w))
