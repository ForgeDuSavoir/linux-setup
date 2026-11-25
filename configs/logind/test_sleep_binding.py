#!/usr/bin/env python3
"""Execute actual Lua sleep-binding gate without bus, logind, keypress or privilege."""
import subprocess
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'hypr/files/keybinds.lua';s=p.read_text();code=s[s.index('local function sleepKeyIgnored'):s.index('hl.bind(mainMod .. " + H"')]
for first,second,expected in [('ignore','ignore',1),('suspend','ignore',0),('ignore','hibernate',0),('bad','ignore',0)]:
 setup='''local count=0
io.popen=function(command) local mode=command:find('LongPress') and SECOND or FIRST;return {read=function() return 's "'..mode..'"\\n' end,close=function() end} end
hl={bind=function(key) assert(key=='XF86Sleep');count=count+1 end,dsp={exec_cmd=function(x) return x end}}
'''.replace('FIRST',repr(first)).replace('SECOND',repr(second))
 r=subprocess.run(['lua','-'],input=setup+code+'\nassert(count=='+str(expected)+')',text=True,capture_output=True);assert r.returncode==0,r.stderr
print('Actual Lua sleep gate: only effective ignore for short AND long press enables binding; no system change/key event.')
