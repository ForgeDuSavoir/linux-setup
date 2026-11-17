import QtQuick
import QtTest
import "../quickshell/files" as Components

Item {
    id: fixture
    width: 400
    height: 100

    QtObject {
        id: sessions
        property var sessions: [{id: "test-n", source: {kind: "neutral"}, number: 1, name: "Neutral-1"}, {id: "test-a", source: {kind: "project", project_name: "Alpha"}, number: 1, name: "Alpha-1"}]
        property bool contextConfirmed: true
        property string displayedContext: "neutral"
        property string visualContext: "test-n"
        property bool stale: false
        property bool busy: false
        function act(args) { tests.calls = tests.calls.concat([args]); }
    }
    Components.SessionStrip {
        id: strip
        x: 10; y: 10
        width: 100; height: 26
        sessionService: sessions
    }
    TestCase {
        id: tests
        name: "SessionSquareHitArea"
        when: windowShown
        property var calls: []

        function findButton(item, name) {
            if (item.objectName === name) return item;
            for (const child of item.children || []) {
                const found = findButton(child, name);
                if (found) return found;
            }
            return null;
        }
        function init() {
            calls = [];
            sessions.busy = false;
            sessions.stale = false;
            sessions.contextConfirmed = true;
            strip.scrollOffset = 0;
            mouseMove(fixture, 350, 80);
        }
        function test_fullSquare_data() {
            return [
                {tag: "top-left", x: 1, y: 1},
                {tag: "top-right", x: 25, y: 1},
                {tag: "bottom-left", x: 1, y: 25},
                {tag: "bottom-right", x: 25, y: 25},
                {tag: "left-edge", x: 1, y: 13},
                {tag: "right-edge", x: 25, y: 13},
                {tag: "text-center", x: 13, y: 13}
            ];
        }
        function test_fullSquare(data) {
            const button = findButton(strip, "session-case-test-a");
            verify(button !== null);
            mouseMove(button, data.x, data.y);
            tryCompare(button, "hovered", true);
            compare(String(button.background.color), "#343d4f");
            mouseClick(button, data.x, data.y, Qt.LeftButton);
            compare(calls.length, 1);
            compare(calls[0][0], "switch");
            compare(calls[0][1], "test-a");
        }
        function test_entireLowerHalf() {
            const button = findButton(strip, "session-case-test-a");
            compare(button.background.x, 0);
            compare(button.background.y, 0);
            compare(button.background.width, button.width);
            compare(button.background.height, button.height);
            for (let y = 13; y < 26; y++) {
                for (let x = 0; x < 26; x++) {
                    mouseMove(button, x, y);
                    verify(button.hovered, "hover missing at " + x + "," + y);
                    mouseClick(button, x, y, Qt.LeftButton);
                }
            }
            compare(calls.length, 13 * 26);
        }
        function test_pendingSwitchDoesNotFlash() {
            const button = findButton(strip, "session-case-test-a");
            const neutral = findButton(strip, "session-case-test-n");
            sessions.busy = true;
            sessions.stale = true;
            sessions.contextConfirmed = false;
            compare(String(button.background.border.color), "#00000000");
            compare(String(neutral.background.border.color), "#00000000");
            compare(button.opacity, 1);
            compare(neutral.opacity, 1);
            compare(String(neutral.background.color), "#3d5a80");
            sessions.busy = false;
            sessions.stale = false;
            sessions.contextConfirmed = true;
            compare(String(button.background.border.color), "#00000000");
        }
        function test_neutralCorner() {
            const button = findButton(strip, "session-case-test-n");
            mouseClick(button, 1, 1, Qt.LeftButton);
            compare(calls.length, 1);
            compare(calls[0][0], "switch");
            compare(calls[0][1], "test-n");
        }
        function test_overflowBottomEdge() {
            const many = [];
            for (let i = 0; i < 30; i++)
                many.push({id:"test-" + i, source: {kind: "project", project_name: "Project"}, number:i+1, name:"Project-"+(i+1)});
            sessions.sessions = many;
            wait(50);
            const button = findButton(strip, "session-case-test-0");
            mouseMove(button, 1, 25);
            tryCompare(button, "hovered", true);
            mouseClick(button, 1, 25, Qt.LeftButton);
            compare(calls.length, 1);
            compare(calls[0][1], "test-0");
            mouseWheel(strip, 50, 13, 0, -120);
            tryVerify(function() { return strip.scrollOffset > 0; });
            strip.scrollOffset = 0;
            sessions.sessions = [{id: "test-n", source: {kind: "neutral"}, number: 1, name: "Neutral-1"}, {id:"test-a", source: {kind: "project", project_name: "Alpha"}, number:1, name:"Alpha-1"}];
            wait(50);
        }
        function test_busyDoesNotLaunch() {
            sessions.busy = true;
            const button = findButton(strip, "session-case-test-a");
            mouseClick(button, 1, 1, Qt.LeftButton);
            compare(calls.length, 0);
        }
    }
}
