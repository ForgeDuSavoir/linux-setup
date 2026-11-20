#!/usr/bin/env python3
"""R6 executable/oracle parity with synthetic files and strict fake processes."""
import copy,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
from thumbnail_fixture import ROOT,ASSET,write_mask,semantic
BIN=ROOT/'target/release/photocraft-thumbnail'
ORACLE=ROOT.parent/'tools/runtime-migration/oracles/scripts/photocraft-thumbnail/photocraft-thumbnail.py'

def execute(root,world,rust=True):
    root.mkdir();folder=root/"images with 'quotes' ; $() é";folder.mkdir();bin=root/'bin';bin.mkdir()
    names=world.get('names',['Alpha dark.png','Zebra bright.PNG'])
    for name in names:(folder/name).write_bytes(b'original image '+name.encode())
    (folder/'unrelated').write_bytes(b'preserve');(folder/'nested').mkdir();(folder/'nested/ignored.png').touch()
    if world.get('input_link'):
        (folder/names[0]).unlink();(folder/names[0]).symlink_to('unrelated')
    if world.get('existing')=='file':(folder/'miniature.pcraft').write_bytes(b'existing')
    if world.get('existing')=='symlink':(folder/'miniature.pcraft').symlink_to('absent')
    if world.get('existing')=='directory':(folder/'miniature.pcraft').mkdir()
    if world.get('extra_temp'):(folder/'.photocraft-thumbnail-unrelated').mkdir()
    program=bin/('photocraft-thumbnail' if rust else 'oracle.py');shutil.copy2(BIN if rust else ORACLE,program);program.chmod(0o700)
    write_mask(bin/'photocraft-thumbnail-mask.zip',world.get('mask'))
    for name in ['ffmpeg','ffprobe','photocraft-cli']:
        tool=bin/name;tool.write_text('#!/usr/bin/python3\nimport sys\nsys.path.insert(0,'+repr(str(ROOT/'tests'))+')\nfrom thumbnail_fixture import cli\ncli()\n');tool.chmod(0o700)
    state=root/'world';state.write_text(json.dumps(world));log=root/'log'
    before={n:(folder/n).read_bytes() for n in names}
    env={'PATH':str(bin)+':/usr/bin:/bin','HOME':str(root),'THUMB_WORLD':str(state),'THUMB_LOG':str(log),'PYTHONDONTWRITEBYTECODE':'1'}
    directory='~/'+folder.name if world.get('tilde') else str(folder)
    args=world.get('args',[]);directory=str(root/'missing') if world.get('missing') else directory
    r=subprocess.run([str(program),directory,*args],env=env,capture_output=True,text=True,timeout=15)
    for n,b in before.items():assert (folder/n).read_bytes()==b
    assert (folder/'unrelated').read_bytes()==b'preserve'
    leftovers=list(folder.glob('.photocraft-thumbnail-*'))
    assert len(leftovers)==(1 if world.get('extra_temp') else 0),leftovers
    def normalized(value):
        if isinstance(value,str):
            # JSON formatting and volatile private directory names are not the ABI.
            if value.startswith('{'):
                try:return normalized(json.loads(value))
                except ValueError:pass
            return re.sub(r'\.photocraft-thumbnail-[^/]+','.photocraft-thumbnail-TMP',value.replace(str(root),'/ROOT'))
        if isinstance(value,list):return [normalized(x) for x in value]
        if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
        return value
    calls=normalized([json.loads(line) for line in log.read_text().splitlines()] if log.exists() else [])
    return r,calls,semantic(folder/'miniature.pcraft')

