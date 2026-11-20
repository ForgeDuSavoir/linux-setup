"""Strict fake image/PhotoCraft processes. Never reads GUI or personal media."""
import json,os,sys,zipfile,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT.parent/'scripts/photocraft-thumbnail/photocraft-thumbnail-mask.zip'
def cli():
    w=json.loads(Path(os.environ['THUMB_WORLD']).read_text());args=sys.argv[1:];tool=Path(sys.argv[0]).name
    with open(os.environ['THUMB_LOG'],'a') as f:f.write(json.dumps([tool,args])+'\n')
    stage={'ffprobe':'probe','ffmpeg':'prepare' if '-y' in args else 'brightness','photocraft-cli':'create' if args[0]=='run' else 'info'}[tool]
    if w.get('fail')==stage:print('synthetic failure',file=sys.stderr);sys.exit(7)
    if tool=='ffprobe':
        name=Path(args[-1]).name
        print('bad JSON' if w.get('bad_probe') else json.dumps({'streams':w.get('streams',[dict(zip(['width','height'],w.get('size',[2304,1440])))])}))
    elif tool=='ffmpeg':
        image=Path(args[args.index('-i')+1])
        if '-y' in args:
            Path(args[-1]).write_text(json.dumps({'name':image.name,'score':w.get('scores',{}).get(image.name,30 if image.name.casefold().startswith('alpha') else 180)}))
        else:
            score=json.loads(image.read_text())['score'];sys.stdout.buffer.write(bytes([score])*w.get('luma_size',1024))
    elif args[0]=='run':
        params=[json.loads(args[i+1]) for i,a in enumerate(args) if a=='--params']
        assert len(params)==3 and params[1]['fit'] is False and params[1]['smartObject'] is False
        bottom,top=params[0]['name'],params[2]['name']
        doc={'format_version':1,'document':{'size':{'width':1920,'height':1080},'layers':[{'name':bottom,'mask':None},{'name':top,'mask':None}],'unknown':{'big':123456789012345678901234567890}}}
        variant=w.get('project')
        if variant=='size':doc['document']['size']['width']=1280
        if variant=='order':doc['document']['layers'].reverse()
        if variant=='mask':doc['document']['layers'][0]['mask']={'already':True}
        if variant=='format':doc['format_version']=2
        target=Path(args[args.index('--out')+1])
        if variant=='absent':return
        if variant=='empty':target.touch();return
        if variant=='corrupt':target.write_bytes(b'bad ZIP');return
        with zipfile.ZipFile(target,'w',compression=w.get('codec',0)) as z:
            # Keep matching tile before rewritten JSON: the legacy writer mutates
            # ZipInfo offsets; matching-data checks only work before that offset moves.
            if variant=='matching':
                with zipfile.ZipFile(ASSET) as ref:
                    tile=next(n for n in ref.namelist() if n.startswith('tiles/'))
                    z.writestr(tile,ref.read(tile))
            if variant!='no-manifest':z.writestr('manifest.json',json.dumps(doc))
            z.writestr('original-pixels.bin',b'actual-input-image-pixels')
            if variant=='duplicate':z.writestr('manifest.json',json.dumps(doc))
            if variant in ['collision','matching-late']:
                with zipfile.ZipFile(ASSET) as ref:
                    tile=next(n for n in ref.namelist() if n.startswith('tiles/'))
                    z.writestr(tile,b'conflicting' if variant=='collision' else ref.read(tile))
        if variant=='crc':
            with zipfile.ZipFile(target) as z:
                i=z.getinfo('original-pixels.bin');offset=i.header_offset+30+len(i.filename.encode())+len(i.extra)
            data=bytearray(target.read_bytes());data[offset]^=1;target.write_bytes(data)
    else:
        assert args[0]=='info' and args[-1]=='--compact'
        target=Path(args[1]);doc=json.loads(zipfile.ZipFile(target).read('manifest.json'))
        info={'width':1920,'height':1080,'layers':[{'name':l['name'],'bounds':[0,0,1920,1080],'hasMask':bool(l.get('mask'))} for l in reversed(doc['document']['layers'])]}
        variant=w.get('info')
        if variant=='size':info['width']=1280
        if variant=='count':info['layers'].pop()
        if variant=='name':info['layers'][0]['name']='wrong'
        if variant=='bounds':info['layers'][0]['bounds']=[0,1,1920,1080]
        if variant=='mask':info['layers'][1]['hasMask']=True
        dest=target.parent.parent/'miniature.pcraft'
        if w.get('race')=='file':dest.write_bytes(b'concurrent project')
        if w.get('race')=='symlink':dest.symlink_to('unrelated')
        if w.get('race')=='directory':dest.mkdir()
        print('bad JSON' if variant=='json' else json.dumps(info))

def write_mask(path,variant=None):
    with zipfile.ZipFile(ASSET) as z:entries={n:z.read(n) for n in z.namelist()}
    m=json.loads(entries['mask.json'])
    if variant=='corrupt':path.write_bytes(b'broken ZIP');return
    if variant=='format':m['format_version']=2
    if variant=='size':m['width']=1280
    if variant=='sample':m['mask']['surface']['format']['sample']='F32'
    if variant=='tile-count':m['mask']['surface']['tiles'].pop()
    if variant=='coords':m['mask']['surface']['tiles'][1]['tx']=99
    if variant=='duplicate-coords':m['mask']['surface']['tiles'][1]=m['mask']['surface']['tiles'][0]
    if variant=='hash':m['mask']['surface']['tiles'][0]['hash']='../unsafe'
    if variant=='missing-tile':entries.pop(next(n for n in entries if n.startswith('tiles/')))
    if variant=='json':entries['mask.json']=b'{'
    else:entries['mask.json']=json.dumps(m).encode()
    entries['reference-image-pixels-NEVER-COPY']=b'not part of the mask'
    with zipfile.ZipFile(path,'w') as z:
        for n,b in entries.items():z.writestr(n,b)
        if variant=='duplicate':z.writestr('mask.json',entries['mask.json'])

def semantic(path):
    if path.is_symlink():return ['symlink',os.readlink(path)]
    if path.is_dir():return ['directory']
    if not path.exists():return None
    if not zipfile.is_zipfile(path):return ['raw',path.read_bytes().hex()]
    with zipfile.ZipFile(path) as z:
        return {n:json.loads(z.read(n)) if n=='manifest.json' else z.read(n).hex() for n in z.namelist()}
