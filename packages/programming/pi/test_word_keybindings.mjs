// Actual installed Pi TUI/editor, synthetic input only: no terminal/model/conversation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base='file:///usr/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-tui/dist/';
const {KeybindingsManager,TUI_KEYBINDINGS,setKeybindings}=await import(base+'keybindings.js');
const {Editor}=await import(base+'components/editor.js');
const config=JSON.parse(fs.readFileSync(new URL('./keybindings.json',import.meta.url),'utf8'));
const manager=new KeybindingsManager(TUI_KEYBINDINGS,config);setKeybindings(manager);
assert(manager.matches('\x1b[127;5u','tui.editor.deleteWordBackward'));
assert(manager.matches('\x1b[3;5~','tui.editor.deleteWordForward'));
for(const key of ['ctrl+w','alt+backspace','ctrl+backspace'])assert(manager.getKeys('tui.editor.deleteWordBackward').includes(key));
for(const key of ['alt+d','alt+delete','ctrl+delete'])assert(manager.getKeys('tui.editor.deleteWordForward').includes(key));
const editor=new Editor({requestRender(){},terminal:{rows:30}}, {borderColor:s=>s});
editor.setText('hello world');editor.handleInput('\x1b[127;5u');assert.equal(editor.getText(),'hello ');
editor.setText('hello world');editor.handleInput('\x01');editor.handleInput('\x1b[3;5~');assert.equal(editor.getText(),' world');
for(const [key,expected] of [['\x1b[127;5u','lo world'],['\x1b[3;5~','hel world']]){
 editor.setText('hello world');editor.handleInput('\x01');for(let i=0;i<3;i++)editor.handleInput('\x1b[C');editor.handleInput(key);assert.equal(editor.getText(),expected);
}
console.log('Actual Pi editor: Ctrl+Backspace/Delete sequences, word boundaries in both directions, within-word deletion and retained aliases passed; synthetic input only.');
