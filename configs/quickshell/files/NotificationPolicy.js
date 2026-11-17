// Pure downstream presentation policy. No core mutation, IO or application launch.
function attribution(hint, sessions, known) {
    if (hint === "global" || hint === "neutral")
        return { context: hint, source: "explicit", orphan: false };
    if (typeof hint === "string" && /^session:[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(hint)) {
        return { context: hint, source: "explicit", orphan: known && !sessions.some(s => "session:" + s.id === hint) };
    }
    return { context: "unknown", source: hint === undefined ? "unattributed" : "invalid-hint", orphan: false };
}

function scoped(entry) {
    return !entry.orphan && (entry.context === "neutral" || entry.context.indexOf("session:") === 0);
}

function receive(history, data, sessions, current, known, limit) {
    const attr = attribution(data.hint, sessions, known);
    const entry = Object.assign({}, data, attr, {
        live: true,
        unread: false,
        popup: false
    });
    delete entry.hint;
    entry.unread = scoped(entry) && entry.context !== current;
    entry.popup = !scoped(entry) || entry.context === current;
    // A replacement is one history entry and replaces the previous attention.
    return [entry].concat(history.filter(item => item.id !== data.id)).slice(0, limit);
}

function reconcile(history, sessions, current, known) {
    let changed = false;
    const result = history.map(item => {
        const entry = Object.assign({}, item);
        if (entry.context.indexOf("session:") === 0 && known) {
            const orphan = !sessions.some(s => "session:" + s.id === entry.context);
            if (orphan && !entry.orphan && entry.live)
                entry.popup = true; // A live orphan is surfaced globally once.
            entry.orphan = orphan;
        }
        if (!scoped(entry)) {
            entry.unread = false;
        } else if (entry.context === current) {
            entry.unread = false; // Never replay a suppressed popup on entry.
        } else if (current !== "unknown" && entry.live && entry.popup) {
            entry.popup = false;
            entry.unread = true;
        }
        if (entry.popup !== item.popup || entry.unread !== item.unread || entry.orphan !== item.orphan) {
            changed = true;
            return entry;
        }
        return item;
    });
    return changed ? result : history;
}

function close(history, id) {
    return history.map(item => item.id === id ? Object.assign({}, item, { live: false, popup: false }) : item);
}

function remove(history, key) {
    return history.filter(item => item.key !== key);
}

function unreadContexts(history) {
    const result = {};
    for (const item of history)
        if (item.unread && scoped(item))
            result[item.context] = true;
    return result;
}
