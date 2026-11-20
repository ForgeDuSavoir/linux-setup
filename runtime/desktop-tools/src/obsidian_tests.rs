use crate::obsidian;
use serde_json::json;
use std::{ffi::OsString, path::Path};
const A: &str = "0123456789abcdef";
#[test]
fn exact_registered_root() {
    assert_eq!(
        obsidian::vault_id(
            &json!({"vaults":{A:{"path":"/Agora/Project"}}}),
            Path::new("/Agora/Project")
        )
        .unwrap(),
        A
    );
}
#[test]
fn no_parent_vault_inference() {
    assert!(
        obsidian::vault_id(
            &json!({"vaults":{A:{"path":"/Agora"}}}),
            Path::new("/Agora/Project")
        )
        .is_err()
    );
}
#[test]
fn names_not_identifiers() {
    assert!(
        obsidian::vault_id(
            &json!({"vaults":{"Project":{"path":"/Agora/Project"}}}),
            Path::new("/Agora/Project")
        )
        .is_err()
    );
}
#[test]
fn ambiguous_root_refused() {
    assert!(
        obsidian::vault_id(
            &json!({"vaults":{A:{"path":"/Agora"},"fedcba9876543210":{"path":"/Agora"}}}),
            Path::new("/Agora")
        )
        .is_err()
    );
}
#[test]
fn malformed_registry_refused() {
    for v in [json!(null), json!({"vaults":[]}), json!({})] {
        assert!(obsidian::vault_id(&v, Path::new("/Agora")).is_err());
    }
}
#[test]
fn id_shadowed_by_another_vault_name_refused() {
    assert!(obsidian::vault_id(&json!({"vaults":{A:{"path":"/Agora"},"fedcba9876543210":{"path":"/Other/0123456789ABCDEF"}}}),Path::new("/Agora")).is_err());
}
#[test]
fn unrelated_vaults_not_selected() {
    assert_eq!(
        obsidian::vault_id(
            &json!({"vaults":{A:{"path":"/Agora"},"other":{"path":"/Other/Agora"}}}),
            Path::new("/Agora")
        )
        .unwrap(),
        A
    );
}
#[test]
fn explicit_links_bypass_all_routing() {
    let a = vec![
        OsString::from("obsidian://open?vault=Other&file=a%20b"),
        OsString::from("/tmp/file 'quotes' ; $().md"),
    ];
    assert_eq!(
        obsidian::arguments(Path::new(""), Path::new(""), &a).unwrap(),
        a
    );
}
