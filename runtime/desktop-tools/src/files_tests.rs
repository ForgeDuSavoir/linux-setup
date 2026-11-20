use crate::{core, core::SessionId, files};
use serde_json::{Value, json};
fn state() -> Value {
    json!({"active_session_id":"11111111-1111-1111-1111-111111111111","displayed_context":"11111111-1111-1111-1111-111111111111","context_confirmed":true,"sessions":[{"id":"11111111-1111-1111-1111-111111111111","source":{"kind":"project","project_name":"P"}}]})
}
#[test]
fn project_confirmed() {
    assert_eq!(
        files::project_context(&state()).unwrap(),
        Some(files::ProjectContext {
            id: SessionId("11111111-1111-1111-1111-111111111111".into()),
            name: "P".into()
        })
    );
}
#[test]
fn neutral_uuid_goes_home() {
    let mut s = state();
    s["sessions"][0]["source"] = json!({"kind":"neutral"});
    assert_eq!(files::project_context(&s).unwrap(), None);
}
#[test]
fn no_session_goes_home() {
    let s = json!({"active_session_id":null,"displayed_context":"neutral","context_confirmed":true,"sessions":[]});
    assert_eq!(files::project_context(&s).unwrap(), None);
}
#[test]
fn unconfirmed_refused() {
    let mut s = state();
    s["context_confirmed"] = json!(false);
    assert!(files::project_context(&s).is_err());
}
#[test]
fn displayed_mismatch_refused() {
    let mut s = state();
    s["displayed_context"] = json!("neutral");
    assert!(files::project_context(&s).is_err());
}
#[test]
fn invalid_source_refused() {
    let mut s = state();
    s["sessions"][0]["source"]["extra"] = json!(1);
    assert!(files::project_context(&s).is_err());
}
#[test]
fn duplicate_session_refused() {
    let mut s = state();
    let duplicate = s["sessions"][0].clone();
    s["sessions"].as_array_mut().unwrap().push(duplicate);
    assert!(files::project_context(&s).is_err());
}
#[test]
fn catalogue_shared() {
    let p = json!({"projects":[{"name":"P","path":"/tmp/project with 'quotes'"}]});
    assert_eq!(
        core::project_path(&p, "P").unwrap(),
        std::path::PathBuf::from("/tmp/project with 'quotes'")
    );
    assert!(core::project_path(&p, "missing").is_err());
}
