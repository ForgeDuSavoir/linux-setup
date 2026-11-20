//! Read-only Rust equivalent of the documented desktop status contract.
use crate::{
    Application, Client, Metadata, Origin, Projects, Result, Sessions, Source, fs, history, process,
};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::fs::OpenOptions;
use std::io::Read;
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Binding {
    pub active: Option<(String, Source)>,
    pub project: Option<(PathBuf, fs::Identity)>,
}
pub struct Snapshot {
    pub binding: Binding,
    pub choices: Vec<Choice>,
    _project_directory: Option<fs::Dir>, // Keep the inode alive while a menu is open.
}
pub struct Choice {
    pub app: Application,
    pub info: Metadata,
    pub token: Token,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Token {
    path: Option<PathBuf>,
    identity: Option<(u64, u64, u32, u64, [u8; 32])>,
}
impl Token {
    fn capture(app: &Application, project: Option<&Path>) -> Result<Self> {
        let path = match app.origin {
            Origin::Installed => {
                gio::DesktopAppInfo::new(&app.id).and_then(|entry| entry.filename())
            }
            Origin::Project => Some(
                project
                    .ok_or("project entry without a project")?
                    .join(".session-manager/apps")
                    .join(&app.id),
            ),
        };
        let Some(path) = path else {
            return Ok(Self {
                path: None,
                identity: None,
            });
        };
        if app.origin == Origin::Project && path.is_symlink() {
            return Err("symlinked project desktop entry".into());
        }
        let mut file = match OpenOptions::new()
            .read(true)
            .custom_flags(
                libc::O_NONBLOCK
                    | libc::O_CLOEXEC
                    | if app.origin == Origin::Project {
                        libc::O_NOFOLLOW
                    } else {
                        0
                    },
            )
            .open(&path)
        {
            Ok(f) => f,
            Err(e)
                if e.kind() == std::io::ErrorKind::NotFound && app.origin == Origin::Installed =>
            {
                return Ok(Self {
                    path: Some(path),
                    identity: None,
                });
            }
            Err(e) => return Err(e.to_string()),
        };
        let before = file.metadata().map_err(|e| e.to_string())?;
        if !before.is_file() || before.len() > history::LIMIT as u64 {
            return Err("invalid/oversized desktop entry".into());
        }
        let mut bytes = Vec::new();
        (&mut file)
            .take(history::LIMIT as u64 + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| e.to_string())?;
        if bytes.len() > history::LIMIT {
            return Err("desktop entry grew beyond limit".into());
        }
        let after = file.metadata().map_err(|e| e.to_string())?;
        if (
            before.dev(),
            before.ino(),
            before.len(),
            before.mtime(),
            before.mtime_nsec(),
            before.ctime(),
            before.ctime_nsec(),
        ) != (
            after.dev(),
            after.ino(),
            after.len(),
            after.mtime(),
            after.mtime_nsec(),
            after.ctime(),
            after.ctime_nsec(),
        ) {
            return Err("desktop entry changed while hashing".into());
        }
        let digest: [u8; 32] = Sha256::digest(&bytes).into();
        Ok(Self {
            path: Some(path),
            identity: Some((
                before.dev(),
                before.ino(),
                before.mode(),
                before.len(),
                digest,
            )),
        })
    }
}
#[derive(Deserialize)]
struct Workspace {
    #[serde(default)]
    id: i64,
    #[serde(default)]
    name: String,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Monitor {
    focused: bool,
    active_workspace: Workspace,
    special_workspace: Workspace,
}
#[derive(Deserialize)]
struct Desktop {
    version: u64,
    owners: std::collections::BTreeMap<String, String>,
}

impl Client {
    fn confirmed(&self) -> Result<Sessions> {
        let before: Sessions = self.query(&["session", "list"])?;
        let mut ids = std::collections::HashSet::new();
        for item in &before.sessions {
            if item.id.is_empty() || !ids.insert(&item.id) {
                return Err("invalid session identities".into());
            }
        }
        if before
            .active_session_id
            .as_ref()
            .is_some_and(|id| !ids.contains(id))
        {
            return Err("unknown active session".into());
        }
        let runtime = std::env::var_os("XDG_RUNTIME_DIR")
            .map(PathBuf::from)
            .filter(|p| p.is_absolute())
            .ok_or("XDG_RUNTIME_DIR must be absolute")?;
        let metadata = runtime.join("hyprland/workspace-columns.json");
        let raw = read_desktop(&metadata)?;
        let output = process::run(
            Command::new("hyprctl").args(["-j", "monitors"]),
            None,
            true,
            Some(Duration::from_secs(5)),
        )?;
        if !output.status.success() {
            return Err("desktop status unavailable".into());
        }
        let monitors: Vec<Monitor> =
            serde_json::from_slice(&output.stdout).map_err(|_| "invalid monitor snapshot")?;
        let monitor = monitors
            .iter()
            .find(|m| m.focused)
            .or_else(|| {
                if monitors.len() == 1 {
                    monitors.first()
                } else {
                    None
                }
            })
            .ok_or("no focused monitor")?;
        let ws = monitor.active_workspace.id;
        if ws <= 0 || ws > 2_147_483_646 {
            return Err("unknown ordinary workspace".into());
        }
        let owner = if let Some(bytes) = &raw {
            let state: Desktop =
                serde_json::from_slice(bytes).map_err(|_| "invalid desktop metadata")?;
            let key = match state.version {
                3 => ws,
                2 => (ws + 1) / 2,
                _ => return Err("unsupported desktop metadata".into()),
            };
            state
                .owners
                .get(&key.to_string())
                .cloned()
                .unwrap_or_else(|| "neutral".into())
        } else {
            "neutral".into()
        };
        let special = &monitor.special_workspace.name;
        let mismatched_scope = special
            .strip_prefix("special:sm-")
            .and_then(|s| s.rsplit_once('-'))
            .is_some_and(|(id, slot)| {
                ["ai", "notes", "tasks", "4", "5"].contains(&slot) && id != owner
            });
        if owner != before.active_session_id.as_deref().unwrap_or("neutral")
            || mismatched_scope
            || (special.starts_with("special:session-") && owner != "neutral")
        {
            return Err(
                "logical session and displayed desktop differ; select a confirmed session".into(),
            );
        }
        if read_desktop(&metadata)? != raw {
            return Err("desktop metadata changed during snapshot".into());
        }
        Ok(before)
    }
    pub fn snapshot(&self) -> Result<Snapshot> {
        let before = self.confirmed()?;
        let active = before
            .active_session_id
            .as_ref()
            .map(|id| {
                before
                    .sessions
                    .iter()
                    .find(|s| &s.id == id)
                    .map(|s| (s.id.clone(), s.source.clone()))
                    .ok_or("unknown active session")
            })
            .transpose()?;
        let mut project_directory = None;
        let project = match active.as_ref().map(|(_, s)| s) {
            Some(Source::Project { project_name }) => {
                let projects: Projects = self.query(&["project", "list"])?;
                let path = &projects
                    .projects
                    .iter()
                    .find(|p| &p.name == project_name)
                    .ok_or("project missing; reopen launcher")?
                    .path;
                if !path.is_absolute() {
                    return Err("project path must be absolute".into());
                }
                let canonical = path.canonicalize().map_err(|e| e.to_string())?;
                let dir = fs::Dir::open(&canonical, false).map_err(|e| e.to_string())?;
                let id = dir.id().map_err(|e| e.to_string())?;
                project_directory = Some(dir);
                Some((canonical, id))
            }
            _ => None,
        };
        let mut choices = Vec::new();
        for app in self.applications()? {
            if app.origin == Origin::Project && project.is_none() {
                return Err("project entry outside project context".into());
            }
            let path = project.as_ref().map(|(p, _)| p.as_path());
            let token = Token::capture(&app, path)?;
            let info = Metadata::read(&app, path);
            if token != Token::capture(&app, path)? {
                return Err("desktop entry changed during metadata read".into());
            }
            choices.push(Choice { app, info, token });
        }
        let after = self.confirmed()?;
        if after.revision != before.revision
            || after.active_session_id != before.active_session_id
            || after.sessions != before.sessions
        {
            return Err("session state changed during snapshot".into());
        }
        Ok(Snapshot {
            binding: Binding { active, project },
            choices,
            _project_directory: project_directory,
        })
    }
    pub fn revalidate(&self, original: &Binding, chosen: &Choice) -> Result<()> {
        let fresh = self.snapshot()?;
        if &fresh.binding != original {
            return Err("context changed; reopen launcher".into());
        }
        let entry = fresh
            .choices
            .iter()
            .find(|c| c.app.id == chosen.app.id)
            .ok_or("application no longer available")?;
        if entry.app != chosen.app || entry.token != chosen.token {
            return Err("desktop entry changed; reopen launcher".into());
        }
        Ok(())
    }
}
fn read_desktop(path: &Path) -> Result<Option<Vec<u8>>> {
    let file = match OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC)
        .open(path)
    {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e.to_string()),
    };
    if !file.metadata().map_err(|e| e.to_string())?.is_file() {
        return Err("desktop metadata is not regular".into());
    }
    let mut bytes = Vec::new();
    file.take(history::LIMIT as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() > history::LIMIT {
        return Err("desktop metadata exceeds limit".into());
    }
    Ok(Some(bytes))
}