def cases():
    out=[]
    def add(name,world=None,ok=True):out.append((name,world or {},ok))
    add('normal');add('explicit',{'args':['--top','Zebra bright.PNG']});add('tilde',{'tilde':True})
    add('literal filename',{'names':["Alpha 'dark' ; $().webp",'Zebra é.tiff']})
    add('casefold',{'names':['ß.png','SS.png'],'scores':{'ß.png':30,'SS.png':180}})
    add('explicit ambiguous',{'scores':{'Alpha dark.png':50,'Zebra bright.PNG':50},'args':['--top=Alpha dark.png']})
    add('ambiguous',{'scores':{'Alpha dark.png':50,'Zebra bright.PNG':50}},False)
    add('gap boundary',{'scores':{'Alpha dark.png':45,'Zebra bright.PNG':60}})
    add('ratio refusal',{'scores':{'Alpha dark.png':46,'Zebra bright.PNG':61}},False)
    add('gap refusal',{'scores':{'Alpha dark.png':40,'Zebra bright.PNG':54}},False)
    add('bad top',{'args':['--top','not present.png']},False)
    add('empty top auto',{'args':['--top=']})
    add('missing arg',{'args':['--top']},False);add('bad option',{'args':['--unknown']},False)
    add('preserve unrelated temp',{'extra_temp':True})
    for count in [0,1,3]:add('image count '+str(count),{'names':[f'{i}.png' for i in range(count)]},False)
    for kind in ['file','symlink','directory']:add('exists '+kind,{'existing':kind},False)
    add('missing',{'missing':True},False);add('input link',{'input_link':True},False)
    for size in [[1920,1200],[2880,1800],[1936,1210],[1920,1080],[1600,1000]]:
        add('size '+str(size),{'size':size},size in [[1920,1200],[2880,1800]])
    add('no stream',{'streams':[]},False);add('bad probe JSON',{'bad_probe':True},False)
    for stage in ['probe','prepare','brightness','create','info']:add('failure '+stage,{'fail':stage},False)
    for length in [0,1023,1025]:add('luma length '+str(length),{'luma_size':length},False)
    for codec in [0,8,12,14,93]:add('zip codec '+str(codec),{'codec':codec})
    for kind in ['size','order','mask','format','absent','empty','corrupt','no-manifest','collision','crc']:
        add('project '+kind,{'project':kind},False)
    add('matching tile',{'project':'matching'})
    for kind in ['corrupt','format','size','sample','tile-count','coords','duplicate-coords','hash','missing-tile','json']:
        add('mask '+kind,{'mask':kind},False)
    for kind in ['size','count','name','bounds','mask','json']:add('info '+kind,{'info':kind},False)
    for kind in ['file','symlink','directory']:add('publication race '+kind,{'race':kind},False)
    return out

def main():
    with tempfile.TemporaryDirectory(prefix='r6-parity-') as d:
        root=Path(d)
        for i,(name,world,ok) in enumerate(cases()):
            old,old_calls,old_doc=execute(root/f'old-{i}',world,False)
            new,new_calls,new_doc=execute(root/f'new-{i}',world)
            assert (old.returncode==0)==ok,(name,old.stderr)
            assert (new.returncode==0)==ok,(name,new.stderr)
            assert old.returncode==new.returncode,(name,old.returncode,new.returncode)
            assert old_calls==new_calls,(name,old_calls,new_calls)
            assert old_doc==new_doc,(name,old_doc,new_doc)
            if ok:assert 'reference-image-pixels-NEVER-COPY' not in new_doc
        # Deliberate fail-closed change: duplicate ZIP names no longer accepted.
        for i,world in enumerate([{'mask':'duplicate'},{'project':'duplicate'}]):
            new,_,doc=execute(root/f'strict-{i}',world)
            assert new.returncode==1 and doc is None
        # R6-ZIP-001: legacy ZipInfo mutation moves source offsets after a rewritten
        # manifest; new archive reads are independent. Track, do not hide this delta.
        old,_,_=execute(root/'offset-old',{'project':'matching-late'},False)
        new,_,doc=execute(root/'offset-new',{'project':'matching-late'})
        assert old.returncode==1 and new.returncode==0 and isinstance(doc,dict)
        print(f'R6: {len(cases())} CLI differential cases, five ZIP codecs, semantic mask/tile equality and two duplicate-ZIP refusals passed.')
if __name__=='__main__':main()
