#!/usr/bin/env python3
"""R6 synthetic-only startup, ZIP orchestration and separately timed real tools."""
import importlib.util,json,os,shutil,statistics,struct,subprocess,tempfile,time,zipfile,zlib
from pathlib import Path
from thumbnail_fixture import ROOT,ASSET,semantic
from test_thumbnail_parity import ORACLE,BIN

def stats(samples):
    return {'samples':len(samples),'median_ms':round(statistics.median(samples),3),'p95_ms':round(sorted(samples)[max(0,int(len(samples)*.95+.999)-1)],3)}
def timed(command,**kwargs):
    t=time.perf_counter();subprocess.run(command,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**kwargs);return (time.perf_counter()-t)*1000
with tempfile.TemporaryDirectory(prefix='r6-bench-') as d:
    root=Path(d);programs={}
    for kind,source in [('python',ORACLE),('rust',BIN)]:
        folder=root/kind;folder.mkdir();programs[kind]=folder/'thumbnail';shutil.copy2(source,programs[kind]);programs[kind].chmod(0o700);shutil.copy2(ASSET,folder/ASSET.name)
    startup={k:stats([timed([str(p),'--help']) for _ in range(31)]) for k,p in programs.items()}
    source=root/'source.pcraft';output=root/'masked.pcraft'
    doc={'format_version':1,'document':{'size':{'width':1920,'height':1080},'layers':[{'name':'bottom'},{'name':'top'}]}}
    with zipfile.ZipFile(source,'w') as z:z.writestr('manifest.json',json.dumps(doc));z.writestr('pixels',b'synthetic pixels')
    spec=importlib.util.spec_from_file_location('thumbnail_oracle',ORACLE);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    samples=[]
    for _ in range(31):
        t=time.perf_counter();oracle.apply_reference_mask(source,output,'top','bottom');output.unlink();samples.append((time.perf_counter()-t)*1000)
    zip_times={'python':stats(samples),'rust':stats(json.loads(subprocess.check_output([str(ROOT/'target/release/examples/thumbnail-mask-bench'),str(ASSET),str(source),str(output)],text=True)))}
    images=root/'images';images.mkdir()
    def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    for name,rgb in [('Alpha.png',(210,35,25)),('Zeta.png',(20,45,210))]:
        w,h=2304,1440
        (images/name).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(rgb)*w)*h))+chunk(b'IEND',b''))
    wrappers=root/'tools';wrappers.mkdir();log=root/'times'
    for name in ['ffmpeg','ffprobe','photocraft-cli']:
        actual=shutil.which(name);assert actual
        script=wrappers/name
        script.write_text('#!/usr/bin/python3\nimport subprocess,sys,time\nt=time.perf_counter()\nr=subprocess.run(['+repr(actual)+',*sys.argv[1:]])\nwith open('+repr(str(log))+',"a") as f:f.write('+repr(name+' ')+"+str(time.perf_counter()-t)+'\\n')\nsys.exit(r.returncode)\n");script.chmod(0o700)
    real={};reference=None
    for kind,program in programs.items():
        totals=[];external={name:[] for name in ['ffmpeg','ffprobe','photocraft-cli']}
        for _ in range(3):
            log.unlink(missing_ok=True)
            totals.append(timed([str(program),str(images)],env={**os.environ,'PATH':str(wrappers)+':'+os.environ['PATH']}))
            rows=[line.split() for line in log.read_text().splitlines()]
            for name in external:external[name].append(sum(float(t)*1000 for n,t in rows if n==name))
            project=images/'miniature.pcraft';actual=semantic(project)
            if reference is None:reference=actual
            else:assert actual==reference,'real document semantics changed'
            project.unlink()
        real[kind]={'end_to_end':stats(totals),'external_by_tool':{n:stats(v) for n,v in external.items()}}
    result={'fixture':'two generated solid-color 2304x1440 RGB PNGs; warm local runs; no personal media','startup_help_no_tools':startup,'zip_mask_only_in_process_with_private_io':zip_times,'real_instrumented_pipeline':real,'limitations':'ZIP benchmark excludes process startup; real external times are sums per run via perf_counter in Python timing wrappers, excluding wrapper startup. Instrumented end-to-end includes wrapper startup (~8 extra Python processes); it is not uninstrumented user latency. Three pipeline samples are illustrative only. Do not subtract medians, promise FFmpeg acceleration or infer live user latency.'}
    destination=ROOT/'tests/thumbnail-benchmark-results.json';destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
