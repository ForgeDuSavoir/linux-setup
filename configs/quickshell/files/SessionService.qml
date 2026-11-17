import Quickshell
import Quickshell.Io
import QtQuick

// One shared, bounded reader and action client. Notifications own attention,
// not this component. A logical active ID is not proof of desktop visibility.
Scope {
    id: service
    property var sessions: []
    property string activeId: ""
    readonly property string activeName: {
        const item = sessions.find(item => item.id === activeId);
        return item ? item.name : "none";
    }
    // Paint the last confirmed selection while a switch is in flight. This
    // cached UI value must never be used for notification acknowledgement.
    property string visualContext: "unknown"
    property string displayedContext: "unknown"
    property bool contextConfirmed: false
    property bool stale: true
    property string error: ""
    property int generation: 0
    property bool refreshPending: false
    readonly property bool busy: actionProcess.running
    readonly property string desktop: Quickshell.env("HOME") + "/.local/bin/session-desktop"
    signal updated()
    signal actionFinished(bool success, string message)

    Component.onCompleted: refresh()
    Timer { interval: 2000; running: true; repeat: true; onTriggered: service.refresh() }

    function refresh() {
        if (snapshot.running || actionProcess.running) {
            refreshPending = true;
            return;
        }
        refreshPending = false;
        snapshot.requestGeneration = generation;
        snapshot.running = true;
    }

    function validSource(source) {
        return source !== null && typeof source === "object" && !Array.isArray(source)
            && ((source.kind === "neutral" && Object.keys(source).length === 1)
                || (source.kind === "project" && Object.keys(source).length === 2
                    && typeof source.project_name === "string" && source.project_name.length > 0));
    }

    function acceptSnapshot(result) {
        if (!Array.isArray(result.sessions) || typeof result.context_confirmed !== "boolean"
                || typeof result.displayed_context !== "string")
            throw new Error("invalid session snapshot");
        const ids = new Set();
        if (result.sessions.length > 1024)
            throw new Error("session limit exceeded");
        for (const item of result.sessions) {
            if (typeof item.id !== "string" || ids.has(item.id)
                    || typeof item.name !== "string" || !validSource(item.source)
                    || !Number.isInteger(item.number) || item.number < 1)
                throw new Error("invalid session entry");
            ids.add(item.id);
        }
        const active = result.active_session_id || "";
        if (result.context_confirmed && result.displayed_context !== (active || "neutral"))
            throw new Error("inconsistent desktop confirmation");
        if (active && !result.sessions.some(item => item.id === active))
            throw new Error("unknown active session");
        // Keep delegates stable on unchanged polls instead of recreating all
        // buttons every two seconds. Preserve the complete session projection.
        const sameRows = sessions.length === result.sessions.length && sessions.every((item, index) => {
            const next = result.sessions[index];
            return item.id === next.id && item.name === next.name && JSON.stringify(item.source) === JSON.stringify(next.source)
                && item.number === next.number && item.lifecycle === next.lifecycle && item.active === next.active;
        });
        visualContext = result.context_confirmed ? result.displayed_context : "unknown";
        if (!sameRows)
            sessions = result.sessions;
        activeId = active;
        displayedContext = result.displayed_context;
        contextConfirmed = result.context_confirmed;
        stale = false;
        error = contextConfirmed ? "" : "Logical session and displayed desktop differ";
        updated();
    }

    function finishSnapshot(exitCode, requestGeneration, output, diagnostic) {
        if (requestGeneration === generation) {
            try {
                if (exitCode !== 0)
                    throw new Error(diagnostic.trim().split("\n")[0] || "Session service unavailable");
                acceptSnapshot(JSON.parse(output));
            } catch (failure) {
                stale = true;
                contextConfirmed = false;
                error = String(failure);
            }
        }
        if (refreshPending)
            Qt.callLater(function() { service.refresh(); });
    }

    function invalidateContext() {
        generation++;
        contextConfirmed = false;
        stale = true;
        refresh();
    }

    function act(argumentsList) {
        if (actionProcess.running)
            return;
        generation++;
        contextConfirmed = false;
        stale = true;
        error = "";
        actionProcess.argumentsList = argumentsList;
        actionProcess.running = true;
    }

    Process {
        id: snapshot
        property int requestGeneration: 0
        command: [service.desktop, "status"]
        stdout: StdioCollector { id: snapshotOutput }
        stderr: StdioCollector { id: snapshotError }
        onExited: function(exitCode) {
            service.finishSnapshot(exitCode, requestGeneration, snapshotOutput.text, snapshotError.text);
        }
    }

    Process {
        id: actionProcess
        property var argumentsList: []
        command: [service.desktop].concat(argumentsList)
        stdout: StdioCollector { id: actionOutput }
        stderr: StdioCollector { id: actionError }
        onExited: function(exitCode) {
            const message = exitCode === 0 ? "" : actionError.text.trim().split("\n")[0] || "Session action failed";
            service.error = message;
            service.actionFinished(exitCode === 0, message);
            Qt.callLater(function() { service.refresh(); });
        }
    }
}
