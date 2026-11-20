//! SUPER+E only: confirmed project directory or HOME, then the standard opener once.
use crate::{
    Result,
    core::{self, SessionId, Sessions, Source},
    notify::{self, Context},
    pi, process,
};
use serde_json::Value;
use std::{
    ffi::CString,
    fs,
    os::unix::{ffi::OsStrExt, fs::MetadataExt},
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};
pub const PROBE_TIMEOUT: Duration = Duration::from_secs(2);

#[derive(Debug, PartialEq)]
pub struct ProjectContext {
    pub id: SessionId,
    pub name: String,
}
pub fn project_context(value: &Value) -> Result<Option<ProjectContext>> {
    let context = notify::confirmed_context(value)?;
    let sessions = Sessions::parse(value)?;
    let Some(active) = sessions.active_session_id else {
        return Ok(None);
    };
    if context != Context::Session(active.0.clone()) {
        return Err("inconsistent desktop origin".into());
    }
    let row = sessions
        .sessions
        .into_iter()
        .find(|s| s.id == active)
        .ok_or("active session missing")?;
    match row.source {
        Source::Neutral {} => Ok(None),
        Source::Project { project_name } => Ok(Some(ProjectContext {
            id: active,
            name: project_name,
        })),
    }
}
fn status(home: &Path) -> Result<Value> {
    let out = process::run(
        Command::new(home.join(".local/bin/session-desktop")).arg("status"),
        None,
        true,
        Some(PROBE_TIMEOUT),
    )?;
    if !out.status.success() {
        return Err("desktop status unavailable".into());
    }
    serde_json::from_slice(&out.stdout).map_err(|_| "invalid desktop status".into())
}
fn directory_identity(path: &Path) -> Result<(u64, u64)> {
    pi::validate_directory(path)?;
    // Open the directory without enumerating its contents; confirm browse access.
    drop(fs::read_dir(path).map_err(|_| "project directory is unreadable")?);
    let name = CString::new(path.as_os_str().as_bytes()).map_err(|_| "invalid directory")?;
    // SAFETY: live NUL-terminated path, no retained pointers. Check effective access.
    if unsafe { libc::faccessat(libc::AT_FDCWD, name.as_ptr(), libc::X_OK, libc::AT_EACCESS) } != 0
    {
        return Err("project directory is not searchable".into());
    }
    let meta = fs::metadata(path).map_err(|_| "project directory unavailable")?;
    Ok((meta.dev(), meta.ino()))
}
fn project_directory(home: &Path) -> Result<PathBuf> {
    let first = project_context(&status(home)?)?.ok_or("no project context")?;
    let catalogue = core::query_json(
        &home.join(".local/bin/session-manager"),
        &["project", "list"],
        PROBE_TIMEOUT,
    )?;
    if catalogue["projects"]
        .as_array()
        .is_none_or(|rows| rows.iter().filter(|p| p["name"] == first.name).count() != 1)
    {
        return Err("ambiguous project catalogue".into());
    }
    let path = core::project_path(&catalogue, &first.name)?;
    let path: PathBuf = path.components().collect();
    let identity = directory_identity(&path)?;
    // Freeze the launch request, but do not open a stale project after a context switch.
    if project_context(&status(home)?)?.as_ref() != Some(&first)
        || directory_identity(&path)? != identity
    {
        return Err("project/context changed while routing".into());
    }
    Ok(path)
}
pub fn destination(home: &Path) -> Result<PathBuf> {
    if !home.is_absolute() || !home.is_dir() {
        return Err("HOME must be an existing absolute directory".into());
    }
    // Unavailable/unknown context is explicitly a HOME request, not a failed launch.
    Ok(project_directory(home).unwrap_or_else(|_| home.to_owned()))
}
pub fn launch(path: &Path) -> Result<()> {
    let status = Command::new("xdg-open")
        .arg(path)
        .status()
        .map_err(|e| format!("cannot start default file manager: {e}"))?;
    if !status.success() {
        return Err("default file manager failed; no second launch/retry".into());
    }
    Ok(())
}
