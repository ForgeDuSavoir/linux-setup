#!/usr/bin/env python3
"""Actual stop script, fake recorder signals/Whisper/notifications. No live dictation."""
import shlex,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
CASES=[
 (' Bonjour','Bonjour'),('   Bonjour  le monde','Bonjour  le monde'),
 ('\n\n \tBonjour\n  suite indentée','Bonjour\n  suite indentée'),
 ('Déjà propre','Déjà propre'),('\t Écriture ; $() "texte"','Écriture ; $() "texte"'),
 ('\n ...\n Bonjour\n  autre ligne','Bonjour\n  autre ligne'),
 (' \t\n',''),('',''),(' Première ligne\n\n  dernière ligne','Première ligne\n\n  dernière ligne'),
]
with tempfile.TemporaryDirectory(prefix='dictation-output-') as d:
 h=Path(d);config=h/'config/text-tools';config.mkdir(parents=True);runtime=h/'run';runtime.mkdir();tools=h/'bin';tools.mkdir()
 model=h/'synthetic-model';model.write_text('placeholder, not a real model')
 (config/'config.sh').write_text('TEXT_TOOLS_RUNTIME_DIR='+shlex.quote(str(runtime))+'\nWHISPER_MODEL='+shlex.quote(str(model))+'\nWHISPER_LANGUAGE=fr\n')
 fake=tools/'whisper-cli';fake.write_text('#!/bin/bash\nprintf "%s" "$TEST_TRANSCRIPT"\nexit "${TEST_WHISPER_CODE:-0}"\n');fake.chmod(0o700)
 notify=tools/'notify-send';notify.write_text('#!/bin/sh\nexit 0\n');notify.chmod(0o700)
 driver=r'''
fixture_stopped=0
kill() {
 case "$1" in
 -0) [[ "$fixture_stopped" == 0 ]] ;;
 -INT) fixture_stopped=1 ;;
 *) return 99 ;;
 esac
}
tr() { printf 'pw-record synthetic fixture'; }
printf '%s\n' "$$" > "$TEST_RUNTIME/dictation.pid"
source "$TEST_SCRIPT"
'''
 env={'HOME':str(h),'PATH':str(tools)+':/usr/bin:/bin','XDG_CONFIG_HOME':str(h/'config'),'XDG_STATE_HOME':str(h/'state'),'XDG_CACHE_HOME':str(h/'cache'),'TEST_RUNTIME':str(runtime),'TEST_SCRIPT':str(HERE/'dictation-stop.sh')}
 for text,expected in CASES:
  (runtime/'dictation.wav').write_bytes(b'synthetic audio');(runtime/'dictation.log').write_text('synthetic recorder')
  r=subprocess.run(['bash','-c',driver],env={**env,'TEST_TRANSCRIPT':text},capture_output=True,text=True,timeout=5)
  assert r.returncode==0 and r.stdout==expected,(repr(text),r.stdout,r.stderr)
  assert (runtime/'dictation.state').read_text()=='idle\n' and not (runtime/'dictation.wav').exists()
 (runtime/'dictation.wav').write_bytes(b'synthetic audio')
 r=subprocess.run(['bash','-c',driver],env={**env,'TEST_TRANSCRIPT':' should not insert','TEST_WHISPER_CODE':'1'},capture_output=True,text=True,timeout=5)
 assert r.returncode!=0 and not r.stdout and (runtime/'dictation.wav').read_bytes()==b'synthetic audio'
 target=h/'.local/bin';target.mkdir(parents=True);other=target/'dictation-start';other.write_text('personal script')
 subprocess.run(['bash',str(HERE/'install_text_tools.sh'),'--dictation-stop-only'],env=env,check=True,capture_output=True)
 assert (target/'dictation-stop').read_bytes()==(HERE/'dictation-stop.sh').read_bytes()
 assert other.read_text()=='personal script'
print(f'Dictation: {len(CASES)} whitespace/format cases, Whisper failure retention and targeted install passed; no recorder/model/typing/personal notification.')
