use super::*;
use std::fs;
fn initial() -> (Value, Value, Temporary, Temporary) {
    let source = Temporary::new(&std::env::temp_dir(), ".r7-test-source-", ".mkv").unwrap();
    let project = Temporary::new(&std::env::temp_dir(), ".r7-test-project-", ".fcproj").unwrap();
    let tracks:Vec<_>=(0..4).map(|i|json!({"id":100+i,"items":[{"clip":i+1,"start":0,"duration":20000,"sourceIn":25000,"sourceOut":45000,"item":1,"link":101}]})).collect();
    let raw_tracks:Vec<_>=(0..4).map(|i|json!({"id":100+i,"name":format!("Audio {}",i+1),"items":[{"source_channels":[i]}]})).collect();
    let before = json!({"duration":60000,"durationFrames":60,"video":[{"id":5}],"audio":tracks});
    let raw = json!({"project":{"items":{"1":{"kind":{"Media":{"media":{"File":{"path":source.path}}}}},"2":{"kind":{"Sequence":{"settings":{"frame_rate":{"num":30,"den":1}},"audio_tracks":raw_tracks}}}}}});
    (before, raw, source, project)
}
#[test]
fn exact_integer() {
    let text = "123456789012345678901234567890";
    assert_eq!(
        integer(&serde_json::from_str(text).unwrap())
            .unwrap()
            .to_string(),
        text
    );
}
#[test]
fn reject_coercions() {
    for v in [json!(true), json!(1.5), json!("1"), Value::Null] {
        assert!(integer(&v).is_err());
    }
}
#[test]
fn required_end_exact() {
    let (b, r, s, p) = initial();
    let t = validate(&b, &r, &s.path, &p.path).unwrap();
    assert_eq!(t.required, Rational::new(3.into(), 2.into()));
}
#[test]
fn rational_fps() {
    let (b, mut r, s, p) = initial();
    r["project"]["items"]["2"]["kind"]["Sequence"]["settings"]["frame_rate"] =
        json!({"num":30000,"den":1001});
    let t = validate(&b, &r, &s.path, &p.path).unwrap();
    assert_eq!(t.required, Rational::new(3003.into(), 2000.into()));
}
#[test]
fn bad_fps_refused() {
    let (b, mut r, s, p) = initial();
    r["project"]["items"]["2"]["kind"]["Sequence"]["settings"]["frame_rate"]["den"] = json!(0);
    assert!(validate(&b, &r, &s.path, &p.path).is_err());
}
#[test]
fn bad_ticks_refused() {
    let (mut b, r, s, p) = initial();
    b["durationFrames"] = json!(0);
    assert!(validate(&b, &r, &s.path, &p.path).is_err());
}
#[test]
fn negative_end_refused() {
    let (mut b, r, s, p) = initial();
    b["audio"][2]["items"][0]["sourceOut"] = json!(-1);
    assert!(validate(&b, &r, &s.path, &p.path).is_err());
}
#[test]
fn misalignment_refused() {
    let (mut b, r, s, p) = initial();
    b["audio"][1]["items"][0]["sourceIn"] = json!(0);
    assert!(validate(&b, &r, &s.path, &p.path).is_err());
}
#[test]
fn decimal_ties_even() {
    assert_eq!(
        decimal(&Rational::new(1.into(), 2_000_000_000u64.into()), 9).unwrap(),
        "0.000000000"
    );
    assert_eq!(
        decimal(&Rational::new(3.into(), 2_000_000_000u64.into()), 9).unwrap(),
        "0.000000002"
    );
}
#[test]
fn decimal_no_float() {
    let n = BigInt::from(1u8) << 100usize;
    assert_eq!(
        decimal(&Rational::from_integer(n.clone()), 9).unwrap(),
        format!("{n}.000000000")
    );
    assert_eq!(
        decimal(&Rational::new(1.into(), 3.into()), 9).unwrap(),
        "0.333333333"
    );
}
#[test]
fn negative_decimal_refused() {
    assert!(decimal(&Rational::new((-1).into(), 3.into()), 9).is_err());
}
#[test]
fn advisory_lock_shared_by_helpers() {
    let t = Temporary::new(&std::env::temp_dir(), ".r7-lock-", ".fcproj").unwrap();
    let lock = Original::open(&t.path).unwrap();
    assert!(Original::open(&t.path).is_err());
    drop(lock);
    assert!(Original::open(&t.path).is_ok());
}
#[test]
fn wav_no_clobber() {
    let a = Temporary::new(&std::env::temp_dir(), ".r7-link-", ".wav").unwrap();
    let b = Temporary::new(&std::env::temp_dir(), ".r7-link-", ".wav").unwrap();
    assert!(Published::create(&a, &b.path).is_err());
    assert_eq!(fs::read(&b.path).unwrap(), b"");
}
#[test]
fn stale_temporary_refused() {
    let t = Temporary::new(&std::env::temp_dir(), ".r7-stale-", ".wav").unwrap();
    fs::write(&t.path, b"changed").unwrap();
    assert!(t.verify().is_err());
}
#[test]
fn exchange_retains_original() {
    let old = Temporary::new(&std::env::temp_dir(), ".r7-original-", ".fcproj").unwrap();
    fs::write(&old.path, b"original bytes").unwrap();
    let snapshot = Original::open(&old.path).unwrap();
    let mut new = Temporary::new(&std::env::temp_dir(), ".r7-new-", ".fcproj").unwrap();
    fs::write(&new.path, b"new bytes").unwrap();
    new.refresh().unwrap();
    let backup = snapshot.exchange(&mut new).unwrap();
    assert_eq!(fs::read(&old.path).unwrap(), b"new bytes");
    assert_eq!(fs::read(&backup).unwrap(), b"original bytes");
    fs::remove_file(&old.path).unwrap();
    fs::remove_file(backup).unwrap();
}
#[test]
fn concurrent_edit_refused() {
    let old = Temporary::new(&std::env::temp_dir(), ".r7-edit-", ".fcproj").unwrap();
    let snapshot = Original::open(&old.path).unwrap();
    fs::write(&old.path, b"user changes").unwrap();
    assert!(snapshot.verify().is_err());
    assert_eq!(fs::read(&old.path).unwrap(), b"user changes");
}
