#!/usr/bin/env python3
"""Private installer + actual Gio dispatch to synthetic ELF, never real Obsidian."""
import importlib.util,json,os,subprocess,tempfile,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('install_obsidian',ROOT/'install_obsidian.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
C=r"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char**argv){
 if(argc==2&&!strcmp(argv[1],"--version")){puts("session-obsidian test (Rust; exact registered vault)");return 0;}
 const char*p=getenv("OBSIDIAN_TEST_CAPTURE");if(!p)return 42;
 FILE*f=fopen(p,"wb");if(!f)return 43;
 for(int i=1;i<argc;i++)fwrite(argv[i],1,strlen(argv[i])+1,f);
 fclose(f);return 0;
}"""
DESKTOP=b'[Desktop Entry]\nName=Obsidian\nName[fr]=Obsidian personnel\nExec=/usr/bin/obsidian %U\nTryExec=/usr/bin/obsidian\nTerminal=false\nType=Application\nIcon=custom-icon\nStartupWMClass=md.obsidian.Obsidian\nMimeType=x-scheme-handler/obsidian;\nCategories=Office;\n'
with tempfile.TemporaryDirectory(prefix='obsidian-install-') as d:
    root=Path(d);h=root/'Home "quotes" \\ $` % é';h.mkdir()
    source=root/'source';source.write_text(C);elf=root/'fake';subprocess.run(['cc','-x','c',str(source),'-o',str(elf)],check=True)
    factory=root/'factory.desktop';factory.write_bytes(DESKTOP)
    env={**os.environ,'HOME':str(h),'XDG_DATA_HOME':str(h/'data'),'XDG_STATE_HOME':str(h/'state'),'XDG_CONFIG_HOME':str(h/'config')}
    with patch.dict(os.environ,env,clear=True),patch.object(m,'GRAPHICAL',elf),patch.object(m,'SYSTEM_DESKTOP',factory),patch.object(m.builder,'build_runtime',return_value=elf):
        targets,base=m.paths();base.mkdir(parents=True);binary,entry=targets
        m.apply(targets,base);backup=next(p for p in base.iterdir() if p.is_dir())
        assert binary.read_bytes()==elf.read_bytes() and binary.stat().st_mode&0o777==0o755
        value=entry.read_bytes()
        for text in [b'Icon=custom-icon',b'Name[fr]=Obsidian personnel',b'MimeType=x-scheme-handler/obsidian;',b'StartupWMClass=md.obsidian.Obsidian']:assert text in value
        mtimes=[p.stat().st_mtime_ns for p in targets];m.apply(targets,base)
        assert mtimes==[p.stat().st_mtime_ns for p in targets] and len(list(base.iterdir()))==1
        # Gio parses the installed desktop Exec itself: special HOME characters, %% and %U.
        for i,args in enumerate([[],['obsidian://open?vault=other&file=a%20b'],['obsidian://open?vault=one','obsidian://open?vault=two']]):
            capture=root/f'capture-{i}';e={**env,'OBSIDIAN_TEST_CAPTURE':str(capture),'DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(root/'no-bus')}
            r=subprocess.run(['gio','launch',str(entry),*args],env=e,capture_output=True,text=True)
            assert r.returncode==0,(r.stderr,entry.read_text())
            for _ in range(100):
                if capture.exists():break
                time.sleep(.01)
            assert capture.exists(),entry.read_text()
            assert capture.read_bytes().split(b'\0')[:-1]==[v.encode() for v in args],(args,capture.read_bytes())
        entry.write_bytes(value+b'# personal edit\n')
        try:m.restore(backup,targets);raise AssertionError('foreign edit accepted')
        except RuntimeError:pass
        entry.write_bytes(value);m.restore(backup,targets);assert all(not p.exists() for p in targets)
        # Existing personal metadata preserved and restored, command overrides refused.
        entry.parent.mkdir(parents=True,exist_ok=True);entry.write_bytes(DESKTOP+b'# personal metadata\n');entry.chmod(0o640)
        m.apply(targets,base);b2=next(p for p in base.iterdir() if p.is_dir() and p!=backup)
        assert b'# personal metadata' in entry.read_bytes()
        m.restore(b2,targets);assert entry.read_bytes()==DESKTOP+b'# personal metadata\n' and entry.stat().st_mode&0o777==0o640
        entry.write_bytes(DESKTOP.replace(b'/usr/bin/obsidian %U',b'/personal/obsidian --special %U'))
        try:m.apply(targets,base);raise AssertionError('personal Exec replaced')
        except RuntimeError:pass
        entry.write_bytes(DESKTOP)
        # Partial publication has an explicit journal/return, never automatic rollback.
        real=m.atomic
        def fail(p,data,mode):
            if p==entry:raise OSError('injected desktop publication failure')
            return real(p,data,mode)
        with patch.object(m,'atomic',side_effect=fail):
            try:m.apply(targets,base);raise AssertionError('fault ignored')
            except OSError:pass
        b3=next(p for p in base.iterdir() if p.is_dir() and p not in [backup,b2])
        assert binary.exists() and json.loads((b3/'manifest.json').read_text())['phase']=='publishing-1'
        m.restore(b3,targets);assert not binary.exists() and entry.read_bytes()==DESKTOP
        entry.unlink();entry.symlink_to(factory)
        try:m.apply(targets,base);raise AssertionError('symlink accepted')
        except RuntimeError:pass
print('Obsidian installer: native/private backup/idempotence, actual Gio %U and quoted HOME, metadata/MIME/identity preserved, personal edits/Exec/symlink refusal, partial publication and guarded restore passed; no GUI.')
