import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick

Scope {
    id: menu

    property bool menuVisible: false
    required property var sessionService
    readonly property var sessions: sessionService.sessions
    property var projects: []
    property string searchText: ""
    readonly property var filteredProjects: projects.filter(function(project) { return project.name.toLocaleLowerCase().includes(searchText.trim().toLocaleLowerCase()); })
    onFilteredProjectsChanged: normalizeSelection()
    readonly property string activeId: sessionService.activeId
    readonly property string activeName: sessionService.activeName
    property string status: ""
    property string pendingStop: ""
    property string selectedSection: "projects"
    property int selectedProject: 0
    property int selectedSession: 0
    property bool initialSelectionPending: false
    readonly property string binary: Quickshell.env("HOME") + "/.local/bin/session-manager"

    property bool startupMenuPending: false
    property bool startupMenuUsed: false

    Component.onCompleted: {
        refresh();
        startupMenuClaim.running = true;
    }

    function finishStartupClaim(exitCode, output, diagnostic) {
        if (exitCode !== 0) {
            status = diagnostic.trim().split("\n")[0] || "Startup menu claim failed";
            return;
        }
        try {
            const reply = JSON.parse(output);
            if (typeof reply.show !== "boolean")
                throw new Error("invalid startup menu claim");
            if (reply.show && !startupMenuUsed) {
                startupMenuPending = true;
                sessionService.invalidateContext(); // Discard pre-claim/in-flight status.
            }
        } catch (failure) {
            status = String(failure);
        }
    }

    function maybeShowStartupMenu() {
        if (!startupMenuPending)
            return;
        startupMenuPending = false;
        if (!startupMenuUsed && !menuVisible && !sessionService.busy
                && !sessionService.stale && sessionService.contextConfirmed
                && !activeId && !sessions.length && sessionService.displayedContext === "neutral")
            showMenu();
    }

    function refresh() {
        sessionService.refresh();
        if (!projectsProcess.running)
            projectsProcess.running = true;
    }

    function showMenu() {
        startupMenuUsed = true;
        startupMenuPending = false;
        menuVisible = true;
        pendingStop = "";
        initialSelectionPending = false;
        searchInput.text = "";
        selectedSection = "projects";
        selectedProject = 0;
        selectedSession = 0;
        initialSelectionPending = true;
        refresh();
        Qt.callLater(function() { menu.focusSelection(); });
    }

    function focusSelection() {
        if (!menuVisible)
            return;
        if (selectedSection === "sessions")
            menuRoot.forceActiveFocus();
        else
            searchInput.forceActiveFocus();
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
        const previousSection = selectedSection;
        selectedProject = Math.max(0, Math.min(selectedProject, filteredProjects.length - 1));
        selectedSession = Math.max(0, Math.min(selectedSession, sessions.length - 1));
        // A loading/empty source list must not steal focus from creation search.
        if (selectedSection === "sessions" && !sessions.length)
            selectedSection = "projects";
        if (menuVisible)
            Qt.callLater(function() {
                menu.ensureSelectedVisible();
                if (previousSection !== menu.selectedSection)
                    menu.focusSelection();
            });
    }

    function handleKey(event) {
        initialSelectionPending = false;
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            if (selectedSection === "projects" && sessions.length)
                selectedSection = "sessions";
            else if (selectedSection === "sessions" && projects.length)
                selectedSection = "projects";
            ensureSelectedVisible();
            focusSelection();
        } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
            const count = selectedSection === "projects" ? filteredProjects.length : sessions.length;
            if (count) {
                const step = event.key === Qt.Key_Down ? 1 : -1;
                if (selectedSection === "projects")
                    selectedProject = Math.max(0, Math.min(selectedProject + step, count - 1));
                else
                    selectedSession = Math.max(0, Math.min(selectedSession + step, count - 1));
                ensureSelectedVisible();
            }
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (selectedSection === "projects" && filteredProjects[selectedProject])
                act(startArguments(filteredProjects[selectedProject]));
            else if (selectedSection === "sessions" && sessions[selectedSession])
                act(["switch", sessions[selectedSession].id]);
        } else if (event.key === Qt.Key_Escape) {
            menuVisible = false;
        } else {
            return;
        }
        event.accepted = true;
    }

    function startArguments(row) {
        return row.source.kind === "neutral" ? ["start", "--neutral"] : ["start", "--project", row.source.project_name];
    }

    function act(argumentsList) {
        if (sessionService.busy)
            return;
        status = "Working...";
        sessionService.act(argumentsList);
    }

    Connections {
        target: menu.sessionService
        function onUpdated() {
            menu.maybeShowStartupMenu();
            if (menu.menuVisible && menu.initialSelectionPending) {
                menu.selectedSection = "projects";
                menu.initialSelectionPending = false;
                Qt.callLater(function() { menu.focusSelection(); });
            }
            menu.normalizeSelection();
        }
        function onActionFinished(success, message) {
            menu.status = message;
            if (success) {
                menu.pendingStop = "";
                menu.menuVisible = false;
                menu.refresh();
            }
        }
    }

    Process {
        id: startupMenuClaim
        command: [Quickshell.env("HOME") + "/.local/bin/session-startup", "--claim-menu"]
        stdout: StdioCollector { id: startupClaimOutput }
        stderr: StdioCollector { id: startupClaimError }
        onExited: function(exitCode) {
            menu.finishStartupClaim(exitCode, startupClaimOutput.text, startupClaimError.text);
        }
    }

    Process {
        id: projectsProcess
        command: [menu.binary, "--json", "source", "list"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (!Array.isArray(result.sources) || !result.sources.every(row => menu.sessionService.validSource(row.source)))
                        throw new Error(result.code || "invalid source response");
                    menu.projects = result.sources;
                } catch (error) {
                    menu.status = "Unable to read launch sources: " + error;
                }
            }
        }
    }

    IpcHandler {
        target: "sessions"
        function nextAttention(): void { menu.sessionService.nextAttention(); }
        function toggle(): void { menu.toggle(); }
        function show(): void { menu.showMenu(); }
        function hide(): void { menu.menuVisible = false; }
    }

    PanelWindow {
        visible: menu.menuVisible
        screen: Quickshell.screens[0]
        anchors { top: true }
        implicitWidth: 460
        implicitHeight: 660
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
                    text: "Type to filter projects · ↑↓ select · Tab list · Enter open · Esc close"
                    color: "#aab3c4"
                    font.pixelSize: 12
                    width: parent.width
                }
                Text {
                    text: menu.status || menu.sessionService.error
                    color: "#d9a26b"
                    font.pixelSize: 12
                    width: parent.width
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
                Text { text: "Start a session"; color: "#aab3c4"; font.pixelSize: 13 }
                Rectangle {
                    width: parent.width
                    height: 30
                    radius: 4

                    color: "#202633"
                    border.color: searchInput.activeFocus ? "#506e93" : "#343d4f"
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Search projects..."
                        color: "#7f8999"
                        visible: !searchInput.text.length
                    }
                    TextInput {
                        id: searchInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: "#f0f0f0"
                        font.pixelSize: 14
                        clip: true
                        selectByMouse: true
                        onTextChanged: {
                            menu.initialSelectionPending = false;
                            menu.searchText = text;
                            menu.selectedProject = 0;
                            Qt.callLater(function() { projectList.contentY = 0; });
                        }
                        onActiveFocusChanged: {
                            if (activeFocus && menu.menuVisible)
                                menu.selectedSection = "projects";
                        }
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: function(event) { menu.handleKey(event); }
                    }
                }
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
                        Text {
                            text: menu.searchText ? "No matching project" : "No projects"
                            color: "#7f8999"
                            height: visible ? 30 : 0
                            visible: !menu.filteredProjects.length
                        }
                        Repeater {
                            model: menu.filteredProjects
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
                                    text: "+ " + modelData.name + (modelData.source.kind === "neutral" ? " (built-in)" : " (project)")
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
                                        menu.act(menu.startArguments(modelData));
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
                    text: "Deselect session — return to the unowned desktop"
                    MouseArea {
                        anchors.fill: parent
                        onClicked: menu.act(["deactivate"])
                    }
                    wrapMode: Text.Wrap
                    color: "#7f8999"
                    font.pixelSize: 12
                }
            }
        }
    }
}
