use crate::{
    Result, admin,
    core::{Core, REQUEST_TIMEOUT},
    desktop::Desktop,
    native::Native,
    startup::{self, Marker, Phase},
    storage::Store,
    workspace::Controller,
};
use serde_json::{Value, json};
use std::{collections::VecDeque, time::Duration};
#[test]
fn marker_phases_and_schema() {
    for phase in ["initializing", "failed", "ready", "deferred"] {
        assert!(Marker::parse(json!({"version":1,"instance":"one","phase":phase})).is_ok());
    }
    for raw in [
        json!({}),
        json!({"version":2,"instance":"one","phase":"ready"}),
        json!({"version":1,"instance":"one","phase":"other"}),
    ] {
        assert!(Marker::parse(raw).is_err());
    }
}
#[test]
fn signature_character_bound() {
    assert!(startup::validate_signature("").is_err());
    assert!(startup::validate_signature(&"x".repeat(513)).is_err());
    assert!(startup::validate_signature(&"é".repeat(512)).is_ok());
}
#[test]
fn defer_preserves_same_instance_failed_or_ready() {
    for phase in ["initializing", "failed", "ready", "deferred"] {
        let marker = json!({"version":1,"instance":"one","phase":phase,"extra":"preserve"});
        let result = startup::defer_marker("one", Some(marker.clone())).unwrap();
        assert_eq!(result, json!({"changed":false,"marker":marker}));
    }
}
#[test]
fn defer_new_instance_only_proposes_marker() {
    let old = json!({"version":1,"instance":"old","phase":"failed"});
    let result = startup::defer_marker("new", Some(old)).unwrap();
    assert_eq!(
        result,
        json!({"changed":true,"marker":{"version":1,"instance":"new","phase":"deferred"}})
    );
    assert_eq!(Marker::new("new", Phase::Deferred).version, 1);
}
#[test]
fn pure_admin_state_and_unknown_operation() {
    let state =
        json!({"version":3,"order":[1],"owners":{"1":"A"},"preferred":{},"next_id":2,"origins":{}});
    assert_eq!(
        admin::run("validate-state", json!({"state":state})).unwrap(),
        state
    );
    assert!(admin::run("project-state", json!({"existing_ids":[1,1]})).is_err());
    assert!(admin::run("unknown", Value::Null).is_err());
    assert!(admin::run("defer-marker", json!({"instance":"new","previous":{}})).is_err());
}
struct Readiness {
    replies: VecDeque<(&'static str, Result<Option<Value>>)>,
    calls: usize,
    sleeps: usize,
}
impl Native for Readiness {
    fn ctl(&mut self, _: &[&str]) -> Result<String> {
        panic!("unbounded/mutating call during readiness")
    }
    fn startup_query(&mut self, name: &str, timeout: Duration) -> Result<Option<Value>> {
        assert!(timeout > Duration::ZERO && timeout <= Duration::from_secs(2));
        self.calls += 1;
        let (expected, reply) = self.replies.pop_front().expect("unexpected probe/retry");
        assert_eq!(name, expected);
        reply
    }
    fn sleep(&mut self, d: Duration) {
        assert!(d <= Duration::from_millis(100));
        self.sleeps += 1;
    }
}
fn ready_probe(replies: Vec<(&'static str, Result<Option<Value>>)>) -> Readiness {
    Readiness {
        replies: replies.into(),
        calls: 0,
        sleeps: 0,
    }
}
#[test]
fn startup_hyprctl_empty_registry_bug_is_narrowly_retryable() {
    use crate::native::startup_reply;
    assert_eq!(startup_reply("instances", true, b"\n]\n\n").unwrap(), None);
    for (name, ok, text) in [
        ("monitors", true, &b"\n]\n\n"[..]),
        ("instances", false, &b"\n]\n\n"[..]),
        ("instances", true, &b"{bad"[..]),
        ("instances", true, &b"\xff"[..]),
    ] {
        assert!(startup_reply(name, ok, text).is_err());
    }
    assert_eq!(
        startup_reply(
            "monitors",
            false,
            b"Couldn't connect to /private/hypr/test/.socket.sock. (4)\n"
        )
        .unwrap(),
        None
    );
    assert!(startup_reply("monitors", false, b"error: invalid configuration").is_err());
}
#[test]
fn readiness_waits_for_registration_ipc_and_active_workspace() {
    let instance = json!([{"instance":"one"}]);
    let mut n = ready_probe(vec![
        ("instances", Ok(None)),
        ("instances", Ok(Some(json!([])))),
        ("instances", Ok(Some(instance.clone()))),
        ("monitors", Ok(None)),
        ("instances", Ok(Some(instance.clone()))),
        ("monitors", Ok(Some(json!([{"activeWorkspace":{"id":0}}])))),
        ("instances", Ok(Some(instance))),
        ("monitors", Ok(Some(json!([{"activeWorkspace":{"id":1}}])))),
    ]);
    startup::wait_for_compositor(&mut n, "one", Duration::from_secs(1)).unwrap();
    assert_eq!(n.calls, 8);
    assert_eq!(n.sleeps, 4);
}
#[test]
fn readiness_exhaustion_never_dispatches_or_queries_core() {
    let mut n = ready_probe(vec![("instances", Ok(None))]);
    assert!(
        startup::wait_for_compositor(&mut n, "one", Duration::ZERO)
            .unwrap_err()
            .contains("no reset performed")
    );
    assert_eq!(n.calls, 1);
    assert_eq!(n.sleeps, 0);
}
#[test]
fn wrong_ambiguous_or_malformed_readiness_is_not_retried() {
    for value in [
        json!(null),
        json!([{"instance":"other"}]),
        json!([{"instance":"one"},{"instance":"other"}]),
    ] {
        let mut n = ready_probe(vec![("instances", Ok(Some(value)))]);
        assert!(startup::wait_for_compositor(&mut n, "one", Duration::from_secs(1)).is_err());
        assert_eq!(n.calls, 1);
        assert_eq!(n.sleeps, 0);
    }
    for value in [
        json!(null),
        json!([null]),
        json!([{"activeWorkspace":{"id":"x"}}]),
        json!([{}, {}]),
    ] {
        let mut n = ready_probe(vec![
            ("instances", Ok(Some(json!([{"instance":"one"}])))),
            ("monitors", Ok(Some(value))),
        ]);
        assert!(startup::wait_for_compositor(&mut n, "one", Duration::from_secs(1)).is_err());
        assert_eq!(n.calls, 2);
        assert_eq!(n.sleeps, 0);
    }
}
struct MenuStore {
    marker: Option<Value>,
    writes: usize,
    fail: bool,
}
impl Store for MenuStore {
    fn read(&mut self) -> Result<Option<Value>> {
        panic!("menu claim must not read workspace state")
    }
    fn save(&mut self, _: &crate::state::State) -> Result<()> {
        panic!("menu claim must not write workspace state")
    }
}
impl startup::StartupStore for MenuStore {
    fn marker(&mut self) -> Result<Option<Value>> {
        Ok(self.marker.clone())
    }
    fn write_marker(&mut self, m: &Marker) -> Result<()> {
        if self.fail {
            return Err("injected marker publication failure".into());
        }
        self.writes += 1;
        self.marker = Some(serde_json::to_value(m).unwrap());
        Ok(())
    }
    fn backup(&mut self, _: &Value) -> Result<()> {
        panic!("menu claim is not initialization")
    }
}
#[test]
fn menu_claim_consumes_only_explicit_ready_request_and_preserves_fields() {
    let raw = json!({"version":1,"instance":"one","phase":"ready","startup_menu":"pending","keep":{"x":1}});
    let mut store = MenuStore {
        marker: Some(raw.clone()),
        writes: 0,
        fail: false,
    };
    assert!(startup::claim_menu(&mut store, "one").unwrap());
    let mut expected = raw;
    expected["startup_menu"] = json!("consumed");
    assert_eq!(store.marker, Some(expected));
    assert!(!startup::claim_menu(&mut store, "one").unwrap());
    assert_eq!(store.writes, 1);
}
#[test]
fn failed_menu_claim_publication_never_authorizes_show() {
    let raw = json!({"version":1,"instance":"one","phase":"ready","startup_menu":"pending"});
    let mut store = MenuStore {
        marker: Some(raw.clone()),
        writes: 0,
        fail: true,
    };
    assert!(startup::claim_menu(&mut store, "one").is_err());
    assert_eq!(store.marker, Some(raw));
    assert_eq!(store.writes, 0);
}
#[test]
fn invalid_menu_request_is_not_repaired() {
    let raw = json!({"version":1,"instance":"one","phase":"ready","startup_menu":true});
    let mut store = MenuStore {
        marker: Some(raw.clone()),
        writes: 0,
        fail: false,
    };
    assert!(startup::claim_menu(&mut store, "one").is_err());
    assert_eq!(store.marker, Some(raw));
    assert_eq!(store.writes, 0);
}
struct Memory;
impl Store for Memory {
    fn read(&mut self) -> Result<Option<Value>> {
        panic!("no state read during wait")
    }
    fn save(&mut self, _: &crate::state::State) -> Result<()> {
        panic!("no save during wait")
    }
}
struct FakeNative {
    waits: usize,
}
impl Native for FakeNative {
    fn ctl(&mut self, _: &[&str]) -> Result<String> {
        panic!("no native IO during core wait")
    }
    fn sleep(&mut self, d: Duration) {
        assert_eq!(d, Duration::from_millis(100));
        self.waits += 1;
    }
}
struct Probe {
    replies: VecDeque<Result<Value>>,
    calls: usize,
}
impl Core for Probe {
    fn request(&mut self, args: &[&str], timeout: Duration) -> Result<Value> {
        assert_eq!(args, ["list"]);
        assert_eq!(timeout, Duration::from_secs(2));
        self.calls += 1;
        self.replies.pop_front().unwrap()
    }
}
fn desktop(replies: Vec<Result<Value>>) -> Desktop<FakeNative, Memory, Probe> {
    Desktop {
        workspace: Controller {
            native: FakeNative { waits: 0 },
            store: Memory,
        },
        core: Probe {
            replies: replies.into(),
            calls: 0,
        },
    }
}
#[test]
fn read_only_unavailable_and_timeout_retry() {
    let mut d = desktop(vec![
        Err("transport.unavailable".into()),
        Err("child deadline exceeded; result may be uncertain; not retrying".into()),
        Ok(json!({"sessions":[],"active_session_id":null})),
    ]);
    assert!(startup::wait_for_core(&mut d, Duration::from_secs(1)).is_ok());
    assert_eq!(d.core.calls, 3);
    assert_eq!(d.workspace.native.waits, 2);
    assert_eq!(REQUEST_TIMEOUT, Duration::from_secs(35));
}
#[test]
fn unavailable_budget_refuses_without_mutation() {
    let mut d = desktop(vec![Err("transport.unavailable".into())]);
    assert!(
        startup::wait_for_core(&mut d, Duration::ZERO)
            .unwrap_err()
            .contains("unavailable at graphical startup")
    );
    assert_eq!(d.core.calls, 1);
    assert_eq!(d.workspace.native.waits, 0);
}
#[test]
fn nontransport_probe_error_not_retried() {
    let mut d = desktop(vec![Err("recovery.upgrade_required".into())]);
    assert_eq!(
        startup::wait_for_core(&mut d, Duration::from_secs(1)).unwrap_err(),
        "recovery.upgrade_required"
    );
    assert_eq!(d.core.calls, 1);
}
