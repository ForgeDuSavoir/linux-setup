#!/usr/bin/env node
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const policy = {};
vm.createContext(policy);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../quickshell/files/NotificationPolicy.js'), 'utf8'), policy);
const A = '11111111-1111-1111-1111-111111111111';
const B = '22222222-2222-2222-2222-222222222222';
const a = 'session:' + A, b = 'session:' + B;
const sessions = [{id: A}, {id: B}];
let serial = 0;
function receive(history, hint, current = a, id = ++serial, known = true) {
    return policy.receive(history, {id, key: String(++serial), hint, summary: 'fixture'}, sessions, current, known, 100);
}
for (const hint of [a, b, 'neutral', 'global', undefined, 'invalid', 'session:../../bad']) {
    const history = receive([], hint);
    const item = history[0];
    assert.equal(item.popup, ![b, 'neutral'].includes(hint));
    assert.equal(item.unread, [b, 'neutral'].includes(hint));
    if (hint === undefined || hint === 'invalid') assert.equal(item.context, 'unknown');
}
let history = receive([], b);
const key = history[0].key;
assert(policy.unreadContexts(history)[b]);
history = policy.close(history, history[0].id);
assert(history[0].unread && !history[0].popup, 'expiration must retain attention');
history = policy.reconcile(history, sessions, b, true);
assert(!history[0].unread && !history[0].popup, 'enter acknowledges, does not replay');
assert.equal(history[0].key, key);
history = receive([], a);
assert(history[0].popup && !history[0].unread);
history = policy.reconcile(history, sessions, b, true);
assert(!history[0].popup && history[0].unread, 'leaving hides foreground popup and marks attention');
history = policy.reconcile(history, sessions, a, true);
assert(!history[0].popup && !history[0].unread);
history = receive([], b);
history = policy.reconcile(history, sessions, 'unknown', false);
assert(history[0].unread, 'unconfirmed switch cannot acknowledge');
history = policy.reconcile(history, sessions, a, true);
assert(history[0].unread, 'a failed switch returning to A must retain B attention');
history = receive(history, 'global', a, history[0].id);
assert.equal(history.length, 1);
assert(!history[0].unread && history[0].popup, 'replacement changes attribution and attention');
history = receive([], b);
history = policy.reconcile(history, [{id: A}], a, true);
assert(history[0].orphan && history[0].popup && !history[0].unread);
const orphan = receive([], 'session:33333333-3333-3333-3333-333333333333')[0];
assert(orphan.orphan && orphan.popup);
const deferred = receive([], b, 'unknown', undefined, false)[0];
assert(!deferred.orphan && deferred.unread && !deferred.popup);
history = receive([], 'neutral', 'neutral');
assert(history[0].popup && !history[0].unread);
history = policy.reconcile(history, sessions, a, true);
assert(!history[0].popup && history[0].unread);
assert(policy.unreadContexts(history).neutral);
assert.equal(policy.remove(history, history[0].key).length, 0);
assert.equal(Object.keys(policy.unreadContexts([])).length, 0);
history = receive([], b);
for (let i = 0; i < 100; i++) history = receive(history, 'global');
assert.equal(history.length, 100);
assert(!policy.unreadContexts(history)[b], 'eviction removes attention belonging only to discarded entries');
const globals = receive([], 'global');
assert.strictEqual(policy.reconcile(globals, sessions, 'unknown', false), globals, 'unchanged polling must preserve history/model identity');
assert(policy.reconcile(globals, sessions, 'unknown', false)[0].popup);
// Exercise the exact QML badge accessor, not only the policy's context map.
const storeSource = fs.readFileSync(path.join(__dirname, '../quickshell/files/NotificationStore.qml'), 'utf8');
const accessor = storeSource.match(/    function hasUnread\(context\) \{[\s\S]*?\n    \}/)[0];
const store = {Policy: policy, history: [], currentContext: a};
vm.createContext(store);
vm.runInContext(accessor, store);
store.history = receive([], 'global');
for (const context of [A, B, 'neutral']) assert.equal(store.hasUnread(context), false);
store.history = receive([], b);
assert.equal(store.hasUnread(B), true);
store.history = receive(store.history, 'global');
assert.equal(store.hasUnread(B), true, 'global receipt must not clear a genuine B badge');
assert.equal(store.hasUnread(A), false);
assert.equal(store.hasUnread('neutral'), false);
store.currentContext = b;
assert.equal(store.hasUnread(B), false, 'current context can never be red');
store.history = [{context: 'global', unread: true, orphan: false}];
assert.equal(store.hasUnread(A), false, 'even a stale global unread flag cannot create a session badge');

// Beeper's application/desktop identity is not a session identity. Keep its
// untagged notifications global for any foreground context; no app-name guess.
for (const current of [a, b, 'neutral', 'unknown']) {
    const beeper = policy.receive([], {id: 999, key: 'beeper-fixture', appName: 'Beeper',
        desktopEntry: 'beeper.desktop', summary: 'Synthetic test'}, sessions, current, true, 100);
    assert.equal(beeper[0].context, 'unknown');
    assert.equal(beeper[0].popup, true);
    assert.equal(beeper[0].unread, false);
    assert.equal(Object.keys(policy.unreadContexts(beeper)).length, 0);
}
console.log('Notification policy: attribution, filtering, neutral/global/unknown/orphan, replacement, retention, expiry, confirmed entry and Beeper global fallback passed.');
