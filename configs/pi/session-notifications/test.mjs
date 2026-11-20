import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, mkdir, writeFile, readFile, cp, chmod, rm, realpath } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import factory from './index.ts';
const here=dirname(fileURLToPath(import.meta.url));
const A='session:11111111-1111-1111-1111-111111111111';
const B='session:22222222-2222-2222-2222-222222222222';
function harness(execute) {
  const handlers=new Map(),calls=[];
  factory({on:(name,fn)=>handlers.set(name,fn),exec:async (file,args,options)=>{
    calls.push({file,args,options});return execute?execute(file,args,options):{stdout:A+'\n',stderr:'',code:0,killed:false};
  }});
  return {calls,handlers,emit:async(name,value={})=>handlers.get(name)?.({type:name,...value},{mode:'tui'})};
}
const sends=h=>h.calls.filter(c=>c.args[0]==='send');
const captures=h=>h.calls.filter(c=>c.args[0]==='capture');

test('factory/restored idle session never executes or notifies',async()=>{
  const h=harness();assert.equal(h.calls.length,0);assert(!h.handlers.has('agent_end'));
  await h.emit('agent_settled',{aborted:false});assert.equal(h.calls.length,0);
});
test('capture once across low-level retries, send once at settlement',async()=>{
  let context=A;const h=harness(()=>({stdout:context,code:0,killed:false}));
  await h.emit('agent_start');context=B;await h.emit('agent_end');await h.emit('agent_start');
  assert.equal(sends(h).length,0);assert.equal(captures(h).length,1);
  await h.emit('agent_before_settle',{outcome:'completed'});await h.emit('agent_settled',{aborted:false});await h.emit('agent_settled',{aborted:false});
  assert.equal(sends(h).length,1);assert.equal(sends(h)[0].args[2],A);
  assert.equal(captures(h)[0].options.timeout,2000);assert.equal(sends(h)[0].options.timeout,3000);
});
test('new independent activity captures again',async()=>{
  let context=A;const h=harness(()=>({stdout:context,code:0,killed:false}));
  await h.emit('agent_start');await h.emit('agent_settled',{aborted:false});context=B;
  await h.emit('agent_start');await h.emit('agent_settled',{aborted:false});
  assert.deepEqual(sends(h).map(c=>c.args[2]),[A,B]);
});
test('abort and shutdown/reload are not task-completion alerts',async()=>{
  for(const action of ['abort','shutdown','outcome']) {
    const h=harness();await h.emit('agent_start');
    if(action==='shutdown') await h.emit('session_shutdown');
    if(action==='outcome') await h.emit('agent_before_settle',{outcome:'aborted'});
    await h.emit('agent_settled',{aborted:action==='abort'});assert.equal(sends(h).length,0);
  }
});
test('errors are labeled honestly, no prompt/path/model output leaks',async()=>{
  const h=harness();await h.emit('agent_start');await h.emit('agent_before_settle',{outcome:'error',entries:[{secret:'private conversation'}]});
  await h.emit('agent_settled',{aborted:false});const call=sends(h)[0];
  assert(call.args.includes('Pi — traitement en erreur'));assert(!call.args.join(' ').includes('private conversation'));
});
test('continuation outcome supersedes a previous boundary error',async()=>{
  const h=harness();await h.emit('agent_start');await h.emit('agent_before_settle',{outcome:'error'});
  await h.emit('agent_start');await h.emit('agent_before_settle',{outcome:'completed'});await h.emit('agent_settled',{aborted:false});
  assert(sends(h)[0].args.includes('Pi — tâche terminée'));assert.equal(captures(h).length,1);
});
test('capture failure, invalid output or kill falls back to explicit global without late lookup',async()=>{
  for(const result of [{stdout:B,code:1,killed:false},{stdout:'invalid',code:0,killed:false},{stdout:A,code:0,killed:true}]) {
    const h=harness((_f,args)=>args[0]==='capture'?result:{stdout:'',code:0,killed:false});await h.emit('agent_start');await h.emit('agent_settled',{aborted:false});
    assert.equal(captures(h).length,1);assert.equal(sends(h)[0].args[2],'global');
  }
});
test('capture exceptions never break work; valid neutral/global stay distinct',async()=>{
  for(const context of [null,'neutral','global']) {
    const h=harness((_f,args)=>{if(args[0]==='capture'&&context===null) throw Error('missing helper');return {stdout:context,code:0,killed:false};});
    await h.emit('agent_start');await h.emit('agent_settled',{aborted:false});
    assert.equal(sends(h)[0].args[2],context??'global');
  }
});
test('failed send is swallowed and never replayed',async(t)=>{
  t.mock.method(console,'error',()=>{});
  const h=harness((_f,args)=>{if(args[0]==='send') throw Error('sender down');return {stdout:A,code:0,killed:false};});
  await h.emit('agent_start');await h.emit('agent_settled',{aborted:false});await h.emit('agent_settled',{aborted:false});
  assert.equal(sends(h).length,1);
});
test('late capture after shutdown cannot revive an abandoned task',async()=>{
  let complete;const h=harness(()=>new Promise(resolve=>{complete=resolve;}));
  const starting=h.emit('agent_start');await h.emit('session_shutdown');complete({stdout:A,code:0,killed:false});await starting;
  await h.emit('agent_settled',{aborted:false});assert.equal(sends(h).length,0);
});

