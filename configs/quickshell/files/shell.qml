//@ pragma UseQApplication

import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Services.UPower
import Quickshell.Services.SystemTray
import Quickshell.Wayland
import Quickshell.Widgets
import QtQuick

Scope {
    id: root

    NotificationService {}

    property bool controlCenterVisible: false
    property bool keybindsVisible: false
    property bool networkManagerVisible: false
    property bool wifiEnabled: false
    property bool networkBusy: false
    property string networkStatus: ""
    property string selectedSsid: ""
    property string selectedSecurity: ""
    property bool selectedConnected: false
    property var wifiNetworks: []
    property bool osdVisible: false
    property bool trayVisible: false
    property bool osdMuted: false
    property int osdValue: 0
    property string osdLabel: ""
    readonly property var controlRows: [
        ["Vol -", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"],
        ["Mute", "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"],
        ["Vol +", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"],
        ["Bright -", "brightnessctl set 5%-"],
        ["Bright +", "brightnessctl set +5%"],
        ["Lock", "hyprlock"],
        ["Network", ""],
        ["Logout", "hyprctl dispatch 'hl.dsp.exit()'"],
        ["Shutdown", "systemctl poweroff"],
        ["Reboot", "systemctl reboot"]
    ]
    readonly property var keybindRows: [
        ["SUPER+Enter", "Terminal"],
        ["SUPER+E", "Yazi home"],
        ["SUPER+P", "Projects"],
        ["SUPER+D", "Applications"],
        ["SUPER+B", "Browser"],
        ["SUPER+O", "Control center"],
        ["SUPER+H", "Keybinds"],
        ["SUPER+L", "Lock screen"],
        ["SUPER+Q", "Close window"],
        ["SUPER+W", "Toggle floating"],
        ["SUPER+F", "Fullscreen"],
        ["SUPER+Tab", "Next workspace"],
        ["SUPER+Shift+Tab", "Previous workspace"],
        ["SUPER+1..0", "Focus workspace"],
        ["SUPER+Shift+1..0", "Move window to workspace"],
        ["Print", "Region screenshot"],
        ["Shift+Print", "Window screenshot"],
        ["Ctrl+Print", "Full screenshot"]
    ]

    function parseNmcliLine(line) {
        const fields = [];
        let field = "";
        let escaped = false;

        for (let i = 0; i < line.length; ++i) {
            const character = line[i];
            if (escaped) {
                field += character;
                escaped = false;
            } else if (character === "\\") {
                escaped = true;
            } else if (character === ":") {
                fields.push(field);
                field = "";
            } else {
                field += character;
            }
        }

        fields.push(field);
        return fields;
    }

    function refreshNetworks() {
        if (networkBusy)
            return;

        networkStatus = "Scanning...";
        wifiStateProcess.running = true;
        wifiScanProcess.running = true;
    }

    function selectNetwork(network) {
        selectedSsid = network.ssid;
        selectedSecurity = network.security;
        selectedConnected = network.connected;
        networkPassword.text = "";
    }

    function runNetworkAction() {
        if (!selectedSsid || networkBusy)
            return;

        networkBusy = true;
        networkStatus = selectedConnected ? "Disconnecting..." : "Connecting...";
        networkActionProcess.ssid = selectedSsid;
        networkActionProcess.password = networkPassword.text;
        networkActionProcess.disconnect = selectedConnected;
        networkActionProcess.running = true;
    }

    function showOsd(label, value, muted) {
        osdLabel = label;
        osdValue = Math.max(0, Math.min(100, value));
        osdMuted = muted;
        osdVisible = true;
        osdTimer.restart();
    }

    function refreshVolumeOsd() {
        if (!volumeStateProcess.running)
            volumeStateProcess.running = true;
    }

    function refreshBrightnessOsd() {
        if (!brightnessStateProcess.running)
            brightnessStateProcess.running = true;
    }

    Timer {
        id: osdTimer

        interval: 1600
        onTriggered: root.osdVisible = false
    }

    Process {
        id: volumeStateProcess

        command: ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]
        stdout: StdioCollector {
            onStreamFinished: {
                const match = text.match(/Volume:\s*([0-9.]+)/);
                if (match)
                    root.showOsd("Volume", Math.round(parseFloat(match[1]) * 100), text.indexOf("[MUTED]") !== -1);
            }
        }
    }

    Process {
        id: brightnessStateProcess

        command: ["brightnessctl", "-m"]
        stdout: StdioCollector {
            onStreamFinished: {
                const match = text.match(/,([0-9]+)%,/);
                if (match)
                    root.showOsd("Brightness", parseInt(match[1]), false);
            }
        }
    }

    Process {
        id: wifiStateProcess

        command: ["nmcli", "radio", "wifi"]
        stdout: StdioCollector {
            onStreamFinished: root.wifiEnabled = text.trim() === "enabled"
        }
    }

    Process {
        id: wifiScanProcess

        command: ["nmcli", "-t", "-f", "IN-USE,SSID,SECURITY,SIGNAL", "device", "wifi", "list", "--rescan", "yes"]
        stdout: StdioCollector {
            onStreamFinished: {
                const networks = {};
                const lines = text.trim().split("\n");

                for (let i = 0; i < lines.length; ++i) {
                    const fields = root.parseNmcliLine(lines[i]);
                    if (fields.length !== 4 || !fields[1])
                        continue;

                    const network = {
                        "connected": fields[0] === "*",
                        "ssid": fields[1],
                        "security": fields[2] || "Open",
                        "signal": parseInt(fields[3]) || 0
                    };
                    const previous = networks[network.ssid];
                    if (!previous || network.connected || network.signal > previous.signal)
                        networks[network.ssid] = network;
                }

                root.wifiNetworks = Object.values(networks).sort((left, right) => {
                    if (left.connected !== right.connected)
                        return left.connected ? -1 : 1;
                    return right.signal - left.signal;
                });
                root.networkStatus = root.wifiNetworks.length > 0 ? "" : "No networks found";
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    root.networkStatus = text.trim().split("\n")[0];
            }
        }
    }

    Process {
        id: wifiToggleProcess

        command: ["nmcli", "radio", "wifi", root.wifiEnabled ? "off" : "on"]
        onExited: {
            root.refreshNetworks();
        }
    }

    Process {
        id: networkActionProcess

        property string ssid: ""
        property string password: ""
        property bool disconnect: false

        command: {
            if (disconnect)
                return ["nmcli", "connection", "down", "id", ssid];

            const arguments = ["nmcli", "device", "wifi", "connect", ssid];
            if (password)
                arguments.push("password", password);
            return arguments;
        }
        onExited: function(exitCode, exitStatus) {
            root.networkBusy = false;
            root.networkStatus = exitCode === 0 ? "Connection updated" : networkActionError.text.trim().split("\n")[0];
            root.selectedSsid = "";
            root.selectedConnected = false;
            root.refreshNetworks();
        }
        stderr: StdioCollector {
            id: networkActionError
        }
    }

    IpcHandler {
        target: "controlCenter"

        function toggle(): void {
            root.controlCenterVisible = !root.controlCenterVisible;
        }

        function show(): void {
            root.controlCenterVisible = true;
        }

        function hide(): void {
            root.controlCenterVisible = false;
        }
    }

    IpcHandler {
        target: "keybinds"

        function toggle(): void {
            root.keybindsVisible = !root.keybindsVisible;
        }

        function show(): void {
            root.keybindsVisible = true;
        }

        function hide(): void {
            root.keybindsVisible = false;
        }
    }

    IpcHandler {
        target: "networkManager"

        function toggle(): void {
            root.networkManagerVisible = !root.networkManagerVisible;
            if (root.networkManagerVisible)
                root.refreshNetworks();
        }

        function show(): void {
            root.networkManagerVisible = true;
            root.refreshNetworks();
        }

        function hide(): void {
            root.networkManagerVisible = false;
        }
    }

    IpcHandler {
        target: "osd"

        function volume(): void {
            root.refreshVolumeOsd();
        }

        function brightness(): void {
            root.refreshBrightnessOsd();
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Component {
            PanelWindow {
                id: trayPopup

                required property var modelData

                screen: modelData
                visible: root.trayVisible
                anchors {
                    top: true
                    right: true
                }
                margins {
                    top: 40
                    right: 156
                }
                implicitWidth: 216
                implicitHeight: Math.max(64, 24 + Math.ceil(SystemTray.items.values.length / 4) * 46)
                color: "transparent"

                WlrLayershell.namespace: "quickshell-tray-" + modelData.name
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.exclusionMode: ExclusionMode.Ignore

                Rectangle {
                    anchors.fill: parent
                    radius: 8
                    color: "#151922"
                    border.color: "#343d4f"
                    border.width: 1

                    Grid {
                        anchors {
                            top: parent.top
                            left: parent.left
                            margins: 12
                        }
                        columns: 4
                        spacing: 4

                        Repeater {
                            model: SystemTray.items

                            delegate: Rectangle {
                                id: trayEntry

                                required property var modelData

                                width: 44
                                height: 42
                                radius: 6
                                color: trayEntryMouse.containsMouse ? "#283142" : "transparent"

                                IconImage {
                                    anchors.centerIn: parent
                                    width: 24
                                    height: 24
                                    source: modelData.icon
                                }

                                QsMenuAnchor {
                                    id: trayMenu

                                    menu: modelData.menu
                                    anchor.window: trayPopup
                                    anchor.item: trayEntry
                                    anchor.edges: Edges.Bottom
                                    anchor.gravity: Edges.Bottom
                                }

                                MouseArea {
                                    id: trayEntryMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                                    onClicked: mouse => {
                                        if (mouse.button === Qt.RightButton && modelData.hasMenu) {
                                            trayMenu.open();
                                        } else if (mouse.button === Qt.MiddleButton) {
                                            modelData.secondaryActivate();
                                        } else if (mouse.button === Qt.LeftButton) {
                                            if (modelData.onlyMenu && modelData.hasMenu)
                                                trayMenu.open();
                                            else {
                                                modelData.activate();
                                                root.trayVisible = false;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: SystemTray.items.values.length === 0
                        color: "#7f8999"
                        font.pixelSize: 13
                        text: "No background applications"
                    }
                }
            }
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Component {
            PanelWindow {
                required property var modelData

                screen: modelData
                visible: root.osdVisible
                anchors {
                    bottom: true
                }
                margins.bottom: 72
                implicitWidth: 300
                implicitHeight: 76
                color: "transparent"
                mask: Region {}

                WlrLayershell.namespace: "quickshell-osd-" + modelData.name
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.exclusionMode: ExclusionMode.Ignore

                Rectangle {
                    anchors.fill: parent
                    radius: 8
                    color: "#151922"
                    border.color: "#343d4f"
                    border.width: 1

                    Text {
                        anchors {
                            top: parent.top
                            left: parent.left
                            topMargin: 12
                            leftMargin: 14
                        }
                        color: "#f0f0f0"
                        font.pixelSize: 14
                        text: root.osdMuted ? "Muted" : root.osdLabel
                    }

                    Text {
                        anchors {
                            top: parent.top
                            right: parent.right
                            topMargin: 12
                            rightMargin: 14
                        }
                        color: root.osdMuted ? "#d66b6b" : "#b9c0cc"
                        font.pixelSize: 14
                        text: root.osdValue + "%"
                    }

                    Rectangle {
                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                            leftMargin: 14
                            rightMargin: 14
                            bottomMargin: 14
                        }
                        height: 8
                        radius: 4
                        color: "#2a3140"

                        Rectangle {
                            width: parent.width * root.osdValue / 100
                            height: parent.height
                            radius: 4
                            color: root.osdMuted ? "#7f8999" : root.osdLabel === "Brightness" ? "#d2a84a" : "#5f8fbd"
                        }
                    }
                }
            }
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Component {
            PanelWindow {
                required property var modelData

                screen: modelData

                anchors {
                    top: true
                    left: true
                    right: true
                }

                implicitHeight: 32

                Rectangle {
                    anchors.fill: parent
                    color: "#111318"

                    Rectangle {
                        width: 28
                        height: 24

                        anchors {
                            right: battery.left
                            rightMargin: 8
                            verticalCenter: parent.verticalCenter
                        }

                        radius: 4
                        color: trayButtonMouse.containsMouse ? "#2a3140" : "#1b202a"
                        opacity: SystemTray.items.values.length > 0 ? 1 : 0.55

                        Text {
                            anchors.centerIn: parent
                            color: "#e7e7e7"
                            font.pixelSize: 13
                            text: root.trayVisible ? "^" : "v"
                        }

                        MouseArea {
                            id: trayButtonMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.trayVisible = !root.trayVisible
                        }
                    }

                    Rectangle {
                        id: battery

                        readonly property var device: UPower.displayDevice.isPresent
                            ? UPower.displayDevice
                            : UPower.devices.values.find(candidate => candidate.isLaptopBattery) || null
                        readonly property bool available: device && device.isPresent
                        readonly property int percentage: available ? Math.round(device.percentage * 100) : 0
                        readonly property bool charging: device && device.state === UPowerDeviceState.Charging

                        width: 76
                        height: 24

                        anchors {
                            right: power.left
                            rightMargin: 8
                            verticalCenter: parent.verticalCenter
                        }

                        radius: 4
                        color: "#1b202a"

                        Text {
                            anchors.centerIn: parent
                            color: battery.available && battery.percentage <= 15 && !battery.charging ? "#d66b6b" : battery.charging ? "#8fc5a3" : "#e7e7e7"
                            font.pixelSize: 13
                            text: battery.available ? (battery.charging ? "+ " : "") + battery.percentage + "%" : "--%"
                        }
                    }

                    Text {
                        anchors {
                            left: parent.left
                            leftMargin: 12
                            verticalCenter: parent.verticalCenter
                        }

                        color: "#e7e7e7"
                        font.pixelSize: 13
                        text: "Session: default"
                    }

                    Row {
                        anchors.centerIn: parent
                        spacing: 6

                        Repeater {
                            model: Hyprland.workspaces

                            delegate: Rectangle {
                                required property var modelData

                                width: Math.max(28, workspaceLabel.implicitWidth + 14)
                                height: 22
                                radius: 4
                                color: modelData.focused ? "#3d5a80" : workspaceMouseArea.containsMouse ? "#2a3140" : "#1b202a"
                                border.color: modelData.urgent ? "#d66b6b" : modelData.active ? "#6f7f95" : "transparent"
                                border.width: modelData.urgent || modelData.active ? 1 : 0

                                Text {
                                    id: workspaceLabel

                                    anchors.centerIn: parent
                                    color: modelData.focused ? "#ffffff" : "#b9c0cc"
                                    font.pixelSize: 12
                                    text: modelData.name
                                }

                                MouseArea {
                                    id: workspaceMouseArea

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: modelData.activate()
                                }
                            }
                        }
                    }

                    Text {
                        id: clock

                        anchors {
                            right: parent.right
                            rightMargin: 12
                            verticalCenter: parent.verticalCenter
                        }

                        color: "#e7e7e7"
                        font.pixelSize: 13

                        function updateClock() {
                            const now = new Date();
                            text = now.toLocaleTimeString(Qt.locale(), "HH:mm");
                        }

                        Component.onCompleted: updateClock()

                        Timer {
                            interval: 1000
                            running: true
                            repeat: true
                            onTriggered: clock.updateClock()
                        }
                    }

                    Rectangle {
                        id: power

                        width: 64
                        height: 24

                        anchors {
                            right: clock.left
                            rightMargin: 12
                            verticalCenter: parent.verticalCenter
                        }

                        radius: 4
                        color: powerMouseArea.containsMouse ? "#2a3140" : "#1b202a"

                        Text {
                            anchors.centerIn: parent
                            color: "#e7e7e7"
                            font.pixelSize: 13
                            text: "Power"
                        }

                        MouseArea {
                            id: powerMouseArea

                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.controlCenterVisible = !root.controlCenterVisible
                        }
                    }
                }
            }
        }
    }

    FloatingWindow {
        id: networkManager

        visible: root.networkManagerVisible
        implicitWidth: 520
        implicitHeight: 620
        color: "transparent"
        onVisibleChanged: {
            if (visible)
                root.refreshNetworks();
        }

        Rectangle {
            anchors.fill: parent
            radius: 8
            color: "#151922"
            border.color: "#2b3342"
            border.width: 1

            Text {
                anchors {
                    top: parent.top
                    left: parent.left
                    margins: 16
                }
                color: "#f0f0f0"
                font.pixelSize: 18
                text: "Network Manager"
            }

            Row {
                anchors {
                    top: parent.top
                    right: parent.right
                    margins: 12
                }
                spacing: 8

                Rectangle {
                    width: 88
                    height: 32
                    radius: 5
                    color: wifiToggleMouse.containsMouse ? "#2a3140" : "#202633"
                    border.color: root.wifiEnabled ? "#5f8f72" : "#7f8999"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        color: "#f0f0f0"
                        font.pixelSize: 13
                        text: root.wifiEnabled ? "Wi-Fi on" : "Wi-Fi off"
                    }

                    MouseArea {
                        id: wifiToggleMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            if (!wifiToggleProcess.running)
                                wifiToggleProcess.running = true;
                        }
                    }
                }

                Rectangle {
                    width: 72
                    height: 32
                    radius: 5
                    color: refreshNetworkMouse.containsMouse ? "#2a3140" : "#202633"
                    border.color: "#343d4f"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        color: "#f0f0f0"
                        font.pixelSize: 13
                        text: "Refresh"
                    }

                    MouseArea {
                        id: refreshNetworkMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.refreshNetworks()
                    }
                }

                Rectangle {
                    width: 32
                    height: 32
                    radius: 5
                    color: closeNetworkMouse.containsMouse ? "#2a3140" : "#202633"

                    Text {
                        anchors.centerIn: parent
                        color: "#f0f0f0"
                        font.pixelSize: 16
                        text: "X"
                    }

                    MouseArea {
                        id: closeNetworkMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.networkManagerVisible = false
                    }
                }
            }

            Text {
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    topMargin: 58
                    leftMargin: 16
                    rightMargin: 16
                }
                color: root.networkStatus.indexOf("Error") === 0 ? "#d66b6b" : "#9aa5b5"
                font.pixelSize: 12
                elide: Text.ElideRight
                text: root.networkStatus
            }

            ListView {
                id: networkList

                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    bottom: networkActions.top
                    topMargin: 82
                    leftMargin: 10
                    rightMargin: 10
                    bottomMargin: 12
                }
                clip: true
                spacing: 4
                model: ScriptModel {
                    values: root.wifiNetworks
                }

                delegate: Rectangle {
                    required property var modelData

                    width: networkList.width
                    height: 52
                    radius: 6
                    color: root.selectedSsid === modelData.ssid || networkMouse.containsMouse ? "#283142" : "transparent"
                    border.color: modelData.connected ? "#5f8f72" : "transparent"
                    border.width: modelData.connected ? 1 : 0

                    Text {
                        anchors {
                            left: parent.left
                            leftMargin: 12
                            right: networkDetails.left
                            rightMargin: 12
                            verticalCenter: parent.verticalCenter
                        }
                        color: "#f0f0f0"
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        text: modelData.ssid
                    }

                    Text {
                        id: networkDetails
                        anchors {
                            right: parent.right
                            rightMargin: 12
                            verticalCenter: parent.verticalCenter
                        }
                        color: modelData.connected ? "#8fc5a3" : "#9aa5b5"
                        font.pixelSize: 12
                        text: (modelData.connected ? "Connected | " : "") + modelData.security + " | " + modelData.signal + "%"
                    }

                    MouseArea {
                        id: networkMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.selectNetwork(modelData)
                    }
                }
            }

            Rectangle {
                id: networkActions

                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    margins: 12
                }
                height: 92
                radius: 6
                color: "#202633"
                border.color: "#343d4f"
                border.width: 1

                Text {
                    anchors {
                        top: parent.top
                        left: parent.left
                        margins: 12
                    }
                    color: "#f0f0f0"
                    font.pixelSize: 13
                    text: root.selectedSsid || "Select a network"
                }

                TextInput {
                    id: networkPassword

                    anchors {
                        left: parent.left
                        right: networkActionButton.left
                        bottom: parent.bottom
                        leftMargin: 12
                        rightMargin: 10
                        bottomMargin: 10
                    }
                    height: 32
                    enabled: root.selectedSsid !== "" && !root.selectedConnected
                    visible: enabled && root.selectedSecurity !== "Open" && root.selectedSecurity !== "--"
                    color: "#f0f0f0"
                    font.pixelSize: 14
                    echoMode: TextInput.Password
                    clip: true
                    Keys.onReturnPressed: root.runNetworkAction()

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -6
                        z: -1
                        radius: 5
                        color: "#151922"
                        border.color: "#343d4f"
                        border.width: 1
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        color: "#7f8999"
                        font.pixelSize: 13
                        text: "Password"
                        visible: networkPassword.text.length === 0
                    }
                }

                Rectangle {
                    id: networkActionButton

                    anchors {
                        right: parent.right
                        bottom: parent.bottom
                        margins: 10
                    }
                    width: 104
                    height: 36
                    radius: 5
                    color: networkActionMouse.containsMouse && root.selectedSsid ? "#3d5a80" : "#2a3140"
                    opacity: root.selectedSsid && !root.networkBusy ? 1 : 0.5

                    Text {
                        anchors.centerIn: parent
                        color: "#ffffff"
                        font.pixelSize: 13
                        text: root.selectedConnected ? "Disconnect" : "Connect"
                    }

                    MouseArea {
                        id: networkActionMouse
                        anchors.fill: parent
                        enabled: root.selectedSsid !== "" && !root.networkBusy
                        hoverEnabled: true
                        onClicked: root.runNetworkAction()
                    }
                }
            }
        }
    }

    FloatingWindow {
        id: controlCenter

        visible: root.controlCenterVisible
        implicitWidth: 360
        implicitHeight: 270
        color: "transparent"

        Rectangle {
            anchors.fill: parent
            radius: 8
            color: "#151922"
            border.color: "#2b3342"
            border.width: 1

            Text {
                anchors {
                    top: parent.top
                    left: parent.left
                    margins: 16
                }

                color: "#f0f0f0"
                font.pixelSize: 16
                text: "Control center"
            }

            Grid {
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    topMargin: 56
                    leftMargin: 16
                    rightMargin: 16
                }

                columns: 3
                spacing: 8

                Repeater {
                    model: root.controlRows

                    delegate: Rectangle {
                        required property var modelData

                        Process {
                            id: controlProcess

                            command: ["sh", "-c", modelData[1]]
                            onExited: {
                                if (modelData[0].indexOf("Vol") === 0 || modelData[0] === "Mute")
                                    root.refreshVolumeOsd();
                                else if (modelData[0].indexOf("Bright") === 0)
                                    root.refreshBrightnessOsd();
                            }
                        }

                        width: 104
                        height: 38
                        radius: 6
                        color: controlMouseArea.containsMouse ? "#2a3140" : "#202633"
                        border.color: "#343d4f"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            color: "#f0f0f0"
                            font.pixelSize: 13
                            text: modelData[0]
                        }

                        MouseArea {
                            id: controlMouseArea

                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (modelData[0] === "Network") {
                                    root.controlCenterVisible = false;
                                    root.networkManagerVisible = true;
                                    root.refreshNetworks();
                                } else {
                                    controlProcess.running = true;
                                }
                            }
                        }
                    }
                }
            }

            Text {
                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    margins: 16
                }

                color: "#7f8999"
                font.pixelSize: 12
                elide: Text.ElideRight
                text: Hyprland.activeToplevel ? Hyprland.activeToplevel.title : ""
            }
        }
    }

    FloatingWindow {
        id: keybinds

        visible: root.keybindsVisible
        implicitWidth: 480
        implicitHeight: 560
        color: "transparent"

        Rectangle {
            anchors.fill: parent
            radius: 8
            color: "#151922"
            border.color: "#2b3342"
            border.width: 1

            Text {
                id: keybindsTitle

                anchors {
                    top: parent.top
                    left: parent.left
                    margins: 16
                }

                color: "#f0f0f0"
                font.pixelSize: 16
                text: "Keybinds"
            }

            ListView {
                anchors {
                    top: keybindsTitle.bottom
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    topMargin: 14
                    leftMargin: 16
                    rightMargin: 16
                    bottomMargin: 16
                }

                clip: true
                spacing: 4
                model: root.keybindRows

                delegate: Rectangle {
                    required property var modelData

                    width: parent ? parent.width : 448
                    height: 30
                    radius: 4
                    color: "#202633"

                    Text {
                        anchors {
                            left: parent.left
                            leftMargin: 10
                            verticalCenter: parent.verticalCenter
                        }

                        width: 150
                        color: "#f0f0f0"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        text: modelData[0]
                    }

                    Text {
                        anchors {
                            left: parent.left
                            leftMargin: 170
                            right: parent.right
                            rightMargin: 10
                            verticalCenter: parent.verticalCenter
                        }

                        color: "#b9c0cc"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        text: modelData[1]
                    }
                }
            }
        }
    }
}
