#!/usr/bin/env python3
"""Record actual inputs.lua declarations; no physical input, compositor or apps."""
from pathlib import Path
import subprocess
p=Path(__file__).resolve().parents[2]/'configs/hypr/files/inputs.lua'
code='''local gestures={};local config=nil
hl={config=function(s) config=s end,gesture=function(s) gestures[#gestures+1]=s end}
dofile(arg[1])
assert(#gestures==0)
assert(config.input.touchpad.natural_scroll and config.input.touchpad.disable_while_typing and config.input.touchpad.clickfinger_behavior)
assert(config.input.touchpad.scroll_factor==0.5)
'''
subprocess.run(['lua','-',str(p)],input=code,text=True,check=True)
print('Actual input config: no compositor swipe/pinch shortcuts; scrolling/click settings retained. No real gesture.')
