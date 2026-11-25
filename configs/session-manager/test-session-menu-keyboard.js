#!/usr/bin/env node
// Exercise the exact QML menu navigation methods without opening a desktop window.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../quickshell/files/SessionMenu.qml'), 'utf8');
function method(name) {
    const start = source.indexOf(`    function ${name}(`);
    assert(start >= 0, `missing ${name}`);
    const open = source.indexOf('{', start);
    let depth = 0;
    for (let i = open; i < source.length; i++) {
        if (source[i] === '{') depth++;
        if (source[i] === '}' && --depth === 0)
            return source.slice(start, i + 1);
    }
    throw new Error(`unclosed ${name}`);
}
const calls = [];
const menu = {
    Qt: {
        Key_Tab: 1, Key_Backtab: 2, Key_Up: 3, Key_Down: 4,
        Key_Return: 5, Key_Enter: 6, Key_Escape: 7, callLater: fn => fn(),
    },
    projects: Array.from({length: 10}, (_, n) => ({name: `Project ${n}`, source: {kind: "project", project_name: `Project ${n}`}})),
    sessions: [{id: 'uuid-1'}, {id: 'uuid-2'}],
    selectedSection: 'projects', selectedProject: 0, selectedSession: 0,
    projectList: {contentY: 0, contentHeight: 336, height: 145},
    sessionList: {contentY: 0, contentHeight: 68, height: 225},
    menuVisible: true,
    menuRoot: {forceActiveFocus: () => { menu.focusTarget = 'sessions'; }},
    searchInput: {text: '', forceActiveFocus: () => { menu.focusTarget = 'search'; }},
    refresh: () => {},
    act: args => calls.push(args),
};
menu.filteredProjects = menu.projects;
menu.searchText = '';
menu.menu = menu;
vm.createContext(menu);
const filterExpression = source.match(/readonly property var filteredProjects: (.+)\n/)[1];
function filter(query) {
    menu.searchText = query;
    menu.filteredProjects = vm.runInContext(filterExpression, menu);
    menu.selectedProject = 0;
    menu.projectList.contentY = 0;
    menu.normalizeSelection();
}
for (const name of ['showMenu', 'focusSelection', 'ensureSelectedVisible', 'normalizeSelection', 'startArguments', 'handleKey', 'maybeShowStartupMenu', 'onUpdated'])
    vm.runInContext(method(name), menu);
function key(code) {
    const event = {key: code, accepted: false};
    menu.handleKey(event);
    assert(event.accepted);
}
menu.showMenu();
assert.equal(menu.selectedSection, 'projects');
assert.equal(menu.focusTarget, 'search');
menu.onUpdated();
assert.equal(menu.selectedSection, 'projects', 'fresh session rows must not move initial focus');
assert.equal(menu.focusTarget, 'search');
key(menu.Qt.Key_Tab);
assert.equal(menu.selectedSection, 'sessions');
assert.equal(menu.focusTarget, 'sessions');
menu.onUpdated();
assert.equal(menu.selectedSection, 'sessions', 'explicit Tab choice survives later refresh');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['switch', 'uuid-1']);
key(menu.Qt.Key_Tab);
assert.equal(menu.selectedSection, 'projects');
assert.equal(menu.focusTarget, 'search');
key(menu.Qt.Key_Up);
assert.equal(menu.selectedProject, 0);
for (let i = 0; i < 20; i++) key(menu.Qt.Key_Down);
assert.equal(menu.selectedProject, 9);
assert(menu.projectList.contentY > 0, 'selection must scroll past clipped projects');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--project', 'Project 9']);
key(menu.Qt.Key_Tab);
assert.equal(menu.selectedSection, 'sessions');
key(menu.Qt.Key_Down);
assert.equal(menu.selectedSession, 1);
key(menu.Qt.Key_Enter);
assert.deepEqual(Array.from(calls.pop()), ['switch', 'uuid-2']);
key(menu.Qt.Key_Backtab);
assert.equal(menu.selectedSection, 'projects');
filter(' PROJECT 3 ');
assert.equal(menu.filteredProjects.length, 1);
assert.equal(menu.filteredProjects[0].name, 'Project 3');
assert.equal(menu.sessions.length, 2, 'search cannot filter open sessions');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--project', 'Project 3']);
filter('nothing matches');
assert.equal(menu.filteredProjects.length, 0);
assert.equal(menu.selectedSection, 'projects');
const count = calls.length;
key(menu.Qt.Key_Return);
assert.equal(calls.length, count, 'Enter cannot launch a hidden project');
key(menu.Qt.Key_Tab);
assert.equal(menu.selectedSection, 'sessions');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['switch', 'uuid-2']);
key(menu.Qt.Key_Backtab);
assert.equal(menu.selectedSection, 'projects');
filter('');
assert.equal(menu.filteredProjects.length, 10);
menu.projects = [];
filter('');
assert.equal(menu.selectedSection, 'projects', 'empty/loading sources must not force a session switch');
menu.sessions = [];
menu.normalizeSelection();
key(menu.Qt.Key_Return);
key(menu.Qt.Key_Tab);
assert.equal(calls.length, count, 'empty lists must not run an action');
key(menu.Qt.Key_Escape);
assert.equal(menu.menuVisible, false);
menu.showMenu();
assert.equal(menu.selectedSection, 'projects');
assert.equal(menu.focusTarget, 'search');
console.log('Session menu search, arrows, Tab, Enter, selection bounds and scroll: passed');

