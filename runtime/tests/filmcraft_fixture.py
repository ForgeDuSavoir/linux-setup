"""Synthetic project plus strict CLI/FFmpeg stand-ins; no GUI or user media."""
import copy,json,os,sys,time,wave
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'target/release/filmcraft-patch-desktop-audio'
ORACLE=ROOT.parent/'tools/runtime-migration/oracles/scripts/filmcraft-patch-desktop-audio/filmcraft-patch-desktop-audio.py'
def fixture(source='recording.mkv',fps=(30,1),ticks=1000):
    tracks=[];raw_tracks=[]
    for i in range(4):
        items=[{'clip':i*10+1,'start':0,'duration':10*ticks,'sourceIn':3*ticks,'sourceOut':13*ticks,'item':1,'link':101},
               {'clip':i*10+2,'start':10*ticks,'duration':20*ticks,'sourceIn':25*ticks,'sourceOut':45*ticks,'item':1,'link':102}]
        tracks.append({'id':100+i,'items':items})
        raw_tracks.append({'id':100+i,'name':'Audio '+str(i+1),'items':[{**c,'source_channels':[i]} for c in items],'volume':1})
    before={'duration':60*ticks,'durationFrames':60,'video':[{'id':55,'items':[{'clip':900,'duration':30*ticks}]}],'audio':tracks}
    raw={'project':{'items':{'1':{'kind':{'Media':{'media':{'File':{'path':source}}}}},'2':{'kind':{'Sequence':{'settings':{'frame_rate':{'num':fps[0],'den':fps[1]}},'audio_tracks':raw_tracks}}}}},'_inspect':before,'fixture_unknown':123456789012345678901234567890}
    return raw

def cli():
    args=sys.argv[1:];tool=Path(sys.argv[0]).name
    world_path=Path(os.environ['FILM_WORLD']);w=json.loads(world_path.read_text());parent=world_path.parent
    if tool=='ffprobe':stage='probe'
    elif tool=='ffmpeg':stage='pad' if 'apad' in args else 'extract'
    else:
        assert args[:1]==['--project'];project=Path(args[1])
        stage='import' if 'file.import' in args else 'batch' if 'run' in args else 'relink' if 'media.relink' in args else 'missing' if 'media.findMissing' in args else 'tree' if args[-1]=='project' else 'before' if project.name=='premontage.fcproj' else 'after'
    stdin=sys.stdin.read() if stage=='batch' else None
    with open(parent/'calls','a') as f:f.write(json.dumps([tool,args,stdin])+'\n')
    if w.get('sleep')==stage:time.sleep(30)
    if w.get('fail')==stage:print('synthetic CLI failure',file=sys.stderr);sys.exit(8)
    if w.get('bad_json')==stage:print('not JSON');return
    if tool=='ffprobe':
        print(json.dumps({'streams':w.get('streams',[{'channels':2},{'channels':2}])}));return
    if tool=='ffmpeg':
        target=Path(args[-1]);rate=w.get('rate',48000)
        if stage=='extract':
            assert args[args.index('-map')+1]=='0:a:1' and args[args.index('-af')+1]=='aresample=async=1:first_pts=0'
            frames=w.get('frames',96000)
        else:
            seconds=Fraction(args[args.index('-t')+1])
            frames=(seconds*rate).__ceil__() if not w.get('bad_pad') else 1
        if w.get('bad_wav')=='tiny':target.write_bytes(b'broken');return
        if w.get('bad_wav')=='header':target.write_bytes(b'?'*2000);return
        with wave.open(str(target),'wb') as f:
            f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b'\x01\0\x02\0'*frames)
        if w.get('wav_race') and stage=='extract':
            dest=parent/'recording_bureau.wav'
            if w['wav_race']=='file':dest.write_bytes(b'foreign WAV')
            else:dest.symlink_to('foreign')
        return
    if stage=='import':
        target=Path(args[args.index('--save-as')+1]);raw=json.loads(project.read_text())
        raw['project']['items']['9']={'kind':{'Media':{'media':{'File':{'path':str(parent/'recording_bureau.wav')}}}}}
        target.write_text(json.dumps(raw));print(json.dumps({'items':[9]}));return
    raw=json.loads(project.read_text());seq=raw['project']['items']['2']['kind']['Sequence']
    if stage in ['before','after']:
        info=copy.deepcopy(raw['_inspect'])
        if stage=='after':
            k=w.get('mutate')
            if k=='durationFrames':info['durationFrames']+=1
            elif k=='video':info['video']=[]
            elif k in ['start','duration','sourceIn','sourceOut','link','clip']:info['audio'][0]['items'][0][k]+=1
            elif k=='source':info['audio'][0]['items'][0]['item']=9
            elif k=='count':info['audio'][0]['items'].pop()
        print(json.dumps(info));return
    if stage=='tree':
        rows=[{'item':9,'name':'recording_bureau.wav','type':'Audio'}]
        if w.get('tree')=='none':rows=[]
        if w.get('tree')=='duplicate':rows*=2
        print(json.dumps({'root':{'children':rows}}));return
    if stage=='relink':
        params=json.loads(args[-1]);assert params=={'item':9,'path':'recording_bureau.wav','relinkOthers':False}
        raw['project']['items']['9']['kind']['Media']['media']['File']['path']=params['path']
        project.write_text(json.dumps(raw))
        print(json.dumps({'relinked':[{'path':params['path']}],'remaining':[1] if w.get('bad_relink') else []}));return
    if stage=='batch':
        steps=[json.loads(line) for line in stdin.splitlines()]
        assert [s['id'] for s in steps]==['sequence.linkedSelection','clip.replaceFromBin','sequence.deleteTrack','sequence.linkedSelection']
        assert steps[0]['params']=={'on':False} and steps[3]['params']=={'on':True}
        assert steps[1]['params']['keepSourceIn'] is True and steps[1]['params']['clips']==[21,22]
        for c in raw['_inspect']['audio'][2]['items']:c['item']=9
        for c in seq['audio_tracks'][2]['items']:c['item']=9;c['source_channels']=[0,1]
        raw['_inspect']['audio'].pop();seq['audio_tracks'].pop()
        if w.get('raw_mutate')=='channels':seq['audio_tracks'][2]['items'][0]['source_channels']=[0]
        if w.get('raw_mutate')=='micro':seq['audio_tracks'][0]['volume']=0
        if w.get('raw_mutate')=='relative':raw['project']['items']['9']['kind']['Media']['media']['File']['path']='/wrong'
        project.write_text(json.dumps(raw))
        replacement={'clips':[21,22]}
        if w.get('replacement')=='count':replacement['clips']=[]
        if w.get('replacement') in ['short','sourceInClamped']:replacement[w['replacement']]=[21]
        rows=[{'ok':True,'result':{}},{'ok':True,'result':replacement},{'ok':True,'result':{}},{'ok':True,'result':{}}]
        if w.get('batch')=='rows':rows.pop()
        if w.get('batch')=='not-ok':rows[0]['ok']=False
        print('\n'.join(json.dumps(row) for row in rows));return
    if stage=='missing':
        if w.get('project_race'):
            public=parent/'premontage.fcproj';v=json.loads(public.read_text());v['foreign_edit']='preserve';public.write_text(json.dumps(v))
        if w.get('wav_after'):
            public=parent/'recording_bureau.wav';public.unlink();public.write_bytes(b'new foreign WAV')
        print(json.dumps({'missing':[1] if w.get('missing') else []}));return
    raise AssertionError(stage)
