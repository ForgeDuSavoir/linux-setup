#!/usr/bin/env python3
"""R7 real FFmpeg, auto-editor XML and headless FilmCraft on generated media only."""
import hashlib,json,os,shutil,subprocess,tempfile,wave
from pathlib import Path
from filmcraft_fixture import ROOT,BIN,ORACLE

def checked(command,**kwargs):
    r=subprocess.run([str(a) for a in command],capture_output=True,text=True,timeout=60,**kwargs)
    assert r.returncode==0,(command,r.stdout,r.stderr)
    return r.stdout
def main():
    auto=shutil.which('auto-editor');assert auto,'auto-editor required only for this synthetic integration test'
    with tempfile.TemporaryDirectory(prefix='r7-real-') as d:
        root=Path(d);seed=root/'seed';seed.mkdir();home=root/'home';home.mkdir()
        runtime=root/'run';runtime.mkdir(mode=0o700)
        env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'config'),'XDG_DATA_HOME':str(home/'data'),'XDG_CACHE_HOME':str(home/'cache'),'XDG_STATE_HOME':str(home/'state'),'XDG_RUNTIME_DIR':str(runtime)}
        source=seed/'recording.mkv';project=seed/'premontage.fcproj';xml=seed/'cuts.xml'
        # Two distinguishable stereo streams. Desktop begins at +100 ms PTS.
        checked(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=blue:s=160x90:r=30000/1001','-f','lavfi','-i','sine=frequency=300:sample_rate=48000','-itsoffset','0.1','-f','lavfi','-i','sine=frequency=900:sample_rate=48000','-map','0:v','-map','1:a','-map','2:a','-c:v','ffv1','-c:a','pcm_s16le','-ac','2','-t','2',source],env=env)
        checked([auto,source,'--edit','none','--cut-out','0.5sec,0.9sec','--export','premiere','-o',xml,'--no-open'],env=env)
        checked(['filmcraft-cli','--save-as',project,'exec','file.import',json.dumps({'paths':[str(xml)]})],env=env,cwd=seed)
        tree=json.loads(checked(['filmcraft-cli','--project',project,'inspect','project'],env=env,cwd=seed))
        media=[i['item'] for i in tree['root']['children'] if i['type']=='Movie'];assert len(media)==1,tree
        checked(['filmcraft-cli','--project',project,'--save','exec','media.relink',json.dumps({'item':media[0],'path':source.name,'relinkOthers':False})],env=env,cwd=seed)
        initial=json.loads(checked(['filmcraft-cli','--project',project,'inspect','sequence'],env=env,cwd=seed))
        assert len(initial['audio'])==4 and len(initial['audio'][2]['items'])>=2,initial
        results=[];waves=[];seed_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        for kind in ['python','rust']:
            folder=root/(kind+" 'quotes' é");folder.mkdir()
            for p in [source,project]:shutil.copy2(p,folder/p.name)
            before=(folder/project.name).read_bytes()
            command=[BIN] if kind=='rust' else ['/usr/bin/python3',ORACLE]
            checked([*command,folder/source.name,folder/project.name],env=env,cwd=folder)
            assert hashlib.sha256((folder/source.name).read_bytes()).hexdigest()==seed_hash
            raw=json.loads((folder/project.name).read_text())
            seq=next(v['kind']['Sequence'] for v in raw['project']['items'].values() if 'Sequence' in v['kind'])
            assert all(c.get('source_channels') in [None,[0,1]] for c in seq['audio_tracks'][2]['items'])
            after=json.loads(checked(['filmcraft-cli','--project',folder/project.name,'inspect','sequence'],env=env,cwd=folder))
            assert len(after['audio'])==3 and after['durationFrames']==initial['durationFrames']
            assert after['video']==initial['video']
            wav=folder/'recording_bureau.wav';waves.append(wav.read_bytes());results.append(after)
            with wave.open(str(wav),'rb') as f:
                assert f.getnchannels()==2 and f.getframerate()==48000
                # PTS materialization adds leading silence; not channel 1 of microphone.
                assert not any(f.readframes(4000))
                assert any(f.readframes(2000))
            if kind=='rust':
                backups=list(folder.glob('.filmcraft-original-*.fcproj'));assert len(backups)==1 and backups[0].read_bytes()==before
        assert results[0]==results[1],'timeline semantics differ'
        assert waves[0]==waves[1],'WAV samples/timing differ'
    print('R7 real private pipeline: rational FPS, two cuts, stereo stream 2 +100 ms PTS, padding, exact Python/Rust WAV/timeline semantics and retained original; no GUI or user recording.')
if __name__=='__main__':main()
