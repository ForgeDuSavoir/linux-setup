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
