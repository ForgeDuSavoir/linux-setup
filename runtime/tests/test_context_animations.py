#!/usr/bin/env python3
"""Actual session CLI generates Lua; execute it synthetically, never move real windows."""
import importlib.util,json,subprocess,tempfile
from pathlib import Path
p=Path(__file__).with_name('test_desktop_parity.py');s=importlib.util.spec_from_file_location('fixture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for action in [['start','--neutral'],['switch','A'],['stop','B'],['deactivate']]:
 data=m.cases()['start_neutral'];data['actions']=[action]
 with tempfile.TemporaryDirectory(prefix='session-animation-') as d:
  e=m.Environment(d,data);result=e.rust();assert result['answers'][0]['ok'],result
  codes=json.loads(e.file.read_text())['codes'];animated=[code for kind,code in codes if 'hl.animation' in code];assert len(animated)==1,(action,codes)
  code=animated[0]
  for fail,collision in [(False,False),(True,False),(False,True)]:
   # Collision only applies to newly created target; existing-target cases ignore it.
   fresh='workspace target already exists' in code
   setup='''local style='slidevert';local captured=nil;local n=0
local base={leaf='workspaces',enabled=true,speed=2.5,bezier='custom',style='slidevert'}
_G.__workflow_workspace_animation=base
hl={animation=function(spec) assert(spec.speed==2.5 and spec.bezier=='custom');style=spec.style;n=n+1 end,
get_workspace=function() return COLLISION and {} or nil end,
dsp={focus=function(opts) return opts end},dispatch=function() captured=style;if FAIL then error('injected') end end}
local ok=pcall(function()
'''.replace('COLLISION','true' if collision else 'false').replace('FAIL','true' if fail else 'false')
   expected_ok=not fail and not (fresh and collision)
   suffix='\nend)\nassert(style=="slidevert" and n==2)\nassert(ok=='+str(expected_ok).lower()+')\n'
   if not(fresh and collision):suffix+='assert(captured=="slidefade")\n'
   r=subprocess.run(['lua','-'],input=setup+code+suffix,text=True,capture_output=True);assert r.returncode==0,(action,r.stderr)
source=(m.ROOT.parent/'configs/hypr/files/visuals.lua').read_text()
assert 'style = "slidevert"' in source and 'style = "slidefadevert"' in source
print('Session animations: actual start/switch/stop-survivor/deactivate Lua, style at dispatch, immediate restoration on success/error/collision, baseline speed/curve preserved; no real GUI.')
