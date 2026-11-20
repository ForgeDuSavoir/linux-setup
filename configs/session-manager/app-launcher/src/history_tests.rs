use super::*;
use crate::{Origin, test_support::Temp};
fn app(id: &str) -> Application {
    Application {
        id: id.into(),
        name: id.into(),
        icon: None,
        origin: Origin::Installed,
    }
}
fn store(temp: &Temp) -> Store {
    let root = fs::Dir::open(&temp.0, false).unwrap();
    Store::project(&temp.0, root.id().unwrap())
}
fn bytes(inner: &str) -> Vec<u8> {
    format!(r#"{{"version":1,"apps":{{{inner}}}}}"#).into_bytes()
}

#[test]
fn half_life_and_increment() {
    let mut h = History::default();
    h.update("a.desktop", 100).unwrap();
    assert_eq!(h.apps["a.desktop"].score(100), 1.0);
    assert_eq!(h.apps["a.desktop"].score(604900), 0.5);
    h.update("a.desktop", 604900).unwrap();
    assert_eq!(h.apps["a.desktop"].weight, 1.5);
    assert_eq!(h.apps["a.desktop"].count, 2);
}
#[test]
fn ranking_ties_recency_name_id_not_total() {
    let mut h = History::default();
    h.apps.insert(
        "a.desktop".into(),
        Entry {
            count: 100,
            last_used: 0,
            weight: 2.0,
        },
    );
    h.apps.insert(
        "b.desktop".into(),
        Entry {
            count: 1,
            last_used: 604800,
            weight: 1.0,
        },
    );
    assert!(
        h.compare(("b.desktop", "Z"), ("a.desktop", "A"), 604800)
            .is_lt()
    );
    assert!(
        h.compare(("x.desktop", "Alpha"), ("y.desktop", "beta"), 604800)
            .is_lt()
    );
    assert!(
        h.compare(("x.desktop", "Same"), ("y.desktop", "same"), 604800)
            .is_lt()
    );
}
#[test]
fn clock_backwards_is_clamped() {
    let mut h = History::default();
    h.update("a.desktop", 100).unwrap();
    assert_eq!(h.apps["a.desktop"].score(50), 1.0);
    h.update("b.desktop", 50).unwrap();
    assert!(
        h.compare(("a.desktop", "Same"), ("b.desktop", "same"), 50)
            .is_lt()
    ); // ID, not future timestamp.
    h.update("a.desktop", 50).unwrap();
    assert_eq!(h.apps["a.desktop"].weight, 2.0);
}
#[test]
fn duplicate_keys_and_unknown_fields_are_rejected() {
    for text in [
        r#"{"version":1,"version":1,"apps":{}}"#,
        r#"{"version":1,"apps":{},"apps":{}}"#,
        r#"{"version":2,"apps":{}}"#,
        r#"{"version":1,"apps":{},"extra":true}"#,
    ] {
        assert!(History::parse(text.as_bytes()).is_err());
    }
    let e = r#""a.desktop":{"count":1,"weight":1,"last_used":0}"#;
    assert!(History::parse(&bytes(&format!("{e},{e}"))).is_err());
    for value in [
        r#"{"count":1,"count":1,"weight":1,"last_used":0}"#,
        r#"{"count":1,"weight":1,"last_used":0,"extra":0}"#,
    ] {
        assert!(History::parse(&bytes(&format!(r#""a.desktop":{value}"#))).is_err());
    }
}
#[test]
fn invalid_numeric_types_ranges_and_ids_are_rejected() {
    for value in [
        r#"{"count":0,"weight":1,"last_used":0}"#,
        r#"{"count":1.0,"weight":1,"last_used":0}"#,
        r#"{"count":1,"weight":2,"last_used":0}"#,
        r#"{"count":1,"weight":-1,"last_used":0}"#,
        r#"{"count":1,"weight":0,"last_used":0}"#,
        r#"{"count":1,"weight":1,"last_used":253402300800}"#,
    ] {
        assert!(History::parse(&bytes(&format!(r#""a.desktop":{value}"#))).is_err());
    }
    assert!(
        History::parse(&bytes(
            r#""../a.desktop":{"count":1,"weight":1,"last_used":0}"#
        ))
        .is_err()
    );
    assert!(History::parse(&vec![b' '; LIMIT + 1]).is_err());
    assert!(!valid_id(&format!("{}.desktop", "a".repeat(1024))));
}
#[test]
fn saturation_and_retention() {
    let mut h = History::default();
    h.apps.insert(
        "a.desktop".into(),
        Entry {
            count: u64::MAX,
            last_used: 0,
            weight: 1_000_000.0,
        },
    );
    h.update("a.desktop", 0).unwrap();
    assert_eq!(h.apps["a.desktop"].count, u64::MAX);
    assert_eq!(h.apps["a.desktop"].weight, 1_000_000.0);
    h.update("b.desktop", RETENTION + 1).unwrap();
    assert!(!h.apps.contains_key("a.desktop"));
    assert_eq!(
        History::parse(&serde_json::to_vec(&h).unwrap())
            .unwrap()
            .apps
            .len(),
        1
    );
}
#[test]
fn eviction_protects_new_entry_and_bounds_size() {
    let mut h = History::default();
    for i in 0..MAX_ENTRIES {
        h.apps.insert(
            format!("{i:04}.desktop"),
            Entry {
                count: 1,
                last_used: 0,
                weight: 1.0,
            },
        );
    }
    let bytes = h.update("new.desktop", 1).unwrap();
    assert_eq!(h.apps.len(), MAX_ENTRIES);
    assert!(!h.apps.contains_key("0000.desktop"));
    assert!(bytes.len() <= LIMIT);
    let many = (0..MAX_ENTRIES + 1)
        .map(|i| format!(r#""{i}.desktop":{{"count":1,"last_used":0,"weight":1}}"#))
        .collect::<Vec<_>>()
        .join(",");
    assert!(History::parse(&bytes_for_many(&many)).is_err());
}
#[test]
fn last_context_failure_does_not_publish_measure() {
    let temp = Temp::new();
    let store = store(&temp);
    assert!(
        store
            .record_checked(&app("a.desktop"), 100, || Err("context changed".into()))
            .is_err()
    );
    assert!(!temp.0.join(".session-manager/app-usage.json").exists());
}
#[test]
fn serialized_size_eviction_is_bounded_too() {
    let mut h = History::default();
    for i in 0..1200 {
        h.apps.insert(
            format!("{i:04}{}.desktop", "x".repeat(900)),
            Entry {
                count: 1,
                last_used: 0,
                weight: 1.0,
            },
        );
    }
    let bytes = h.update("new.desktop", 1).unwrap();
    assert!(bytes.len() <= LIMIT && h.apps.len() < 1200 && h.apps.contains_key("new.desktop"));
    assert!(History::parse(&bytes).is_ok());
}
fn bytes_for_many(text: &str) -> Vec<u8> {
    bytes(text)
}
#[test]
fn missing_read_is_pure_and_parallel_sessions_merge() {
    let temp = Temp::new();
    let store = store(&temp);
    assert!(store.read().unwrap().apps.is_empty());
    assert!(!temp.0.join(".session-manager").exists());
    std::thread::scope(|scope| {
        for _ in 0..8 {
            scope.spawn(|| {
                for _ in 0..4 {
                    store.record(&app("a.desktop"), 100).unwrap();
                }
            });
        }
    });
    assert_eq!(store.read().unwrap().apps["a.desktop"].count, 32);
}
#[test]
fn corrupt_file_is_not_replaced() {
    let temp = Temp::new();
    let store = store(&temp);
    std::fs::create_dir(temp.0.join(".session-manager")).unwrap();
    use std::os::unix::fs::PermissionsExt;
    let path = temp.0.join(".session-manager/app-usage.json");
    std::fs::write(&path, b"corrupt").unwrap();
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
    assert!(store.record(&app("a.desktop"), 100).is_err());
    assert_eq!(std::fs::read(path).unwrap(), b"corrupt");
}
#[test]
fn identity_replacement_cannot_recreate_old_project() {
    let temp = Temp::new();
    let path = temp.0.join("p");
    std::fs::create_dir(&path).unwrap();
    let root = fs::Dir::open(&path, false).unwrap();
    let store = Store::project(&path, root.id().unwrap());
    std::fs::rename(&path, temp.0.join("renamed")).unwrap();
    assert!(store.record(&app("a.desktop"), 100).is_err());
    assert!(!path.exists());
    std::fs::create_dir(&path).unwrap();
    assert!(store.record(&app("a.desktop"), 100).is_err());
    assert!(!path.join(".session-manager").exists());
}
#[test]
fn independent_projects_and_reopen_after_rename() {
    let a = Temp::new();
    let b = Temp::new();
    store(&a).record(&app("a.desktop"), 100).unwrap();
    assert!(store(&b).read().unwrap().apps.is_empty());
    let moved = a.0.with_extension("moved");
    std::fs::rename(&a.0, &moved).unwrap();
    let root = fs::Dir::open(&moved, false).unwrap();
    assert_eq!(
        Store::project(&moved, root.id().unwrap())
            .read()
            .unwrap()
            .apps["a.desktop"]
            .count,
        1
    );
    std::fs::rename(moved, &a.0).unwrap();
}
