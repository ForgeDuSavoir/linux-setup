use crate::{core::*, desktop::Action};
use serde_json::json;
use std::{
    os::unix::fs::PermissionsExt,
    time::{Duration, Instant},
};
#[test]
fn closed_typed_sources() {
    for bad in [
        json!({"kind":"neutral","extra":true}),
        json!({"kind":"project"}),
        json!({"kind":"other"}),
    ] {
        assert!(serde_json::from_value::<Source>(bad).is_err());
    }
    assert!(
        Source::Project {
            project_name: "".into()
        }
        .arguments()
        .is_err()
    );
}
#[test]
fn identities_and_active_membership() {
    for bad in [
        json!({"sessions":[],"active_session_id":"missing"}),
        json!({"sessions":[{"id":"A","source":{"kind":"neutral"}},{"id":"A","source":{"kind":"neutral"}}],"active_session_id":"A"}),
        json!({"sessions":[{"id":"","source":{"kind":"neutral"}}],"active_session_id":null}),
        json!({"sessions":[]}),
    ] {
        assert!(Sessions::parse(&bad).is_err());
    }
}
#[test]
fn sources_required_for_v3_list() {
    for source in [
        json!(null),
        json!({"kind":"project","project_name":""}),
        json!({"kind":"neutral","extra":1}),
    ] {
        assert!(
            Sessions::parse(
                &json!({"sessions":[{"id":"A","source":source}],"active_session_id":"A"})
            )
            .is_err()
        );
    }
    assert!(Sessions::parse(&json!({"sessions":[{"id":"A"}],"active_session_id":"A"})).is_err());
}
#[test]
fn minimal_ack_and_invalid_ack() {
    assert_eq!(
        acknowledged_session(&json!({"session":{"id":"A"}}))
            .unwrap()
            .0,
        "A"
    );
    for bad in [
        json!({}),
        json!({"session":{"id":""}}),
        json!({"session":{"id":false}}),
    ] {
        assert!(acknowledged_session(&bad).is_err());
    }
}
#[test]
fn cli_actions_and_literal_project() {
    for argv in [
        vec!["status"],
        vec!["deactivate"],
        vec!["close"],
        vec!["close", "3"],
        vec!["switch", "A"],
        vec!["stop", "A"],
        vec!["start", "--neutral"],
        vec!["start", "--project", "literal ; $(value)"],
    ] {
        assert!(Action::parse(&argv.into_iter().map(String::from).collect::<Vec<_>>()).is_ok());
    }
    assert!(Action::parse(&["start".into(), "old-project".into()]).is_err());
}
#[test]
fn default_deadline_is_preserved() {
    assert_eq!(REQUEST_TIMEOUT, Duration::from_secs(35));
}
fn helper(text: &str) -> (crate::tests::Temp, CliCore) {
    let tmp = crate::tests::Temp::new();
    let path = tmp.0.join("core");
    std::fs::write(&path, format!("#!/usr/bin/python3\n{text}\n")).unwrap();
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o700)).unwrap();
    (tmp, CliCore { binary: path })
}
#[test]
fn transport_errors_and_json() {
    for text in [
        "print('bad JSON')",
        "import sys;print('{\"code\":\"fixture.error\"}');sys.exit(1)",
    ] {
        let (_tmp, mut cli) = helper(text);
        assert!(cli.request(&["list"], Duration::from_secs(2)).is_err());
    }
    let (_tmp, mut cli) = helper("print('{\"sessions\":[],\"active_session_id\":null}')");
    assert!(Sessions::parse(&cli.request(&["list"], Duration::from_secs(2)).unwrap()).is_ok());
}
#[test]
fn timed_out_helper_is_not_retried() {
    let (tmp, mut cli) = helper(
        "import time\nfrom pathlib import Path\np=Path(__file__).with_name(\"calls\")\nwith p.open(\"a\") as f:f.write(\"once\\n\")\ntime.sleep(5)",
    );
    let start = Instant::now();
    let error = cli
        .request(&["stop", "A"], Duration::from_millis(30))
        .unwrap_err();
    assert!(error.contains("uncertain"));
    assert!(start.elapsed() < Duration::from_secs(2));
    if let Ok(calls) = std::fs::read_to_string(tmp.0.join("calls")) {
        assert_eq!(calls.lines().count(), 1);
    }
}
#[test]
fn owner_neutral_uuid_is_not_unowned() {
    use crate::desktop::Owner;
    let id = SessionId("11111111-1111-1111-1111-111111111111".into());
    assert_ne!(Owner::active(Some(&id)), Owner::Unowned);
    assert_eq!(Owner::parse(&id.0).unwrap(), Owner::active(Some(&id)));
    assert_eq!(Owner::active(None), Owner::Unowned);
}
