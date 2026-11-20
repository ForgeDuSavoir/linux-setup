use crate::{
    native,
    state::{self, MAX_ID, State},
    storage::{LockedStore, Store},
    workspace::Action,
};
use serde_json::{Value, json};
use std::{collections::BTreeSet, path::PathBuf};
pub(crate) struct Temp(pub PathBuf);
impl Temp {
    pub fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "agora-r1-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        Self(root)
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
pub(crate) fn state() -> State {
    State::from_value(
        json!({"version":3,"order":[1,2],"owners":{"1":"A","2":"B"},"preferred":{},"next_id":3}),
    )
    .unwrap()
}
#[test]
fn empty_projection() {
    let s = state::project(None, &BTreeSet::new()).unwrap();
    assert_eq!(s.next_id, 1);
    assert!(s.order.is_empty());
}
#[test]
fn legacy_projection_is_pure() {
    let raw = json!({"version":2,"owners":{"1":"A","2":"B","3":"C"},"last":{"1":2,"3":2},"preferred":{"A":1,"B":2,"C":3},"origins":{"a":1}});
    let before = raw.clone();
    let s = state::project(Some(raw.clone()), &BTreeSet::from([1, 2, 3])).unwrap();
    assert_eq!(s.order, [1, 2, 3, 6]);
    assert_eq!(s.preferred["C"], 6);
    assert_eq!(raw, before);
}
#[test]
fn rejects_invalid_shapes() {
    for key in ["order", "owners", "preferred", "next_id"] {
        let mut v = serde_json::to_value(state()).unwrap();
        v.as_object_mut().unwrap().remove(key);
        assert!(State::from_value(v).is_err());
    }
}
#[test]
fn rejects_duplicate_ids() {
    let mut s = state();
    s.order.push(1);
    assert!(s.validate().is_err());
}
#[test]
fn rejects_bad_preference() {
    let mut s = state();
    s.preferred.insert("B".into(), 1);
    assert!(s.validate().is_err());
}
#[test]
fn rejects_boolean_integer() {
    let mut v = serde_json::to_value(state()).unwrap();
    v["next_id"] = json!(true);
    assert!(State::from_value(v).is_err());
}
#[test]
fn rejects_negative_and_limit_ids() {
    for id in [-1, 0, MAX_ID + 1] {
        let mut s = state();
        s.order[0] = id;
        assert!(s.validate().is_err());
    }
}
#[test]
fn accepts_exhausted_next_without_allocating() {
    let mut s = state();
    s.next_id = MAX_ID + 1;
    assert!(s.validate().is_ok());
}
#[test]
fn retires_origins_preserves_extensions() {
    let mut v = serde_json::to_value(state()).unwrap();
    v["origins"] = json!({"old":9});
    v["future"] = json!({"x":true});
    let s = State::from_value(v).unwrap();
    assert!(!s.extra.contains_key("origins"));
    assert_eq!(s.extra["future"], json!({"x":true}));
}
#[test]
fn rejects_malformed_legacy() {
    for raw in [
        json!({"version":7}),
        json!({"version":2,"owners":{"bad":"A"}}),
        json!({"version":2,"owners":{"1":false}}),
        json!({"version":2,"last":false}),
        json!({"version":2,"owners":{"1":"A"},"last":{"1":i64::MAX}}),
    ] {
        assert!(state::project(Some(raw), &BTreeSet::new()).is_err());
    }
}
#[test]
fn parses_all_commands() {
    for name in [
        "cycle",
        "create-empty",
        "isolate-or-previous",
        "move-next",
        "cleanup",
        "snapshot",
        "migrate",
    ] {
        assert!(Action::parse(&[name.into()]).is_ok());
    }
    for name in ["closed", "focus-workspace"] {
        assert!(Action::parse(&[name.into(), "9".into()]).is_ok());
    }
}
#[test]
fn rejects_bad_commands_before_lock() {
    for args in [
        vec![],
        vec!["toggle-row".into()],
        vec!["closed".into(), "-1".into()],
        vec!["focus-workspace".into(), "x".into()],
    ] {
        assert!(Action::parse(&args).is_err());
    }
}
#[test]
fn lua_guard_single_eval() {
    for code in [
        native::focus(9, true),
        native::move_window(9, "0xab", true).unwrap(),
    ] {
        assert!(code.find("hl.get_workspace").unwrap() < code.find("hl.dispatch").unwrap());
        assert!(!code.contains("animation"));
    }
}
#[test]
fn rejects_lua_address_injection() {
    for address in ["", "0x1\";bad", "0x1\n", "$(bad)"] {
        assert!(native::move_window(9, address, true).is_err());
    }
}
#[test]
fn atomic_roundtrip_and_private_state() {
    use std::os::unix::fs::PermissionsExt;
    let tmp = Temp::new();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    assert_eq!(store.read().unwrap(), None);
    store.save(&state()).unwrap();
    assert_eq!(
        store.read().unwrap(),
        Some(serde_json::to_value(state()).unwrap())
    );
    assert_eq!(
        std::fs::metadata(tmp.0.join("workspace-columns.json"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
}
#[test]
fn invalid_save_preserves_previous() {
    let tmp = Temp::new();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    store.save(&state()).unwrap();
    let before = std::fs::read(tmp.0.join("workspace-columns.json")).unwrap();
    let mut bad = state();
    bad.next_id = 0;
    assert!(store.save(&bad).is_err());
    assert_eq!(
        std::fs::read(tmp.0.join("workspace-columns.json")).unwrap(),
        before
    );
}
#[test]
fn refuses_symlink_state_and_lock() {
    use std::os::unix::fs::symlink;
    let tmp = Temp::new();
    let target = tmp.0.join("target");
    std::fs::write(&target, b"preserve").unwrap();
    symlink(&target, tmp.0.join("workspace-columns.lock")).unwrap();
    assert!(LockedStore::open(&tmp.0).is_err());
    std::fs::remove_file(tmp.0.join("workspace-columns.lock")).unwrap();
    symlink(&target, tmp.0.join("workspace-columns.json")).unwrap();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    assert!(store.read().is_err());
    assert!(store.save(&state()).is_err());
    assert_eq!(std::fs::read(target).unwrap(), b"preserve");
}
#[test]
fn refuses_hardlinked_state() {
    let tmp = Temp::new();
    std::fs::write(tmp.0.join("target"), b"preserve").unwrap();
    std::fs::hard_link(tmp.0.join("target"), tmp.0.join("workspace-columns.json")).unwrap();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    assert!(store.read().is_err());
    assert!(store.save(&state()).is_err());
}
#[test]
fn preserves_unowned_temporary() {
    let tmp = Temp::new();
    std::fs::write(tmp.0.join(".workspace-list-foreign"), b"keep").unwrap();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    store.save(&state()).unwrap();
    assert_eq!(
        std::fs::read(tmp.0.join(".workspace-list-foreign")).unwrap(),
        b"keep"
    );
}
#[test]
fn unknown_schema_does_not_repair() {
    let tmp = Temp::new();
    std::fs::write(tmp.0.join("workspace-columns.json"), b"{\"version\":99}").unwrap();
    let mut store = LockedStore::open(&tmp.0).unwrap();
    let raw: Value = store.read().unwrap().unwrap();
    assert!(state::project(Some(raw), &BTreeSet::new()).is_err());
    assert_eq!(
        std::fs::read(tmp.0.join("workspace-columns.json")).unwrap(),
        b"{\"version\":99}"
    );
}