test('actual helper forwards frozen context/hint, even after current desktop changes',async()=>{
  const root=await mkdtemp(join(tmpdir(),'pi-notify-'));
  const original={...process.env};
  try {
    await mkdir(join(root,'.local/bin'),{recursive:true});await mkdir(join(root,'bin'));
    await cp(resolve(here,'../../../runtime/target/release/agora-notify'),join(root,'.local/bin/agora-notify'));
    await chmod(join(root,'.local/bin/agora-notify'),0o700);
    await writeFile(join(root,'state.json'),JSON.stringify({context_confirmed:true,displayed_context:A.slice(8),active_session_id:A.slice(8),sessions:[{id:A.slice(8)}]}));
    const status=join(root,'.local/bin/session-desktop');
    await writeFile(status,'#!/usr/bin/python3\nimport os\nfrom pathlib import Path\nr=Path(os.environ["HOME"]);print((r/"state.json").read_text());(r/"captured").write_text("yes")\n');await chmod(status,0o700);
    const sender=join(root,'bin/notify-send');
    await writeFile(sender,'#!/usr/bin/python3\nimport os,sys,json\nfrom pathlib import Path\n(Path(os.environ["HOME"])/"notification.json").write_text(json.dumps(sys.argv[1:]))\n');await chmod(sender,0o700);
    process.env.HOME=root;process.env.PATH=join(root,'bin')+':'+original.PATH;delete process.env.AGORA_NOTIFICATION_CONTEXT;
    const execute=async(file,args,options)=>{
      try {const result=await promisify(execFile)(file,args,{timeout:options.timeout,env:{...process.env}});return {...result,code:0,killed:false};}
      catch(e){return {stdout:e.stdout??'',stderr:e.stderr??'',code:e.code??1,killed:!!e.killed};}
    };
    const h=harness(execute);await h.emit('agent_start');
    await writeFile(join(root,'state.json'),JSON.stringify({context_confirmed:true,displayed_context:B.slice(8),active_session_id:B.slice(8),sessions:[{id:B.slice(8)}]}));
    await h.emit('agent_settled',{aborted:false});
    const notification=JSON.parse(await readFile(join(root,'notification.json'),'utf8'));
    assert(notification.includes('string:x-agora-context:'+A));assert(!notification.includes('string:x-agora-context:'+B));
    // An inherited launch origin wins over the currently selected desktop.
    process.env.AGORA_NOTIFICATION_CONTEXT=A;
    const inherited=harness(execute);await inherited.emit('agent_start');await inherited.emit('agent_settled',{aborted:false});
    assert(JSON.parse(await readFile(join(root,'notification.json'),'utf8')).includes('string:x-agora-context:'+A));
    // Load through the installed Pi loader too, without creating a session/model.
    const executable=await promisify(execFile)('which',['pi']);
    let directory=dirname(await realpath(executable.stdout.trim()));
    while(directory!=='/' && !existsSync(join(directory,'dist/core/extensions/loader.js'))) directory=dirname(directory);
    const {loadExtensions}=await import(pathToFileURL(join(directory,'dist/core/extensions/loader.js')).href);
    const loaded=await loadExtensions([join(here,'index.ts')],root);
    assert.deepEqual(loaded.errors,[]);assert.equal(loaded.extensions.length,1);
    const events=loaded.extensions[0].handlers;
    assert(events.has('agent_settled'));assert(!events.has('agent_end'));
  } finally {
    for(const key of Object.keys(process.env)) if(!(key in original)) delete process.env[key];
    Object.assign(process.env,original);await rm(root,{recursive:true,force:true});
  }
});
