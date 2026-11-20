#!/usr/bin/env node
// Exact QML state-machine methods + actual pure notification policy; no IO beyond sources.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../quickshell/files');
const source=fs.readFileSync(path.join(root,'SessionService.qml'),'utf8');
function method(name){const start=source.indexOf(`    function ${name}(`);assert(start>=0);const open=source.indexOf('{',start);let depth=0;for(let i=open;i<source.length;i++){if(source[i]==='{')depth++;if(source[i]==='}'&&--depth===0)return source.slice(start,i+1);}throw Error(name);}
const policy={};vm.createContext(policy);vm.runInContext(fs.readFileSync(path.join(root,'NotificationPolicy.js'),'utf8'),policy);
const A='11111111-1111-1111-1111-111111111111',B='22222222-2222-2222-2222-222222222222',C='33333333-3333-3333-3333-333333333333';
const rows=[{id:B,name:'Zulu',source:{kind:'project',project_name:'Zulu'},number:1},{id:A,name:'Alpha',source:{kind:'neutral'},number:1},{id:C,name:'Beta',source:{kind:'neutral'},number:2}];
function fixture(){
 const s={sessions:[],activeId:'',generation:0,refreshPending:false,navigationPhase:'idle',navigationTarget:'',navigationError:'',snapshot:{running:false},actionProcess:{running:false},Qt:{callLater:f=>f()},updated:()=>s.notificationState.synchronize(),actionFinished:()=>{}};
 Object.defineProperty(s,'busy',{get:()=>s.actionProcess.running||s.navigationPhase!=='idle'});s.service=s;
 const store={history:[],hasUnread:id=>store.history.some(e=>e.unread&&policy.scoped(e)&&e.context==='session:'+id),synchronize:()=>{store.history=policy.reconcile(store.history,s.sessions,s.stale||!s.contextConfirmed?'unknown':s.displayedContext==='neutral'?'neutral':'session:'+s.displayedContext,!s.stale);}};
 s.notificationState=store;vm.createContext(s);
 for(const n of ['refresh','validSource','acceptSnapshot','finishSnapshot','invalidateContext','act','startAction','attentionTarget','nextAttention','continueNavigation','finishAction'])vm.runInContext(method(n),s);
 const state=(active=A,extra={})=>({sessions:rows,active_session_id:active,displayed_context:active||'neutral',context_confirmed:true,...extra});
 const read=(active=A,extra={})=>{s.snapshot.running=false;s.finishSnapshot(0,s.snapshot.requestGeneration,JSON.stringify(state(active,extra)),'');};
 const seed=(...ids)=>{store.history=ids.map((id,i)=>({key:String(i),id:i,context:'session:'+id,orphan:false,live:true,unread:true,popup:false}));};
 s.acceptSnapshot(state());return {s,store,state,read,seed};
}
let f=fixture();f.seed(C,B);f.s.nextAttention();assert(f.s.busy&&f.s.snapshot.running);f.read();assert.deepEqual(Array.from(f.s.actionProcess.argumentsList),['switch',B],'leftmost pending, not arrival/alphabetical order');assert(f.store.hasUnread(B));
let generation=f.s.generation;f.s.nextAttention();f.s.act(['switch',C]);assert.equal(f.s.generation,generation,'busy presses are ignored');
f.s.actionProcess.running=false;f.s.finishAction(0,'');assert(f.s.busy&&f.s.snapshot.running,'still busy until fresh confirmation');f.read(B);assert(!f.s.busy&&!f.store.hasUnread(B)&&f.store.hasUnread(C));
f.s.nextAttention();f.read(B);assert.equal(f.s.actionProcess.argumentsList[1],C);f.s.actionProcess.running=false;f.s.finishAction(0,'');f.read(C);assert(!f.store.hasUnread(C));
f.s.nextAttention();f.read(C);assert.equal(f.s.actionProcess.argumentsList[1],B,'ordinary successor wraps in bar order');
f=fixture();f.s.nextAttention();f.read();assert.equal(f.s.actionProcess.argumentsList[1],C,'successor of A, not alphabetic');
f=fixture();f.s.nextAttention();f.read(null);assert.equal(f.s.actionProcess.argumentsList[1],B,'unowned selects first row');
for(const rs of [[],[rows[1]]]){f=fixture();f.s.nextAttention();f.read(rs.length?A:null,{sessions:rs});assert(!f.s.busy&&!f.s.actionProcess.running);}
f=fixture();f.seed(B);f.s.nextAttention();f.read();f.s.actionProcess.running=false;f.s.finishAction(7,'synthetic failure');f.read(A);assert(!f.s.busy&&f.store.hasUnread(B)&&f.s.error==='synthetic failure');
f=fixture();f.seed(B);f.s.nextAttention();f.read();f.s.actionProcess.running=false;f.s.finishAction(0,'');f.read(A);assert(!f.s.busy&&f.store.hasUnread(B)&&f.s.error.includes('not confirmed'),'hide-first/mismatched target never clears attention or retries');
f=fixture();f.seed(B);f.s.nextAttention();f.read(A,{context_confirmed:false});assert(!f.s.busy&&!f.s.actionProcess.running&&f.store.hasUnread(B));
f=fixture();f.s.snapshot.running=true;f.s.snapshot.requestGeneration=0;f.s.nextAttention();f.s.snapshot.running=false;f.s.finishSnapshot(0,0,JSON.stringify(f.state()),'');assert.equal(f.s.navigationPhase,'choose');assert(f.s.snapshot.running,'old read triggers fresh read without a timer');f.read();assert(f.s.actionProcess.running);
f=fixture();f.s.nextAttention();f.s.snapshot.running=false;f.s.finishSnapshot(1,f.s.generation,'','backend offline');assert(!f.s.busy&&f.s.error.includes('offline'));
f=fixture();f.seed(B);f.s.nextAttention();f.read(A,{sessions:[rows[1],rows[2]]});assert.equal(f.s.actionProcess.argumentsList[1],C);assert(!f.store.hasUnread(B),'closed-session attention is orphaned, not selected');
f=fixture();f.seed(A,B);f.s.nextAttention();f.read();assert.equal(f.s.actionProcess.argumentsList[1],B);assert(!f.store.hasUnread(A),'current-session attention reconciled before choosing');
const menu=fs.readFileSync(path.join(root,'SessionMenu.qml'),'utf8');assert(menu.includes('function nextAttention(): void { menu.sessionService.nextAttention(); }'));
assert(fs.readFileSync(path.join(root,'shell.qml'),'utf8').includes('notificationState: notificationService'));
console.log('Session attention: exact bar-order priority/cycle, fresh status, real policy acknowledgement, repeat/action serialization through confirmation, failure/no retry, orphan/current/Neutral/unowned/empty/single and IPC wiring passed.');
