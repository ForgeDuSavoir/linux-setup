#!/usr/bin/env python3
"""Recorder-only Lua evaluation of the actual visuals config; no real windows."""
from pathlib import Path
import subprocess
p=Path(__file__).resolve().parents[2]/'configs/hypr/files/visuals.lua'
code='''local animations,curves={},{}
hl={env=function() end,config=function() end,curve=function(n,s) curves[n]=s end,animation=function(s) animations[s.leaf]=s end}
dofile(arg[1])
local a=animations.windowsIn
assert(a.enabled and a.style=='popin' and a.speed==3 and a.bezier=='windowEase')
assert(curves.windowEase.points[1][1]==0.16 and curves.windowEase.points[1][2]==1)
assert(curves.windowEase.points[2][1]==0.3 and curves.windowEase.points[2][2]==1)
assert(animations.windowsOut.style=='popin' and animations.windowsOut.speed==3 and animations.windowsOut.bezier=='windowEase')
assert(animations.windowsMove.speed==5 and animations.windowsMove.bezier=='wind')
assert(animations.workspaces.style=='slidevert' and animations.workspaces.speed==5)
assert(animations.specialWorkspaceIn.style=='slidefadevert top' and animations.specialWorkspaceOut.style=='slidefadevert bottom')
assert(animations.fade.speed==10)
'''
subprocess.run(['lua','-',str(p)],input=code,text=True,check=True)
print('Window popin source: full centered expansion and reverse contraction, both speed 3/ease-out; movement/fade/workspaces/scratchpads preserved; no GUI.')
