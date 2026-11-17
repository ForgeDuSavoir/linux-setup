import Quickshell
import Quickshell.Services.Notifications
import QtQuick
import QtQml.Models
import "NotificationPolicy.js" as Policy

// The existing server/history moved here so policy can be tested without windows.
// NotificationService inherits this store; it does not create a second server.
Scope {
    id: store
    required property var sessionService
    readonly property int historyLimit: 100
    property var history: []
    property int serial: 0
    signal received(double notificationId)
    property var hovered: ({})
    readonly property var sessionList: sessionService ? sessionService.sessions : []
    readonly property bool sessionsKnown: !!sessionService && !sessionService.stale
    readonly property string currentContext: sessionsKnown && sessionService.contextConfirmed
        ? (sessionService.displayedContext === "neutral" ? "neutral" : "session:" + sessionService.displayedContext) : "unknown"
    readonly property var unread: Policy.unreadContexts(history)
    readonly property var trackedNotifications: server.trackedNotifications
    readonly property var popupNotifications: server.trackedNotifications.values.filter(notification =>
        history.some(entry => entry.id === notification.id && entry.live && entry.popup
            && (!Policy.scoped(entry) || entry.context === currentContext)))

    function hasUnread(context) {
        const target = context === "neutral" ? context : "session:" + context;
        // A badge is owned by an exact scoped context, never by a global
        // notification or the truthiness of a shared attention object.
        if (target === currentContext)
            return false;
        return history.some(entry => entry.unread === true && Policy.scoped(entry)
            && entry.context === target);
    }

    function receive(notification) {
        const hint = notification.hints["x-agora-context"];
        serial++;
        history = Policy.receive(history, {
            id: notification.id, key: String(notification.id) + ":" + serial,
            timestamp: Date.now(), appName: notification.appName,
            summary: notification.summary, body: notification.body, urgency: notification.urgency,
            hint: hint
        }, sessionList, currentContext, sessionsKnown, historyLimit);
        notification.tracked = true;
        received(notification.id);
    }

    function synchronize() {
        history = Policy.reconcile(history, sessionList, currentContext, sessionsKnown);
    }

    function clearHistory() { history = []; }
    function removeHistory(key) { history = Policy.remove(history, key); }
    function closed(id) { history = Policy.close(history, id); }
    function setHovered(id, value) {
        const next = Object.assign({}, hovered);
        if (value) next[String(id)] = true;
        else delete next[String(id)];
        hovered = next;
    }
    function contextLabel(entry) {
        if (entry.context === "global") return "Global";
        if (entry.context === "neutral") return "Unowned desktop (no session)";
        if (entry.context === "unknown") return "Unknown / global";
        const session = sessionList.find(item => "session:" + item.id === entry.context);
        return session ? session.name : "Stopped / unknown session";
    }

    Connections {
        target: store.sessionService || null
        function onUpdated() { store.synchronize(); }
        function onContextConfirmedChanged() { if (!store.sessionService.contextConfirmed) store.synchronize(); }
        function onStaleChanged() { if (store.sessionService.stale) store.synchronize(); }
    }

    NotificationServer {
        id: server
        keepOnReload: false
        bodySupported: true
        bodyMarkupSupported: true
        actionsSupported: true
        imageSupported: true
        extraHints: ["x-agora-context"]
        onNotification: notification => store.receive(notification)
    }

    // Lifetime is independent of visible cards, screens and history retention.
    // Hiding a popup never calls dismiss/expire. Suppressed objects still expire.
    Instantiator {
        model: server.trackedNotifications
        delegate: Scope {
            id: lifetime
            required property var modelData
            readonly property var notification: modelData
            Connections {
                target: lifetime.notification
                function onSummaryChanged() { replacement.restart(); }
                function onBodyChanged() { replacement.restart(); }
                function onAppNameChanged() { replacement.restart(); }
                function onHintsChanged() { replacement.restart(); }
                function onUrgencyChanged() { replacement.restart(); }
                function onActionsChanged() { replacement.restart(); }
                function onExpireTimeoutChanged() { replacement.restart(); }
                function onClosed(reason) {
                    replacement.stop();
                    store.closed(lifetime.notification.id);
                    store.setHovered(lifetime.notification.id, false);
                }
            }
            Timer {
                id: replacement
                interval: 0
                repeat: false
                onTriggered: {
                    if (lifetime.notification && lifetime.notification.tracked)
                        store.receive(lifetime.notification);
                }
            }
            Connections {
                target: store
                function onReceived(notificationId) {
                    if (notificationId === lifetime.notification.id) {
                        expiry.restart();
                        ceiling.restart();
                    }
                }
            }
            Timer {
                id: expiry
                interval: lifetime.notification.expireTimeout > 0
                    ? Math.min(lifetime.notification.expireTimeout, 300000)
                    : (lifetime.notification.urgency === NotificationUrgency.Critical ? 10000 : 5000)
                running: !store.hovered[String(lifetime.notification.id)]
                repeat: false
                onTriggered: lifetime.notification.expire()
            }
            Timer {
                id: ceiling
                interval: 300000
                running: true
                repeat: false
                onTriggered: lifetime.notification.expire()
            }
        }
    }
}
