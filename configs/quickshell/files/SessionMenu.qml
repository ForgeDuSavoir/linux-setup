import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick

Scope {
    id: menu

    property bool menuVisible: false
    property var sessions: []
    property var projects: []
    property string activeId: ""
    property string activeName: "none"
    property string status: ""
    property string pendingStop: ""
    readonly property string binary: Quickshell.env("HOME") + "/.local/bin/session-manager"
    readonly property string desktop: Quickshell.env("HOME") + "/.local/bin/session-desktop"

    Component.onCompleted: refresh()

    function refresh() {
        if (!sessionsProcess.running)
            sessionsProcess.running = true;
        if (!projectsProcess.running)
            projectsProcess.running = true;
    }

    function toggle() {
        menuVisible = !menuVisible;
        pendingStop = "";
        if (menuVisible)
            refresh();
    }

    function act(argumentsList) {
        if (actionProcess.running)
            return;
        status = "Working...";
        actionProcess.argumentsList = argumentsList;
        actionProcess.running = true;
    }

    Process {
        id: sessionsProcess
        command: [menu.binary, "--json", "session", "list"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!result.sessions)
                        throw new Error(result.code || "invalid session response");
                    menu.sessions = result.sessions;
                    menu.activeId = result.active_session_id || "";
                    const active = result.sessions.find(item => item.id === menu.activeId);
                    menu.activeName = active ? active.name : "none";
                    menu.status = "";
                } catch (error) {
                    menu.status = "Unable to read sessions: " + error;
                }
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    menu.status = text.trim().split("\n")[0];
            }
        }
    }

    Process {
        id: projectsProcess
        command: [menu.binary, "--json", "project", "list"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!result.projects)
                        throw new Error(result.code || "invalid project response");
                    menu.projects = result.projects;
                } catch (error) {
                    menu.status = "Unable to read projects: " + error;
                }
            }
        }
    }

    Process {
        id: actionProcess
        property var argumentsList: []
        command: [menu.desktop].concat(argumentsList)
        onExited: function(exitCode) {
            if (exitCode !== 0) {
                try {
                    const error = JSON.parse(actionOutput.text);
                    menu.status = error.code || "Session action failed";
                } catch (_) {
                    menu.status = actionError.text.trim().split("\n")[0] || "Session action failed";
                }
            }
            else {
                menu.pendingStop = "";
                menu.menuVisible = false;
                menu.refresh();
            }
        }
        stdout: StdioCollector { id: actionOutput }
        stderr: StdioCollector { id: actionError }
    }

    IpcHandler {
        target: "sessions"
        function toggle(): void { menu.toggle(); }
        function show(): void {
            menu.menuVisible = true;
            menu.refresh();
        }
        function hide(): void { menu.menuVisible = false; }
    }

    PanelWindow {
        visible: menu.menuVisible
        screen: Quickshell.screens[0]
        anchors { top: true }
        implicitWidth: 460
        implicitHeight: 570
        color: "transparent"
        WlrLayershell.namespace: "quickshell-sessions"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        WlrLayershell.exclusionMode: ExclusionMode.Ignore

        Rectangle {
            anchors.fill: parent
            color: "#151922"
            border.color: "#343d4f"
            radius: 8
            focus: menu.menuVisible
            Keys.onEscapePressed: menu.menuVisible = false

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    text: "Sessions — active: " + menu.activeName + "    (Esc to close)"
                    color: "#f0f0f0"
                    font.pixelSize: 16
                    elide: Text.ElideRight
                    width: parent.width
                }
                Text {
                    text: menu.status
                    color: "#d9a26b"
                    font.pixelSize: 12
                    width: parent.width
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    radius: 4
                    color: menu.activeId === "" ? "#3d5a80" : neutralMouse.containsMouse ? "#343d4f" : "#202633"
                    Text {
                        anchors.centerIn: parent
                        text: "Neutral workspace (keep sessions open)"
                        color: "#f0f0f0"
                        font.pixelSize: 12
                    }
                    MouseArea {
                        id: neutralMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: menu.act(["deactivate"])
                    }
                }
                Text { text: "Start from project"; color: "#aab3c4"; font.pixelSize: 13 }
                Flickable {
                    width: parent.width
                    height: 145
                    clip: true
                    contentHeight: projectColumn.implicitHeight
                    Column {
                        id: projectColumn
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: menu.projects
                            delegate: Rectangle {
                                required property var modelData
                                width: projectColumn.width
                                height: 30
                                radius: 4
                                color: projectMouse.containsMouse ? "#343d4f" : "#202633"
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 20
                                    text: "+ " + modelData.name
                                    elide: Text.ElideRight
                                    color: "#f0f0f0"
                                }
                                MouseArea {
                                    id: projectMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: menu.act(["start", modelData.name])
                                }
                            }
                        }
                    }
                }
                Text { text: "Open sessions (Stop requires two clicks)"; color: "#aab3c4"; font.pixelSize: 13 }
                Flickable {
                    width: parent.width
                    height: 225
                    clip: true
                    contentHeight: sessionColumn.implicitHeight
                    Column {
                        id: sessionColumn
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: menu.sessions
                            delegate: Row {
                                required property var modelData
                                width: sessionColumn.width
                                height: 32
                                spacing: 5
                                Rectangle {
                                    width: sessionColumn.width - 82
                                    height: 30
                                    radius: 4
                                    color: modelData.id === menu.activeId ? "#3d5a80" : switchMouse.containsMouse ? "#343d4f" : "#202633"
                                    Text {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: parent.width - 20
                                        text: modelData.name
                                        elide: Text.ElideRight
                                        color: "#f0f0f0"
                                    }
                                    MouseArea {
                                        id: switchMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: menu.act(["switch", modelData.id])
                                    }
                                }
                                Rectangle {
                                    width: 76
                                    height: 30
                                    radius: 4
                                    color: menu.pendingStop === modelData.id ? "#a04b4b" : stopMouse.containsMouse ? "#343d4f" : "#202633"
                                    Text {
                                        anchors.centerIn: parent
                                        text: menu.pendingStop === modelData.id ? "Confirm" : "Stop"
                                        color: "#f0f0f0"
                                        font.pixelSize: 12
                                    }
                                    MouseArea {
                                        id: stopMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            if (menu.pendingStop === modelData.id)
                                                menu.act(["stop", modelData.id]);
                                            else
                                                menu.pendingStop = modelData.id;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    text: "The menu keeps existing windows in their workspaces. Stop refuses sessions with windows."
                    wrapMode: Text.Wrap
                    color: "#7f8999"
                    font.pixelSize: 12
                }
            }
        }
    }
}
