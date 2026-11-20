#!/usr/bin/env node
// Run exact service methods with fake processes; no desktop/notifications touched.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../quickshell/files/SessionService.qml'), 'utf8');
function method(source, name) {
    const start = source.indexOf(`    function ${name}(`);
    assert(start >= 0);
    const open = source.indexOf('{', start);
    let depth = 0;
    for (let i = open; i < source.length; i++) {
        if (source[i] === '{') depth++;
        if (source[i] === '}' && --depth === 0) return source.slice(start, i + 1);
    }
    throw Error('unclosed method');
}
const service = {navigationPhase: 'idle', navigationTarget: '', navigationError: '', sessions: [], activeId: '', generation: 0, refreshPending: false,
    snapshot: {running: false}, actionProcess: {running: false},
    Qt: {callLater: callback => callback()}, updated: () => {}};
Object.defineProperty(service, 'busy', {get: () => service.actionProcess.running || service.navigationPhase !== 'idle'});
service.service = service;
vm.createContext(service);
for (const name of ['validSource', 'refresh', 'acceptSnapshot', 'finishSnapshot', 'invalidateContext', 'act', 'startAction', 'finishAction', 'continueNavigation', 'attentionTarget', 'nextAttention'])
    vm.runInContext(method(source, name), service);
const state = {sessions: [{id: 'z', name: 'Zulu-1', source: {kind: 'project', project_name: 'Zulu'}, number: 1}, {id: 'a', name: 'Alpha-1', source: {kind: 'project', project_name: 'Alpha'}, number: 1}], active_session_id: 'a', displayed_context: 'a', context_confirmed: true};
service.acceptSnapshot(state);
assert.deepEqual(service.sessions, state.sessions);
assert.equal(service.contextConfirmed, true);
assert.equal(service.visualContext, 'a');
const stableRows = service.sessions;
service.acceptSnapshot(JSON.parse(JSON.stringify(state)));
assert.strictEqual(service.sessions, stableRows, 'identical polls must not recreate session buttons');
service.refresh();
assert.equal(service.snapshot.running, true);
service.refresh();
assert.equal(service.refreshPending, true);
service.act(['switch', 'z']);
assert.equal(service.contextConfirmed, false);
assert.equal(service.stale, true);
assert.equal(service.visualContext, 'a', 'pending action keeps the last painted selection');
service.refreshPending = false;
service.finishSnapshot(0, 0, JSON.stringify(state), '');
assert.equal(service.contextConfirmed, false, 'old in-flight snapshot must not confirm a new action');
service.finishSnapshot(1, 1, '', 'daemon unavailable');
assert.equal(service.stale, true);
assert.equal(service.activeId, 'a', 'failure preserves last good state, never invents neutral');
assert.deepEqual(service.sessions, state.sessions);
service.finishSnapshot(0, 1, JSON.stringify({...state, active_session_id: 'z', context_confirmed: false}), '');
assert.equal(service.stale, false);
assert.equal(service.contextConfirmed, false);
assert(service.error.includes('differ'));
service.finishSnapshot(0, 1, JSON.stringify({...state, displayed_context: 'neutral'}), '');
assert.equal(service.stale, true, 'a conflicting confirmation must fail');
service.finishSnapshot(0, 1, JSON.stringify({sessions: [], active_session_id: null, displayed_context: 'neutral', context_confirmed: true}), '');
assert.equal(service.sessions.length, 0);
assert.equal(service.activeId, '');
assert.equal(service.contextConfirmed, true);
service.finishSnapshot(0, 1, '{bad json', '');
assert.equal(service.stale, true);
service.snapshot.running = false;
service.actionProcess.running = false;
const previousGeneration = service.generation;
service.invalidateContext();
assert.equal(service.generation, previousGeneration + 1);
assert.equal(service.stale, true);
assert.equal(service.contextConfirmed, false);
assert.equal(service.snapshot.requestGeneration, service.generation);
const strip = fs.readFileSync(path.join(__dirname, '../quickshell/files/SessionStrip.qml'), 'utf8');
assert(!strip.includes('ToolTip.'), 'bar tooltips must not intercept clicks or be clipped by the panel');
vm.runInContext(method(strip, 'initials'), service);
assert.equal(service.initials('Forge du Savoir YouTube'), 'FDS');
assert.equal(service.initials('Linux Workflow'), 'LW');
assert.equal(service.initials('foo-bar'), 'FB');
assert.equal(service.initials('Écriture'), 'É');
console.log('Shared session service: ordered snapshots, bounded polling, errors, stale generations and initials passed.');

const neutralRows = [{id: 'n1', name: 'Neutral-1', source: {kind: 'neutral'}, number: 1},
    {id: 'n2', name: 'Neutral-2', source: {kind: 'neutral'}, number: 2}];
service.acceptSnapshot({sessions: neutralRows, active_session_id: 'n2', displayed_context: 'n2', context_confirmed: true});
assert.equal(service.visualContext, 'n2');
assert.equal(service.sessions.length, 2);
for (const invalid of [null, {}, {kind:'neutral',project_name:null}, {kind:'project'}, {kind:'task'}])
    assert.equal(service.validSource(invalid), false);
assert.equal(service.validSource({kind:'neutral'}), true);
