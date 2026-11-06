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
    property string selectedSection: "projects"
    property int selectedProject: 0
    property int selectedSession: 0
    readonly property string binary: Quickshell.env("HOME") + "/.local/bin/session-manager"
    readonly property string desktop: Quickshell.env("HOME") + "/.local/bin/session-desktop"

    Component.onCompleted: refresh()

    function refresh() {
        if (!sessionsProcess.running)
            sessionsProcess.running = true;
        if (!projectsProcess.running)
            projectsProcess.running = true;
    }

    function showMenu() {
        menuVisible = true;
        pendingStop = "";
        selectedSection = projects.length ? "projects" : "sessions";
        selectedProject = 0;
        selectedSession = 0;
        refresh();
        Qt.callLater(function() { menuRoot.forceActiveFocus(); });
    }

    function toggle() {
        if (menuVisible)
            menuVisible = false;
        else
            showMenu();
    }

    function ensureSelectedVisible() {
        const list = selectedSection === "projects" ? projectList : sessionList;
        const index = selectedSection === "projects" ? selectedProject : selectedSession;
        const rowHeight = selectedSection === "projects" ? 34 : 36;
        const top = index * rowHeight;
        const bottom = top + rowHeight;
        if (top < list.contentY)
            list.contentY = top;
        else if (bottom > list.contentY + list.height)
            list.contentY = Math.min(bottom - list.height, Math.max(0, list.contentHeight - list.height));
    }

    function normalizeSelection() {
        selectedProject = Math.max(0, Math.min(selectedProject, projects.length - 1));
        selectedSession = Math.max(0, Math.min(selectedSession, sessions.length - 1));
        if (selectedSection === "projects" && !projects.length && sessions.length)
            selectedSection = "sessions";
        else if (selectedSection === "sessions" && !sessions.length && projects.length)
            selectedSection = "projects";
        if (menuVisible)
            Qt.callLater(function() { menu.ensureSelectedVisible(); });
    }

    function handleKey(event) {
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            if (selectedSection === "projects" && sessions.length)
                selectedSection = "sessions";
            else if (selectedSection === "sessions" && projects.length)
                selectedSection = "projects";
            ensureSelectedVisible();
        } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
            const count = selectedSection === "projects" ? projects.length : sessions.length;
            if (count) {
                const step = event.key === Qt.Key_Down ? 1 : -1;
                if (selectedSection === "projects")
                    selectedProject = Math.max(0, Math.min(selectedProject + step, count - 1));
                else
                    selectedSession = Math.max(0, Math.min(selectedSession + step, count - 1));
                ensureSelectedVisible();
            }
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (selectedSection === "projects" && projects[selectedProject])
                act(["start", projects[selectedProject].name]);
            else if (selectedSection === "sessions" && sessions[selectedSession])
                act(["switch", sessions[selectedSession].id]);
        } else {
            return;
        }
        event.accepted = true;
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
                    menu.normalizeSelection();
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
                    menu.normalizeSelection();
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
        function show(): void { menu.showMenu(); }
        function hide(): void { menu.menuVisible = false; }
    }

    PanelWindow {
        visible: menu.menuVisible
        screen: Quickshell.screens[0]
        anchors { top: true }
        implicitWidth: 460
        implicitHeight: 600
        color: "transparent"
        WlrLayershell.namespace: "quickshell-sessions"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        WlrLayershell.exclusionMode: ExclusionMode.Ignore

        Rectangle {
            id: menuRoot
            anchors.fill: parent
            color: "#151922"
            border.color: "#343d4f"
            radius: 8
            focus: menu.menuVisible
            Keys.onEscapePressed: menu.menuVisible = false
            Keys.onPressed: function(event) { menu.handleKey(event); }

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    text: "Sessions — active: " + menu.activeName
                    color: "#f0f0f0"
                    font.pixelSize: 16
                    elide: Text.ElideRight
                    width: parent.width
                }
                Text {
                    text: "↑↓ select · Tab switch list · Enter start/switch · Esc close"
                    color: "#aab3c4"
                    font.pixelSize: 12
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
                    id: projectList
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
                                required property int index
                                width: projectColumn.width
                                height: 30
                                radius: 4
                                color: menu.selectedSection === "projects" && menu.selectedProject === index ? "#506e93" : projectMouse.containsMouse ? "#343d4f" : "#202633"
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
                                    onClicked: {
                                        menu.selectedSection = "projects";
                                        menu.selectedProject = index;
                                        menu.act(["start", modelData.name]);
                                    }
                                }
                            }
                        }
                    }
                }
                Text { text: "Open sessions (Stop requires two clicks)"; color: "#aab3c4"; font.pixelSize: 13 }
                Flickable {
                    id: sessionList
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
                                required property int index
                                width: sessionColumn.width
                                height: 32
                                spacing: 5
                                Rectangle {
                                    width: sessionColumn.width - 82
                                    height: 30
                                    radius: 4
                                    color: menu.selectedSection === "sessions" && menu.selectedSession === index ? "#506e93" : modelData.id === menu.activeId ? "#3d5a80" : switchMouse.containsMouse ? "#343d4f" : "#202633"
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
                                        onClicked: {
                                            menu.selectedSection = "sessions";
                                            menu.selectedSession = index;
                                            menu.act(["switch", modelData.id]);
                                        }
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
