import QtQuick
import QtQuick.Controls

Item {
    id: strip
    required property var sessionService
    property var notificationState: null
    readonly property var entries: sessionService.sessions
    readonly property real contentWidth: buttons.implicitWidth
    readonly property real maximumOffset: Math.max(0, contentWidth - width)
    property real scrollOffset: 0
    clip: true
    onMaximumOffsetChanged: scrollOffset = Math.max(0, Math.min(scrollOffset, maximumOffset))

    function initials(name) {
        return name.split(/[\s-]+/).filter(word => word.length > 0).slice(0, 3)
            .map(word => Array.from(word)[0]).join("").toLocaleUpperCase();
    }

    // No Flickable or scrollbar can grab/intercept button presses. Wheel-only
    // scrolling handles overflow without overlapping the visible 26px squares.
    WheelHandler {
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) {
            const pixels = event.pixelDelta.x || event.pixelDelta.y;
            const delta = pixels || (event.angleDelta.x || event.angleDelta.y) / 120 * 30;
            strip.scrollOffset = Math.max(0, Math.min(strip.scrollOffset - delta, strip.maximumOffset));
            event.accepted = true;
        }
    }
    Row {
        id: buttons
        x: -strip.scrollOffset
        y: 0
        spacing: 4
        Repeater {
            model: strip.entries
            delegate: Button {
                id: sessionCase
                required property var modelData
                readonly property string context: modelData.id
                objectName: "session-case-" + context
                readonly property bool current: strip.sessionService.visualContext === sessionCase.context
                readonly property bool pendingNotification: !sessionCase.current
                    && strip.notificationState !== null
                    && strip.notificationState.hasUnread(sessionCase.context) === true
                width: 26
                height: 26
                padding: 0
                topInset: 0
                bottomInset: 0
                leftInset: 0
                rightInset: 0
                hoverEnabled: true
                enabled: !strip.sessionService.busy
                background: Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: sessionCase.current ? "#3d5a80" : sessionCase.hovered ? "#343d4f" : "#1b202a"
                    border.width: sessionCase.pendingNotification ? 2 : 1
                    // Pending refreshes are normal during a switch, not notifications.
                    border.color: sessionCase.pendingNotification ? "#d66b6b" : "transparent"
                }
                contentItem: Text {
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 5
                    elide: Text.ElideRight
                    text: strip.initials(sessionCase.modelData.source.kind === "neutral" ? "Neutral" : sessionCase.modelData.source.project_name) + sessionCase.modelData.number
                    color: sessionCase.current ? "#ffffff" : "#b9c0cc"
                    font.pixelSize: 9
                }
                onClicked: strip.sessionService.act(["switch", sessionCase.modelData.id])
            }
        }
    }
}
