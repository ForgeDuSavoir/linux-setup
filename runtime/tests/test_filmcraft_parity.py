#!/usr/bin/env python3
"""R7 core pipeline parity; explicit publication hardening is checked separately."""
import copy,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
from filmcraft_fixture import ROOT,BIN,ORACLE,fixture

def execute(root,world,rust=True):
    root.mkdir();source=root/'recording.mkv';source.write_bytes(b'synthetic recording')
    project=root/'premontage.fcproj';raw=fixture(fps=world.get('fps',(30,1)),ticks=world.get('ticks',1000))
    change=world.get('invalid')
    if change=='tracks':raw['_inspect']['audio'].pop()
    if change=='video':raw['_inspect']['video']=[]
    if change=='empty':
        for t in raw['_inspect']['audio']:t['items']=[]
    if change=='alignment':raw['_inspect']['audio'][0]['items'][0]['start']=5
    if change=='counts':raw['_inspect']['audio'][0]['items'].pop()
    if change=='media':raw['project']['items']['1']['kind']['Media']['media']['File']['path']='wrong'
    if change=='name':raw['project']['items']['2']['kind']['Sequence']['audio_tracks'][0]['name']='User renamed'
    if change=='mixed-media':
        for t in raw['_inspect']['audio']:t['items'][1]['item']=8
    if change=='channel':raw['project']['items']['2']['kind']['Sequence']['audio_tracks'][0]['items'][0]['source_channels']=[1]
    project.write_text(json.dumps(raw));before=project.read_bytes()
    wav=root/'recording_bureau.wav'
    if world.get('existing')=='file':wav.write_bytes(b'previous WAV')
    if world.get('existing')=='symlink':wav.symlink_to('foreign')
    bin=root/'bin';bin.mkdir()
    for name in ['ffmpeg','ffprobe','filmcraft-cli']:
        p=bin/name;p.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom filmcraft_fixture import cli\ncli()\n');p.chmod(0o700)
    (root/'world').write_text(json.dumps(world))
    env={'HOME':str(root),'PATH':str(bin)+':/usr/bin:/bin','FILM_WORLD':str(root/'world'),'PYTHONDONTWRITEBYTECODE':'1'}
    r=subprocess.run([str(BIN),str(source),str(project)] if rust else ['/usr/bin/python3',str(ORACLE),str(source),str(project)],env=env,cwd=root,capture_output=True,text=True,timeout=10)
    assert source.read_bytes()==b'synthetic recording'
    after=project.read_bytes()
    backups=list(root.glob('.filmcraft-original-*.fcproj'))
    if r.returncode==0 and rust:assert len(backups)==1 and backups[0].read_bytes()==before
    elif r.returncode!=0 and not world.get('project_race'):assert after==before,(world,r.stderr)
    # Ordinary handled failures remove only owned temporaries. Success retains original.
    assert not list(root.glob('.filmcraft-bureau-*')) and not list(root.glob('.filmcraft-pad-*'))
    assert not list(root.glob('.filmcraft-patch-*'))
    if r.returncode!=0:assert not backups
    def normalize(v):
        if isinstance(v,str):
            if v.startswith('{') or v.startswith('['):
                try:return normalize(json.loads(v))
                except ValueError:pass
            if '\n' in v:
                try:return [normalize(json.loads(line)) for line in v.splitlines() if line.strip()]
                except ValueError:pass
            v=v.replace(str(root),'/ROOT')
            return re.sub(r'\.filmcraft-(?:bureau|pad|patch|original)-[^/]+\.(wav|fcproj)',lambda m:'.TEMP.'+m.group(1),v)
        if isinstance(v,list):return [normalize(x) for x in v]
        if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
        return v
    calls=normalize([json.loads(line) for line in (root/'calls').read_text().splitlines()]) if (root/'calls').exists() else []
    return r,calls,json.loads(after),wav, before

def cases():
    out=[('normal',{},True),('fps rational',{'fps':[30000,1001]},True),('large exact ticks',{'ticks':2**90},True),
         ('padding',{'frames':67200},True),('shortage boundary',{'frames':62400},True),('too short',{'frames':62399},False),
         ('bad padding',{'frames':67200,'bad_pad':True},False),('existing WAV',{'existing':'file'},False)]
    for mode in ['tracks','video','empty','alignment','counts','media','name','channel']:out.append(('invalid '+mode,{'invalid':mode},False))
    for streams in [[],[{'channels':2}],[{'channels':2},{'channels':1}]]:out.append(('streams '+str(streams),{'streams':streams},False))
    for stage in ['probe','before','extract','pad','import','tree','relink','batch','after','missing']:
        w={'fail':stage}
        if stage=='pad':w['frames']=67200
        out.append(('tool failure '+stage,w,False))
    for stage in ['probe','before','tree','relink','batch','after','missing']:out.append(('JSON '+stage,{'bad_json':stage},False))
    for value in ['tiny','header']:out.append(('WAV '+value,{'bad_wav':value},False))
    for mode in ['none','duplicate']:out.append(('tree '+mode,{'tree':mode},False))
    out.append(('relink remaining',{'bad_relink':True},False))
    for mode in ['count','short','sourceInClamped']:out.append(('replacement '+mode,{'replacement':mode},False))
    for mode in ['rows','not-ok']:out.append(('batch '+mode,{'batch':mode},False))
    for mode in ['durationFrames','video','start','duration','sourceIn','link','clip','source','count']:out.append(('mutate '+mode,{'mutate':mode},False))
    out.extend([('missing media',{'missing':True},False),('wrong relative path',{'raw_mutate':'relative'},False)])
    return out

def main():
    with tempfile.TemporaryDirectory(prefix='r7-parity-') as d:
        root=Path(d)
        for i,(name,w,ok) in enumerate(cases()):
            old,old_calls,old_doc,old_wav,_=execute(root/f'old-{i}',w,False)
            new,new_calls,new_doc,new_wav,_=execute(root/f'new-{i}',w)
            assert (old.returncode==0)==ok,(name,old.stderr)
            assert new.returncode==old.returncode,(name,new.stderr,old.stderr)
            assert new_calls==old_calls,(name,new_calls,old_calls)
            assert new_doc==old_doc,(name,new_doc,old_doc)
            if ok:assert old_wav.read_bytes()==new_wav.read_bytes(),name
            elif new_wav.exists() and not w.get('existing'):assert not old_wav.exists(),'intentional new retain-after-publish only'
        # Stricter postconditions not present in old helper.
        for i,w in enumerate([{'mutate':'sourceOut'},{'raw_mutate':'channels'},{'raw_mutate':'micro'},{'existing':'symlink'},{'invalid':'mixed-media'}]):
            new,_,_,wav,_=execute(root/f'strict-{i}',w)
            assert new.returncode==1
        for i,w in enumerate([{'wav_race':'file'},{'wav_race':'symlink'},{'project_race':True},{'wav_after':True}]):
            new,_,doc,wav,_=execute(root/f'race-{i}',w)
            assert new.returncode==1
            if w.get('wav_race')=='file':assert wav.read_bytes()==b'foreign WAV'
            if w.get('wav_race')=='symlink':assert wav.is_symlink()
            if w.get('wav_after'):assert wav.read_bytes()==b'new foreign WAV'
            if w.get('project_race'):assert doc['foreign_edit']=='preserve'
    print(f'R7: {len(cases())} differential CLI scenarios; exact WAV/clip semantics, five stronger refusals and four publication races passed.')
if __name__=='__main__':main()
