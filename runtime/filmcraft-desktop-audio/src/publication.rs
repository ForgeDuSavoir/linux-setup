//! Linux publication: no-clobber WAV, project exchange retaining the displaced version.
use crate::Result;
use std::{
    ffi::CString,
    fs::{self, File, OpenOptions},
    io::{Read, Seek, SeekFrom},
    os::{
        fd::AsRawFd,
        unix::{
            ffi::OsStrExt,
            fs::{MetadataExt, OpenOptionsExt, PermissionsExt},
        },
    },
    path::{Path, PathBuf},
};
fn open(path: &Path) -> Result<File> {
    let file = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)?;
    if !file.metadata()?.is_file() {
        return Err("Fichier régulier requis".into());
    }
    Ok(file)
}
#[derive(PartialEq, Eq)]
struct Stamp {
    dev: u64,
    ino: u64,
    len: u64,
    mtime: (i64, i64),
    ctime: (i64, i64),
}
fn stamp(file: &File) -> Result<Stamp> {
    let m = file.metadata()?;
    Ok(Stamp {
        dev: m.dev(),
        ino: m.ino(),
        len: m.len(),
        mtime: (m.mtime(), m.mtime_nsec()),
        ctime: (m.ctime(), m.ctime_nsec()),
    })
}
fn same_inode(path: &Path, file: &File) -> bool {
    let Ok(p) = path.symlink_metadata() else {
        return false;
    };
    let Ok(f) = file.metadata() else {
        return false;
    };
    p.is_file() && p.dev() == f.dev() && p.ino() == f.ino()
}
fn contents(file: &File) -> Result<Vec<u8>> {
    let mut fd = file.try_clone()?;
    fd.seek(SeekFrom::Start(0))?;
    let mut bytes = Vec::new();
    fd.read_to_end(&mut bytes)?;
    Ok(bytes)
}
pub struct Temporary {
    pub path: PathBuf,
    file: File,
    snapshot: Stamp,
    retain: bool,
}
impl Temporary {
    pub fn new(parent: &Path, prefix: &str, suffix: &str) -> Result<Self> {
        let template = parent.join(format!("{prefix}XXXXXX{suffix}"));
        let mut bytes = CString::new(template.as_os_str().as_bytes())?.into_bytes_with_nul();
        let fd = unsafe {
            libc::mkostemps(
                bytes.as_mut_ptr().cast(),
                suffix.len().try_into()?,
                libc::O_CLOEXEC,
            )
        };
        if fd < 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        use std::os::fd::FromRawFd;
        let file = unsafe { File::from_raw_fd(fd) };
        let path = PathBuf::from(std::ffi::OsStr::from_bytes(&bytes[..bytes.len() - 1]));
        let snapshot = stamp(&file)?;
        Ok(Self {
            path,
            file,
            snapshot,
            retain: false,
        })
    }
    pub fn refresh(&mut self) -> Result<()> {
        let file = open(&self.path)?;
        if file.metadata()?.nlink() != 1 {
            return Err("Temporaire lié à un autre fichier".into());
        }
        self.snapshot = stamp(&file)?;
        self.file = file;
        Ok(())
    }
    pub fn verify(&self) -> Result<()> {
        if !same_inode(&self.path, &self.file) || stamp(&self.file)? != self.snapshot {
            return Err("Temporaire modifié après validation".into());
        }
        Ok(())
    }
    pub fn bytes(&self) -> Result<Vec<u8>> {
        self.verify()?;
        let bytes = contents(&self.file)?;
        self.verify()?;
        Ok(bytes)
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        if !self.retain && same_inode(&self.path, &self.file) {
            let _ = fs::remove_file(&self.path);
        }
    }
}
pub struct Original {
    path: PathBuf,
    file: File,
    stamp: Stamp,
    pub bytes: Vec<u8>,
}
impl Original {
    pub fn open(path: &Path) -> Result<Self> {
        let mut file = open(path)?;
        if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return Err("Projet déjà verrouillé par un autre correctif".into());
        }
        let old = stamp(&file)?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;
        if stamp(&file)? != old || !same_inode(path, &file) {
            return Err("Projet modifié pendant la lecture".into());
        }
        Ok(Self {
            path: path.into(),
            file,
            stamp: old,
            bytes,
        })
    }
    pub fn verify(&self) -> Result<()> {
        if !same_inode(&self.path, &self.file)
            || stamp(&self.file)? != self.stamp
            || contents(&self.file)? != self.bytes
            || stamp(&self.file)? != self.stamp
            || !same_inode(&self.path, &self.file)
        {
            return Err("Projet modifié concurremment ; publication refusée".into());
        }
        Ok(())
    }
    pub fn exchange(&self, temp: &mut Temporary) -> Result<PathBuf> {
        self.verify()?;
        temp.verify()?;
        temp.file.set_permissions(fs::Permissions::from_mode(
            self.file.metadata()?.permissions().mode() & 0o777,
        ))?;
        temp.file.sync_all()?;
        let a = CString::new(temp.path.as_os_str().as_bytes())?;
        let b = CString::new(self.path.as_os_str().as_bytes())?;
        if unsafe {
            libc::renameat2(
                libc::AT_FDCWD,
                a.as_ptr(),
                libc::AT_FDCWD,
                b.as_ptr(),
                libc::RENAME_EXCHANGE,
            )
        } != 0
        {
            let error = std::io::Error::last_os_error();
            if same_inode(&temp.path, &self.file) {
                temp.retain = true;
            }
            return Err(format!("Échange projet non acquitté ({error}) ; inspecter le projet et la version éventuelle conservée : {}",temp.path.display()).into());
        }
        // The public project is now committed. Never drop/unlink the displaced file,
        // even on sync/inspection failure, and never automatically exchange back.
        temp.retain = true;
        let backup = temp.path.clone();
        let fail = |reason: &str| {
            format!(
                "Publication projet effectuée, résultat incertain ({reason}) ; version déplacée conservée : {}",
                backup.display()
            )
        };
        if !same_inode(&backup, &self.file)
            || !same_inode(&self.path, &temp.file)
            || contents(&self.file).map_err(|_| fail("lecture sauvegarde"))? != self.bytes
        {
            return Err(fail("écriture concurrente tardive").into());
        }
        File::open(self.path.parent().unwrap())
            .and_then(|directory| directory.sync_all())
            .map_err(|_| fail("fsync dossier"))?;
        Ok(backup)
    }
}
pub struct Published {
    path: PathBuf,
    file: File,
    stamp: Stamp,
}
impl Published {
    pub fn create(temp: &Temporary, path: &Path) -> Result<Self> {
        temp.verify()?;
        temp.file.sync_all()?;
        fs::hard_link(&temp.path, path).map_err(|e| {
            format!("WAV non publié, destination préexistante/concurrente ou erreur : {e}")
        })?;
        let file = temp.file.try_clone()?;
        let partial = |e: &str| {
            format!(
                "WAV publié ou incertain, conservé : {} ; {e}. Inspecter avant reprise.",
                path.display()
            )
        };
        if !same_inode(path, &file) {
            return Err(partial("destination modifiée pendant la publication").into());
        }
        let s = stamp(&file).map_err(|e| partial(e.to_string().as_str()))?;
        File::open(path.parent().unwrap())
            .and_then(|d| d.sync_all())
            .map_err(|e| partial(e.to_string().as_str()))?;
        Ok(Self {
            path: path.into(),
            file,
            stamp: s,
        })
    }
    pub fn verify(&self) -> Result<()> {
        if !same_inode(&self.path, &self.file) || stamp(&self.file)? != self.stamp {
            return Err("WAV publié modifié concurremment ; projet non publié".into());
        }
        Ok(())
    }
}
