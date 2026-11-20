use super::*;
use crate::test_support::Temp;
use std::os::unix::fs::{PermissionsExt, symlink};

#[test]
fn reads_are_pure_and_atomic_updates_keep_modes() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    assert!(dir.read("missing", 16, false).unwrap().0.is_none());
    assert!(!temp.0.join("missing").exists());
    dir.publish("data", b"one", None, false, ".owned-").unwrap();
    let (_, stamp) = dir.read("data", 16, false).unwrap();
    dir.publish("data", b"two", stamp.as_ref(), false, ".owned-")
        .unwrap();
    assert_eq!(dir.read("data", 16, false).unwrap().0.unwrap(), b"two");
    assert_eq!(
        std::fs::metadata(temp.0.join("data")).unwrap().mode() & 0o777,
        0o600
    );
}
#[test]
fn symlink_fifo_and_hardlink_are_refused() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    dir.publish("outside", b"keep", None, false, ".owned-")
        .unwrap();
    symlink(temp.0.join("outside"), temp.0.join("alias")).unwrap();
    assert!(dir.read("alias", 100, false).is_err());
    assert!(dir.lock("alias").is_err());
    std::fs::hard_link(temp.0.join("outside"), temp.0.join("hard")).unwrap();
    assert!(dir.read("hard", 100, false).is_err());
    let fifo = CString::new(temp.0.join("fifo").as_os_str().as_bytes()).unwrap();
    assert_eq!(unsafe { libc::mkfifo(fifo.as_ptr(), 0o600) }, 0);
    assert!(dir.read("fifo", 100, false).is_err());
}
#[test]
fn parent_symlinks_are_not_followed_or_created_through() {
    let temp = Temp::new();
    std::fs::create_dir(temp.0.join("actual")).unwrap();
    symlink(temp.0.join("actual"), temp.0.join("alias")).unwrap();
    assert!(Dir::open(&temp.0.join("alias/new"), true).is_err());
    assert!(!temp.0.join("actual/new").exists());
}
#[test]
fn replaced_file_is_not_overwritten() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    dir.publish("data", b"old", None, false, ".owned-").unwrap();
    let (_, stamp) = dir.read("data", 100, false).unwrap();
    std::fs::remove_file(temp.0.join("data")).unwrap();
    dir.publish("data", b"external", None, false, ".owned-")
        .unwrap();
    assert!(
        dir.publish("data", b"ours", stamp.as_ref(), false, ".owned-")
            .is_err()
    );
    assert_eq!(std::fs::read(temp.0.join("data")).unwrap(), b"external");
    assert!(!std::fs::read_dir(&temp.0).unwrap().any(|entry| {
        entry
            .unwrap()
            .file_name()
            .to_string_lossy()
            .starts_with(".owned-")
    }));
}
#[test]
fn readonly_and_public_data_are_preserved() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    dir.publish("data", b"keep", None, false, ".owned-")
        .unwrap();
    std::fs::set_permissions(temp.0.join("data"), std::fs::Permissions::from_mode(0o400)).unwrap();
    let (_, stamp) = dir.read("data", 100, false).unwrap();
    assert!(
        dir.publish("data", b"no", stamp.as_ref(), false, ".owned-")
            .is_err()
    );
    std::fs::set_permissions(temp.0.join("data"), std::fs::Permissions::from_mode(0o644)).unwrap();
    assert!(dir.read("data", 100, false).is_err());
}
#[test]
fn lock_timeout_and_replaced_lock_are_safe() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    let _guard = dir.lock("lock").unwrap();
    let start = Instant::now();
    assert!(dir.lock("lock").is_err());
    assert!(start.elapsed() < Duration::from_secs(2));
}
#[test]
fn bounded_read_and_noreplace_publish() {
    let temp = Temp::new();
    let dir = Dir::open(&temp.0, false).unwrap();
    dir.publish("data", b"123456", None, false, ".owned-")
        .unwrap();
    assert!(dir.read("data", 4, false).is_err());
    assert!(dir.publish("data", b"new", None, false, ".owned-").is_err());
}
