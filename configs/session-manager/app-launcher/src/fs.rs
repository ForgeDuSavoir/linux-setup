//! Linux directory capabilities: no symlink traversal, bounded reads, stable locks.
use std::ffi::{CString, OsStr};
use std::fs::{File, Metadata};
use std::io::{self, Read, Write};
use std::os::fd::{AsRawFd, FromRawFd};
use std::os::unix::{ffi::OsStrExt, fs::MetadataExt};
use std::path::{Component, Path};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

fn name(value: &OsStr) -> io::Result<CString> {
    let bytes = value.as_bytes();
    if bytes.is_empty() || bytes == b"." || bytes == b".." || bytes.contains(&b'/') {
        return Err(io::Error::other("unsafe path component"));
    }
    CString::new(bytes).map_err(io::Error::other)
}
fn owned(meta: &Metadata) -> io::Result<()> {
    if meta.uid() != unsafe { libc::geteuid() } {
        return Err(io::Error::other("file/directory belongs to another user"));
    }
    Ok(())
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Identity {
    pub dev: u64,
    pub ino: u64,
}
pub fn identity(meta: &Metadata) -> Identity {
    Identity {
        dev: meta.dev(),
        ino: meta.ino(),
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Stamp {
    id: Identity,
    size: u64,
    modified: (i64, i64),
    changed: (i64, i64),
    pub mode: u32,
}
fn stamp(meta: &Metadata) -> Stamp {
    Stamp {
        id: identity(meta),
        size: meta.len(),
        modified: (meta.mtime(), meta.mtime_nsec()),
        changed: (meta.ctime(), meta.ctime_nsec()),
        mode: meta.mode(),
    }
}

pub struct Dir(File);
impl Dir {
    pub fn open(path: &Path, create: bool) -> io::Result<Self> {
        if !path.is_absolute() {
            return Err(io::Error::other("directory must be absolute"));
        }
        let mut dir = Self(File::open("/")?);
        for part in path.components() {
            match part {
                Component::RootDir => {}
                Component::Normal(p) => dir = dir.child(p, create)?,
                _ => return Err(io::Error::other("noncanonical directory path")),
            }
        }
        Ok(dir)
    }
    pub fn child(&self, value: &OsStr, create: bool) -> io::Result<Self> {
        let value = name(value)?;
        let flags = libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_RDONLY;
        let mut fd = unsafe { libc::openat(self.0.as_raw_fd(), value.as_ptr(), flags) };
        if fd < 0 && create && io::Error::last_os_error().kind() == io::ErrorKind::NotFound {
            if self.0.metadata()?.mode() & 0o200 == 0 {
                return Err(io::Error::other("directory is read-only"));
            }
            let result = unsafe { libc::mkdirat(self.0.as_raw_fd(), value.as_ptr(), 0o700) };
            if result < 0 && io::Error::last_os_error().kind() != io::ErrorKind::AlreadyExists {
                return Err(io::Error::last_os_error());
            }
            fd = unsafe { libc::openat(self.0.as_raw_fd(), value.as_ptr(), flags) };
        }
        if fd < 0 {
            return Err(io::Error::last_os_error());
        }
        // SAFETY: newly opened descriptor, transferred exactly once to File.
        Ok(Self(unsafe { File::from_raw_fd(fd) }))
    }
    pub fn own(&self) -> io::Result<()> {
        owned(&self.0.metadata()?)
    }
    pub fn id(&self) -> io::Result<Identity> {
        Ok(identity(&self.0.metadata()?))
    }
    fn file(&self, value: &OsStr, flags: i32, public: bool) -> io::Result<File> {
        let value = name(value)?;
        let fd = unsafe {
            libc::openat(
                self.0.as_raw_fd(),
                value.as_ptr(),
                flags | libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC,
                0o600,
            )
        };
        if fd < 0 {
            return Err(io::Error::last_os_error());
        }
        let file = unsafe { File::from_raw_fd(fd) };
        validate(&file.metadata()?, public)?;
        Ok(file)
    }
    pub fn read(
        &self,
        value: &str,
        limit: usize,
        public: bool,
    ) -> io::Result<(Option<Vec<u8>>, Option<Stamp>)> {
        let mut file = match self.file(OsStr::new(value), libc::O_RDONLY, public) {
            Ok(f) => f,
            Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok((None, None)),
            Err(e) => return Err(e),
        };
        let before = stamp(&file.metadata()?);
        let mut bytes = Vec::new();
        (&mut file).take(limit as u64 + 1).read_to_end(&mut bytes)?;
        if bytes.len() > limit || stamp(&file.metadata()?) != before {
            return Err(io::Error::other("oversized or changing file"));
        }
        Ok((Some(bytes), Some(before)))
    }
    pub fn current(&self, value: &str, public: bool) -> io::Result<Option<Stamp>> {
        match self.file(OsStr::new(value), libc::O_RDONLY, public) {
            Ok(file) => Ok(Some(stamp(&file.metadata()?))),
            Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(e),
        }
    }
    pub fn lock(&self, value: &str) -> io::Result<Lock> {
        if self.0.metadata()?.mode() & 0o200 == 0 {
            return Err(io::Error::other("directory is read-only"));
        }
        let file = self.file(OsStr::new(value), libc::O_RDWR | libc::O_CREAT, false)?;
        let started = Instant::now();
        loop {
            if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
                break;
            }
            let error = io::Error::last_os_error();
            if error.kind() != io::ErrorKind::WouldBlock {
                return Err(error);
            }
            if started.elapsed() >= Duration::from_secs(1) {
                return Err(io::Error::other("history/exclusion lock deadline exceeded"));
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        if self.current(value, false)?.as_ref().map(|s| &s.id) != Some(&identity(&file.metadata()?))
        {
            return Err(io::Error::other("lock replaced during acquisition"));
        }
        Ok(Lock(file))
    }
    pub fn publish(
        &self,
        value: &str,
        bytes: &[u8],
        expected: Option<&Stamp>,
        public: bool,
        prefix: &str,
    ) -> io::Result<()> {
        if expected.is_some_and(|s| s.mode & 0o200 == 0) {
            return Err(io::Error::other("file is read-only"));
        }
        if self.0.metadata()?.mode() & 0o200 == 0 {
            return Err(io::Error::other("directory is read-only"));
        }
        if self.0.metadata()?.nlink() == 0 {
            return Err(io::Error::other("directory was removed"));
        }
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let temp = format!(
            "{prefix}{}-{}-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_err(io::Error::other)?
                .as_nanos(),
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        );
        let mut file = self.file(
            OsStr::new(&temp),
            libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL,
            false,
        )?;
        let tmp = name(OsStr::new(&temp))?;
        let target = name(OsStr::new(value))?;
        let result = (|| {
            file.write_all(bytes)?;
            if public {
                use std::os::unix::fs::PermissionsExt;
                file.set_permissions(std::fs::Permissions::from_mode(
                    expected.map(|s| s.mode & 0o777).unwrap_or(0o600),
                ))?;
            }
            file.sync_all()?;
            if self.current(value, public)?.as_ref() != expected {
                return Err(io::Error::other("file changed before publication"));
            }
            let flags = if expected.is_none() {
                libc::RENAME_NOREPLACE
            } else {
                0
            };
            if unsafe {
                libc::renameat2(
                    self.0.as_raw_fd(),
                    tmp.as_ptr(),
                    self.0.as_raw_fd(),
                    target.as_ptr(),
                    flags,
                )
            } < 0
            {
                return Err(io::Error::last_os_error());
            }
            self.0.sync_all()
        })();
        // This invocation owns only this O_EXCL-created temporary name.
        unsafe { libc::unlinkat(self.0.as_raw_fd(), tmp.as_ptr(), 0) };
        result
    }
}
fn validate(meta: &Metadata, public: bool) -> io::Result<()> {
    owned(meta)?;
    if !meta.is_file()
        || meta.nlink() != 1
        || (!public && meta.mode() & 0o077 != 0)
        || meta.mode() & 0o022 != 0
    {
        return Err(io::Error::other("unsafe file type, links or permissions"));
    }
    Ok(())
}
pub struct Lock(File);
impl Drop for Lock {
    fn drop(&mut self) {
        unsafe { libc::flock(self.0.as_raw_fd(), libc::LOCK_UN) };
    }
}

#[cfg(test)]
#[path = "fs_tests.rs"]
mod tests;