for (const name of ['finishStartupClaim','maybeShowStartupMenu'])
    vm.runInContext(method(name),menu);
menu.sessions=[];menu.activeId='';
let invalidations=0;
menu.sessionService={busy:false,stale:false,contextConfirmed:true,displayedContext:'neutral',invalidateContext:()=>invalidations++};
menu.startupMenuPending=false;menu.startupMenuUsed=false;menu.menuVisible=false;
menu.finishStartupClaim(0,'{"show":true}','');
assert(menu.startupMenuPending&&!menu.menuVisible);assert.equal(invalidations,1);
menu.maybeShowStartupMenu();assert(menu.menuVisible&&menu.startupMenuUsed&&!menu.startupMenuPending);
assert.equal(menu.focusTarget,'search');
key(menu.Qt.Key_Escape);menu.maybeShowStartupMenu();assert(!menu.menuVisible,'Escape must not reopen startup menu');
menu.startupMenuUsed=false;menu.finishStartupClaim(0,'{"show":false}','');menu.maybeShowStartupMenu();assert(!menu.menuVisible);
menu.startupMenuUsed=false;menu.startupMenuPending=true;menu.sessions=[{id:'user'}];menu.activeId='user';menu.maybeShowStartupMenu();assert(!menu.menuVisible&&!menu.startupMenuPending,'user-created session wins');
menu.sessions=[];menu.activeId='';menu.showMenu();key(menu.Qt.Key_Escape);menu.finishStartupClaim(0,'{"show":true}','');assert(!menu.startupMenuPending,'manual show/close before claim wins');
menu.startupMenuUsed=false;menu.finishStartupClaim(1,'','failure');assert(!menu.menuVisible&&menu.status==='failure');
menu.finishStartupClaim(0,'{"show":"yes"}','');assert(menu.status.includes('invalid'));
console.log('Startup menu: fresh status gate, search focus, explicit native claim, Escape/no reopen, user selection/manual menu and error guards passed.');

menu.projects = [{name: 'Neutral', source: {kind: 'neutral'}},
    {name: 'Neutral', source: {kind: 'project', project_name: 'Neutral'}},
    {name: 'Work', source: {kind: 'project', project_name: 'Work'}}];
menu.sessions = [];
menu.showMenu();
filter('   ');
assert.equal(menu.filteredProjects.length, 3);
assert.equal(menu.filteredProjects[0].source.kind, 'neutral', 'unfiltered Neutral stays first');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--neutral']);
filter(' WORK ');
assert.equal(menu.filteredProjects.length, 1, 'Neutral obeys the same name filter as projects');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--project', 'Work']);
filter('does not match any project');
assert.equal(menu.filteredProjects.length, 0);
const beforeUnmatched = calls.length;
key(menu.Qt.Key_Return);
assert.equal(calls.length, beforeUnmatched, 'no hidden Neutral launch on an unmatched query');
filter(' nEuT ');
assert.equal(menu.filteredProjects.length, 2, 'case-insensitive substring search includes both Neutral names');
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--neutral']);
menu.selectedProject = 1;
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--project', 'Neutral']);
console.log('Neutral uses ordinary name filtering, keeps unfiltered order and typed launch identity: passed.');
assert(!source.includes('Neutral workspace (keep sessions open)'), 'no singleton neutral button');
