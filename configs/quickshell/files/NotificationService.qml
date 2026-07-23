import Quickshell
import Quickshell.Services.Notifications
import Quickshell.Wayland
import Quickshell.Widgets
import QtQuick
import QtQuick.Layouts

Scope {
    id: root

    readonly property int popupWidth: 380

    function accentColor(urgency) {
        if (urgency === NotificationUrgency.Critical)
            return "#d66b6b";
        if (urgency === NotificationUrgency.Low)
            return "#7f8999";
        return "#5f8fbd";
    }

    NotificationServer {
        id: notificationServer

        keepOnReload: false
        bodySupported: true
        bodyMarkupSupported: true
        actionsSupported: true
        imageSupported: true

        onNotification: notification => {
            notification.tracked = true;
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Component {
            PanelWindow {
                id: notificationWindow

                required property var modelData

                screen: modelData
                visible: notificationServer.trackedNotifications.values.length > 0

                anchors {
                    top: true
                    right: true
                }

                margins {
                    top: 44
                    right: 12
                }

                implicitWidth: root.popupWidth
                implicitHeight: notificationStack.implicitHeight
                color: "transparent"

                WlrLayershell.namespace: "quickshell-notifications-" + modelData.name
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.exclusionMode: ExclusionMode.Ignore

                Column {
                    id: notificationStack

                    width: parent.width
                    spacing: 8

                    Repeater {
                        model: notificationServer.trackedNotifications

                        delegate: Rectangle {
                            id: notificationCard

                            required property var modelData

                            readonly property var notification: modelData
                            readonly property color accent: root.accentColor(notification.urgency)
                            readonly property int defaultDuration: notification.urgency === NotificationUrgency.Critical ? 10000 : 5000

                            width: notificationStack.width
                            implicitHeight: content.implicitHeight + 24
                            radius: 8
                            color: notificationHover.hovered ? "#1b202a" : "#151922"
                            border.color: "#343d4f"
                            border.width: 1

                            Rectangle {
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                }

                                width: 4
                                radius: 2
                                color: notificationCard.accent
                            }

                            RowLayout {
                                id: content

                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 16
                                    rightMargin: 12
                                }

                                spacing: 12

                                Rectangle {
                                    Layout.preferredWidth: 40
                                    Layout.preferredHeight: 40
                                    Layout.alignment: Qt.AlignTop
                                    radius: 8
                                    color: "#202633"
                                    visible: notification.appIcon !== "" || notification.image !== "" || notification.appName !== ""

                                    IconImage {
                                        anchors {
                                            fill: parent
                                            margins: 7
                                        }

                                        visible: source !== ""
                                        source: notification.image !== "" ? notification.image : notification.appIcon
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        visible: notification.image === "" && notification.appIcon === ""
                                        color: notificationCard.accent
                                        font {
                                            pixelSize: 16
                                            bold: true
                                        }
                                        text: notification.appName !== "" ? notification.appName.charAt(0).toUpperCase() : "!"
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        Layout.fillWidth: true
                                        visible: notification.appName !== ""
                                        color: "#8f99a8"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        text: notification.appName
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        color: "#f0f0f0"
                                        font {
                                            pixelSize: 14
                                            bold: true
                                        }
                                        elide: Text.ElideRight
                                        text: notification.summary
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        visible: notification.body !== ""
                                        color: "#b9c0cc"
                                        font.pixelSize: 13
                                        text: notification.body
                                        textFormat: Text.StyledText
                                        wrapMode: Text.Wrap
                                        maximumLineCount: 4
                                        elide: Text.ElideRight
                                        onLinkActivated: link => Qt.openUrlExternally(link)
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        visible: notification.actions.length > 0
                                        spacing: 6

                                        Repeater {
                                            model: notification.actions

                                            delegate: Rectangle {
                                                id: actionButton

                                                required property var modelData

                                                width: actionLabel.implicitWidth + 18
                                                height: 28
                                                radius: 5
                                                color: actionMouse.containsMouse ? "#3d5a80" : "#2a3140"

                                                Text {
                                                    id: actionLabel

                                                    anchors.centerIn: parent
                                                    color: "#f0f0f0"
                                                    font.pixelSize: 12
                                                    text: modelData.text
                                                }

                                                MouseArea {
                                                    id: actionMouse

                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    onClicked: modelData.invoke()
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 26
                                    Layout.preferredHeight: 26
                                    Layout.alignment: Qt.AlignTop
                                    radius: 5
                                    color: closeMouse.containsMouse ? "#3a2530" : "transparent"

                                    Text {
                                        anchors.centerIn: parent
                                        color: closeMouse.containsMouse ? "#d66b6b" : "#7f8999"
                                        font.pixelSize: 16
                                        text: "×"
                                    }

                                    MouseArea {
                                        id: closeMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: notification.dismiss()
                                    }
                                }
                            }

                            HoverHandler {
                                id: notificationHover
                            }

                            Timer {
                                interval: notification.expireTimeout > 0
                                    ? notification.expireTimeout
                                    : notificationCard.defaultDuration
                                running: !notificationHover.hovered
                                repeat: false
                                onTriggered: notification.expire()
                            }
                        }
                    }
                }
            }
        }
    }
}
