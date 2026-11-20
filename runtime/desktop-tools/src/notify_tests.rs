use crate::notify::{self, Action, Context};
use serde_json::json;
fn parse(args: &[&str]) -> Action {
    notify::parse(&args.iter().map(|s| s.to_string()).collect::<Vec<_>>()).unwrap()
}
#[test]
fn canonical_contexts() {
    for label in [
        "global",
        "neutral",
        "session:12345678-1234-1234-1234-123456789abc",
    ] {
        assert_eq!(Context::parse(label).unwrap().label(), label);
    }
    for label in [
        "",
        "unknown",
        "session:12345678-1234-1234-1234-123456789ABC",
        "session:1234",
        "global\n",
        "session:12345678-1234-1234-1234-123456789abc\n",
    ] {
        assert!(Context::parse(label).is_err());
    }
}
#[test]
fn global_precedence_ignores_bad_inheritance() {
    let Action::Send(s) = parse(&["send", "--global", "x"]) else {
        panic!()
    };
    assert!(
        s.arguments(Some("bad"))
            .unwrap()
            .contains(&"string:x-agora-context:global".into())
    );
}
#[test]
fn explicit_precedence_ignores_bad_inheritance() {
    let Action::Send(s) = parse(&["send", "--context", "neutral", "x"]) else {
        panic!()
    };
    assert!(
        s.arguments(Some("bad"))
            .unwrap()
            .contains(&"string:x-agora-context:neutral".into())
    );
}
#[test]
fn invalid_inheritance_is_not_guessed() {
    let Action::Send(s) = parse(&["send", "x"]) else {
        panic!()
    };
    assert!(s.arguments(Some("bad")).is_err());
    assert!(
        s.arguments(None)
            .unwrap()
            .contains(&"string:x-agora-context:global".into())
    );
}
#[test]
fn signed_expiration_and_u32_range() {
    let Action::Send(s) = parse(&["send", "-t-1", "-r4294967295", "x"]) else {
        panic!()
    };
    assert!(s.arguments(None).unwrap().contains(&"-1".into()));
    let Action::Send(s) = parse(&["send", "-r4294967296", "x"]) else {
        panic!()
    };
    assert!(s.arguments(None).is_err());
}
#[test]
fn syntax_and_help_are_separate() {
    for args in [
        vec![],
        vec!["send"],
        vec!["send", "--global", "--context", "global", "x"],
        vec!["send", "-u", "bad", "x"],
    ] {
        assert!(notify::parse(&args.into_iter().map(String::from).collect::<Vec<_>>()).is_err());
    }
    assert_eq!(parse(&["send", "--h"]), Action::Help);
    assert_eq!(parse(&["capture", "--help"]), Action::Help);
}
#[test]
fn confirmed_status_never_invents_neutral() {
    for status in [
        json!({}),
        json!({"context_confirmed":false}),
        json!({"context_confirmed":1}),
        json!({"context_confirmed":true,"displayed_context":"unknown","active_session_id":null}),
    ] {
        assert!(notify::confirmed_context(&status).is_err());
    }
    assert_eq!(notify::confirmed_context(&json!({"context_confirmed":true,"displayed_context":"neutral","active_session_id":null})).unwrap(),Context::Unowned);
}
#[test]
fn inherited_capture_needs_no_desktop_or_home() {
    assert_eq!(
        notify::capture(std::path::Path::new("/nonexistent"), Some("global")).unwrap(),
        Context::Global
    );
    assert!(notify::capture(std::path::Path::new("/nonexistent"), Some("bad")).is_err());
}
#[test]
fn literal_summary_preserved() {
    let Action::Send(s) = parse(&["send", "--", "$(not-executed); literal", "quoted \"body\""])
    else {
        panic!()
    };
    let argv = s.arguments(None).unwrap();
    assert_eq!(
        &argv[argv.len() - 3..],
        ["--", "$(not-executed); literal", "quoted \"body\""]
    );
}
