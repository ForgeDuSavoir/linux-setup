use crate::{notify::Context, pi};
const A: &str = "session:11111111-1111-1111-1111-111111111111";
#[test]
fn exact_origin() {
    assert_eq!(pi::accepted_context(&format!(" {A}\n"), Some(A)).label(), A);
}
#[test]
fn changed_origin() {
    assert_eq!(
        pi::accepted_context("session:22222222-2222-2222-2222-222222222222", Some(A)),
        Context::Global
    );
}
#[test]
fn unowned_is_not_uuid() {
    assert_eq!(pi::accepted_context("neutral", Some(A)), Context::Global);
    assert_eq!(
        pi::accepted_context("neutral", Some("neutral")),
        Context::Unowned
    );
}
#[test]
fn explicit_agora_accepts_fresh_source() {
    assert_eq!(pi::accepted_context(A, None).label(), A);
}
#[test]
fn malformed_capture_is_global() {
    for s in [
        "",
        "session:bad",
        "neutral\nextra",
        "SESSION:11111111-1111-1111-1111-111111111111",
    ] {
        assert_eq!(pi::accepted_context(s, None), Context::Global);
    }
}
#[test]
fn relative_config_is_refused() {
    assert!(pi::agora_root(std::path::Path::new("relative")).is_err());
}
#[test]
fn relative_directory_is_refused() {
    assert!(pi::validate_directory(std::path::Path::new(".")).is_err());
}
