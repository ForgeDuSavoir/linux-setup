#!/usr/bin/env python3
"""Execute versioned visual config with recorder-only Lua API; no real compositor."""
from pathlib import Path
import subprocess
source=Path(__file__).resolve().parents[2]/'configs/hypr/files/visuals.lua'
code='''local animations,curves={},{}
hl={env=function() end,config=function() end,curve=function(name,spec) curves[name]=spec end,animation=function(spec) animations[spec.leaf]=spec end}
dofile(arg[1])
local opening,closing=animations.specialWorkspaceIn,animations.specialWorkspaceOut
assert(opening.style=='slidefadevert top' and closing.style=='slidefadevert bottom')
assert(opening.speed==3 and closing.speed==3 and opening.bezier=='scratchpadEase' and closing.bezier=='scratchpadEase')
local points=curves.scratchpadEase.points
assert(points[1][1]==0.16 and points[1][2]==1 and points[2][1]==0.3 and points[2][2]==1)
local last=0
for i=0,100 do local t=i/100; local y=3*(1-t)^2*t+3*(1-t)*t^2+t^3;assert(y>=last-1e-12 and y<=1+1e-12);last=y end
assert(animations.workspaces.speed==5 and animations.workspaces.bezier=='wind' and animations.workspaces.style=='slidevert')
assert(_G.__workflow_workspace_animation==animations.workspaces)
-- Exact installed compositor formula: top => left=false, bottom => left=true.
local function offset(style,incoming) local left=style:find(' bottom',1,true)~=nil; if incoming then return left and 1 or -1 else return left and -1 or 1 end end
assert(offset(opening.style,true)<0 and offset(closing.style,false)<0)
'''
subprocess.run(['lua','-',str(source)],input=code,text=True,check=True)
print('Scratchpad source: top entry/upward exit, 300ms both, monotonic no-overshoot curve, unchanged workspace/session baseline; no GUI.')
