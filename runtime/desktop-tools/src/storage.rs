//! One flock at the outer boundary. Directory-relative atomic state publication.
use crate::{Result, state::State};
use serde_json::Value;
use std::{
    ffi::CString,
    fs::{File, OpenOptions},
    io::{Read, Write},
    os::{
        fd::{AsRawFd, FromRawFd},
        unix::fs::{MetadataExt, OpenOptionsExt},
    },
    path::Path,
    sync::atomic::{AtomicU64, Ordering},
};

pub trait Store {
    fn read(&mut self) -> Result<Option<Value>>;
    fn save(&mut self, state: &State) -> Result<()>;
}
static COUNTER: AtomicU64 = AtomicU64::new(0);
fn error(e: impl std::fmt::Display) -> String {
    e.to_string()
}
fn regular(file: &File) -> Result<()> {
    let metadata = file.metadata().map_err(error)?;
    // SAFETY: geteuid has no pointer arguments.
    if !metadata.is_file() || metadata.nlink() != 1 || metadata.uid() != unsafe { libc::geteuid() }
    {
        return Err("unsafe nonregular, linked or foreign state/lock".into());
    }
    Ok(())
}
pub struct LockedStore {
    directory: File,
    _lock: Option<File>,
}
impl LockedStore {
    pub fn open(runtime: &Path) -> Result<Self> {
        std::fs::create_dir_all(runtime).map_err(error)?;
        let directory = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC)
            .open(runtime)
            .map_err(error)?;
        let mut store = Self {
            directory,
            _lock: None,
        };
        let lock = store
            .openat("workspace-columns.lock", libc::O_RDWR | libc::O_CREAT)
            .map_err(error)?;
        regular(&lock)?;
        loop {
            // SAFETY: lock owns a live fd; flock has no pointers.
            if unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX) } == 0 {
                break;
            }
            let e = std::io::Error::last_os_error();
            if e.kind() != std::io::ErrorKind::Interrupted {
                return Err(error(e));
            }
        }
        store._lock = Some(lock);
        Ok(store)
    }
    fn openat(&self, name: &str, flags: i32) -> std::io::Result<File> {
        let name = CString::new(name)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidInput, e))?;
        // SAFETY: directory owns fd, name is a live NUL-terminated string.
        let fd = unsafe {
            libc::openat(
                self.directory.as_raw_fd(),
                name.as_ptr(),
                flags | libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC,
                0o600,
            )
        };
        if fd < 0 {
            return Err(std::io::Error::last_os_error());
        }
        // SAFETY: openat returned a new descriptor transferred exactly once.
        Ok(unsafe { File::from_raw_fd(fd) })
    }
    fn named_exists(&self, name: &str) -> Result<bool> {
        let name = CString::new(name).map_err(error)?;
        let mut info = std::mem::MaybeUninit::<libc::stat>::uninit();
        // SAFETY: valid directory/name, output initialized by successful fstatat.
        let result = unsafe {
            libc::fstatat(
                self.directory.as_raw_fd(),
                name.as_ptr(),
                info.as_mut_ptr(),
                libc::AT_SYMLINK_NOFOLLOW,
            )
        };
        if result < 0 {
            let e = std::io::Error::last_os_error();
            if e.kind() == std::io::ErrorKind::NotFound {
                return Ok(false);
            }
            return Err(error(e));
        }
        Ok(true)
    }
}
impl Store for LockedStore {
    fn read(&mut self) -> Result<Option<Value>> {
        if !self.named_exists("workspace-columns.json")? {
            return Ok(None);
        }
        let mut file = self
            .openat("workspace-columns.json", libc::O_RDONLY)
            .map_err(error)?;
        regular(&file)?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes).map_err(error)?;
        serde_json::from_slice(&bytes).map(Some).map_err(error)
    }
    fn save(&mut self, state: &State) -> Result<()> {
        self.publish(state, || Ok(()))
    }
}
impl LockedStore {
    // Private pre-publication seam for deterministic crash/write-failure tests.
    fn publish(
        &mut self,
        state: &State,
        before_publish: impl FnOnce() -> Result<()>,
    ) -> Result<()> {
        state.validate()?;
        self.publish_bytes(
            "workspace-columns.json",
            ".workspace-list-",
            &serde_json::to_vec(state).map_err(error)?,
            before_publish,
        )
    }
    fn publish_bytes(
        &mut self,
        target: &str,
        prefix: &str,
        bytes: &[u8],
        before_publish: impl FnOnce() -> Result<()>,
    ) -> Result<()> {
        if self.named_exists(target)? {
            regular(&self.openat(target, libc::O_RDONLY).map_err(error)?)?;
        }
        let target = CString::new(target).map_err(error)?;
        let mut temporary = None;
        for _ in 0..128 {
            let name = format!(
                "{prefix}{}-{}",
                std::process::id(),
                COUNTER.fetch_add(1, Ordering::Relaxed)
            );
            match self.openat(&name, libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL) {
                Ok(file) => {
                    temporary = Some((name, file));
                    break;
                }
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
                Err(e) => return Err(error(e)),
            }
        }
        let (name, mut file) = temporary.ok_or("cannot create exclusive workspace temporary")?;
        let c_name = CString::new(name).map_err(error)?;
        let result = (|| {
            file.write_all(bytes).map_err(error)?;
            file.sync_all().map_err(error)?;
            before_publish()?;
            // SAFETY: both relative names and directory descriptor remain live.
            if unsafe {
                libc::renameat(
                    self.directory.as_raw_fd(),
                    c_name.as_ptr(),
                    self.directory.as_raw_fd(),
                    target.as_ptr(),
                )
            } < 0
            {
                return Err(error(std::io::Error::last_os_error()));
            }
            // A failure after publication is reported, never rolled back/replayed.
            self.directory
                .sync_all()
                .map_err(|e| format!("state publication uncertain: {e}"))
        })();
        // SAFETY: remove only our own exclusive temporary (possibly already renamed).
        unsafe { libc::unlinkat(self.directory.as_raw_fd(), c_name.as_ptr(), 0) };
        result
    }
}
impl crate::startup::StartupStore for LockedStore {
    fn marker(&mut self) -> Result<Option<Value>> {
        if !self.named_exists("session-startup.json")? {
            return Ok(None);
        }
        let mut file = self
            .openat("session-startup.json", libc::O_RDONLY)
            .map_err(error)?;
        regular(&file)?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes).map_err(error)?;
        serde_json::from_slice(&bytes).map(Some).map_err(error)
    }
    fn write_marker(&mut self, marker: &crate::startup::Marker) -> Result<()> {
        self.publish_bytes(
            "session-startup.json",
            ".session-startup-",
            &serde_json::to_vec(marker).map_err(error)?,
            || Ok(()),
        )
    }
    fn backup(&mut self, before: &Value) -> Result<()> {
        let mut previous = None;
        if self.named_exists("workspace-columns.json")? {
            let mut file = self
                .openat("workspace-columns.json", libc::O_RDONLY)
                .map_err(error)?;
            regular(&file)?;
            let mut bytes = Vec::new();
            file.read_to_end(&mut bytes).map_err(error)?;
            previous = Some(bytes);
        }
        let mut backup = None;
        for _ in 0..128 {
            let name = CString::new(format!(
                "session-startup-backup-{}-{}",
                std::process::id(),
                COUNTER.fetch_add(1, Ordering::Relaxed)
            ))
            .map_err(error)?;
            // SAFETY: live parent fd and NUL-terminated unique relative name.
            if unsafe { libc::mkdirat(self.directory.as_raw_fd(), name.as_ptr(), 0o700) } == 0 {
                backup = Some(
                    self.openat(
                        name.to_str().map_err(error)?,
                        libc::O_RDONLY | libc::O_DIRECTORY,
                    )
                    .map_err(error)?,
                );
                break;
            }
            let e = std::io::Error::last_os_error();
            if e.kind() != std::io::ErrorKind::AlreadyExists {
                return Err(error(e));
            }
        }
        let backup = backup.ok_or("cannot create private startup backup")?;
        let mut entries = vec![(
            "core-before.json",
            serde_json::to_vec(before).map_err(error)?,
        )];
        if let Some(bytes) = previous {
            entries.push(("workspace-state.json", bytes));
        }
        for (name, bytes) in entries {
            let name = CString::new(name).map_err(error)?;
            // SAFETY: backup owns directory fd; name is live and contains no slash.
            let fd = unsafe {
                libc::openat(
                    backup.as_raw_fd(),
                    name.as_ptr(),
                    libc::O_WRONLY
                        | libc::O_CREAT
                        | libc::O_EXCL
                        | libc::O_CLOEXEC
                        | libc::O_NOFOLLOW,
                    0o600,
                )
            };
            if fd < 0 {
                return Err(error(std::io::Error::last_os_error()));
            }
            // SAFETY: new descriptor ownership transferred once.
            let mut file = unsafe { File::from_raw_fd(fd) };
            file.write_all(&bytes).map_err(error)?;
            file.sync_all().map_err(error)?;
        }
        backup.sync_all().map_err(error)?;
        self.directory.sync_all().map_err(error)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn interrupted_before_publication_preserves_previous_and_cleans_own_temp() {
        let tmp = crate::tests::Temp::new();
        let mut store = LockedStore::open(&tmp.0).unwrap();
        let state = crate::tests::state();
        store.save(&state).unwrap();
        let before = std::fs::read(tmp.0.join("workspace-columns.json")).unwrap();
        let mut replacement = state.clone();
        replacement.next_id = 99;
        assert!(
            store
                .publish(&replacement, || Err(
                    "injected failure after write/fsync".into()
                ))
                .is_err()
        );
        assert_eq!(
            std::fs::read(tmp.0.join("workspace-columns.json")).unwrap(),
            before
        );
        assert!(!std::fs::read_dir(&tmp.0).unwrap().any(|entry| {
            entry
                .unwrap()
                .file_name()
                .to_string_lossy()
                .starts_with(".workspace-list-")
        }));
    }
}
