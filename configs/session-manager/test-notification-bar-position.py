#!/usr/bin/env python3
"""Actual anchor snippets in private offscreen Qt; no live shell or notifications."""
import os,re,subprocess,tempfile
from pathlib import Path
source=(Path(__file__).resolve().parents[1]/'quickshell/files/shell.qml').read_text()
def anchor(start):
 text=source[source.index(start):];return re.search(r'anchors\s*\{[^}]*\}',text)[0]
button=anchor('id: notificationButton\n');sessions=anchor('                    SessionStrip {');battery=anchor('id: battery\n');power=anchor('id: power\n');clock=anchor('id: clock\n')
assert 'relativeX: notificationButton.x\n' in source
qml='''import QtQuick
import QtTest
TestCase {
 name: "NotificationBarPosition"
 Item {
  id: bar; width:1280; height:32
  Rectangle { id:notificationButton;width:28;height:24; BUTTON }
  Rectangle { id:sessions;width:300;height:26; SESSIONS }
  Rectangle { id:battery;width:76;height:24; BATTERY }
  Rectangle { id:power;width:64;height:24; POWER }
  Rectangle { id:clock;width:34;height:20; CLOCK }
 }
 function test_positions() {
  compare(notificationButton.x,12)
  compare(sessions.x,notificationButton.x+notificationButton.width+8)
  compare(battery.x+battery.width,power.x-8)
  verify(battery.x>bar.width/2)
  compare(notificationButton.y,4)
 }
}
'''
for key,value in [('BUTTON',button),('SESSIONS',sessions),('BATTERY',battery),('POWER',power),('CLOCK',clock)]:qml=qml.replace(key,value)
with tempfile.TemporaryDirectory(prefix='notification-bar-layout-') as d:
 h=Path(d);(h/'tst_position.qml').write_text(qml);(h/'run').mkdir(mode=0o700)
 env={'HOME':d,'PATH':'/usr/bin:/bin','QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software',**{'XDG_'+k:str(h/v) for k,v in [('CONFIG_HOME','config'),('STATE_HOME','state'),('DATA_HOME','data'),('CACHE_HOME','cache'),('RUNTIME_DIR','run')]}}
 subprocess.run(['/usr/lib/qt6/bin/qmltestrunner','-input',d],env=env,check=True,timeout=15)
print('Actual QML anchor geometry: notification first at x12, sessions x48, battery/right group preserved, history left-aligned; private offscreen only.')
