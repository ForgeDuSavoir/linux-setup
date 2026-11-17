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
for (const name of ['showMenu', 'focusSelection', 'ensureSelectedVisible', 'normalizeSelection', 'startArguments', 'handleKey'])
    vm.runInContext(method(name), menu);
function key(code) {
    const event = {key: code, accepted: false};
    menu.handleKey(event);
    assert(event.accepted);
}
menu.showMenu();
assert.equal(menu.selectedSection, 'sessions');
assert.equal(menu.focusTarget, 'sessions');
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
assert.equal(menu.selectedSection, 'sessions');
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

menu.projects = [{name: 'Neutral', source: {kind: 'neutral'}},
    {name: 'Neutral', source: {kind: 'project', project_name: 'Neutral'}}];
menu.sessions = [];
filter('does not match any project');
assert.equal(menu.filteredProjects.length, 1, 'built-in source remains available during project search');
menu.showMenu();
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--neutral']);
filter('Neutral');
menu.selectedProject = 1;
key(menu.Qt.Key_Return);
assert.deepEqual(Array.from(calls.pop()), ['start', '--project', 'Neutral']);
assert(!source.includes('Neutral workspace (keep sessions open)'), 'no singleton neutral button');
