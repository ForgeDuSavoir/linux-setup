//! Contextual menu launch only. Never register/create a vault or rewrite Obsidian state.
use crate::{Result, files, pi};
use serde_json::Value;
use std::{
    ffi::OsString,
    fs::{self, OpenOptions},
    io::Read,
    os::unix::fs::OpenOptionsExt,
    path::{Component, Path, PathBuf},
    process::Command,
};
const LIMIT: u64 = 4 * 1024 * 1024;
fn vault_directory(path: &Path) -> Result<()> {
    pi::validate_directory(path)?;
    if path.components().any(|c| c == Component::ParentDir) {
        return Err("non-normalized vault path".into());
    }
    let config = fs::symlink_metadata(path.join(".obsidian"))
        .map_err(|_| "vault configuration directory unavailable")?;
    if !config.is_dir() {
        return Err("no .obsidian directory at the vault root".into());
    }
    // Check directory readability without reading notes, configuration or plugins.
    drop(fs::read_dir(path).map_err(|_| "vault root unreadable")?);
    Ok(())
}
pub fn registry(config: &Path) -> Result<Value> {
    if !config.is_absolute() {
        return Err("XDG_CONFIG_HOME must be absolute".into());
    }
    let file = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(config.join("obsidian/obsidian.json"))
        .map_err(|_| "Obsidian vault registry unavailable; open the vault once in Obsidian")?;
    let meta = file
        .metadata()
        .map_err(|_| "cannot inspect Obsidian registry")?;
    if !meta.is_file() || meta.len() > LIMIT {
        return Err("invalid or oversized Obsidian registry".into());
    }
    let mut data = Vec::new();
    file.take(LIMIT + 1)
        .read_to_end(&mut data)
        .map_err(|_| "cannot read Obsidian registry")?;
    if data.len() as u64 > LIMIT {
        return Err("oversized Obsidian registry".into());
    }
    serde_json::from_slice(&data).map_err(|_| "invalid Obsidian registry JSON".into())
}
/// Exact root only: never select a known ancestor or match a vault by basename.
pub fn vault_id(registry: &Value, root: &Path) -> Result<String> {
    let rows = registry
        .get("vaults")
        .and_then(Value::as_object)
        .ok_or("invalid Obsidian vault registry")?;
    let mut matches = rows.iter().filter(|(_, v)| {
        v.get("path").and_then(Value::as_str).is_some_and(|p| {
            Path::new(p).is_absolute() && Path::new(p).components().collect::<PathBuf>() == root
        })
    });
    let (id, _) = matches
        .next()
        .ok_or("vault is not registered at this exact root")?;
    if matches.next().is_some() {
        return Err("multiple registered vaults at this root".into());
    }
    if id.len() != 16 || !id.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("invalid registered vault ID".into());
    }
    // Obsidian's URI resolver accepts both IDs and basenames in the same field.
    // Reject even a basename that could shadow this ID in another registry row.
    if rows.iter().any(|(other, v)| {
        other != id
            && v.get("path")
                .and_then(Value::as_str)
                .and_then(|p| Path::new(p).file_name())
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.eq_ignore_ascii_case(id))
    }) {
        return Err("vault ID is shadowed by another vault name".into());
    }
    Ok(id.clone())
}
pub fn arguments(home: &Path, config: &Path, explicit: &[OsString]) -> Result<Vec<OsString>> {
    // Links/files supplied by applications are authoritative, even with no valid HOME/config.
    if !explicit.is_empty() {
        return Ok(explicit.to_vec());
    }
    if !home.is_absolute() {
        return Err("HOME must be absolute".into());
    }
    let known = registry(config)?;
    if let Ok(root) = files::project_directory(home)
        && vault_directory(&root).is_ok()
        && let Ok(id) = vault_id(&known, &root)
    {
        return Ok(vec![format!("obsidian://open?vault={id}").into()]);
    }
    let root = pi::agora_root(config)?;
    vault_directory(&root)?;
    let id = vault_id(&known, &root).map_err(
        |_| "Agora vault is not registered unambiguously; open its root once in Obsidian",
    )?;
    Ok(vec![format!("obsidian://open?vault={id}").into()])
}
pub fn launch(binary: &Path, args: &[OsString]) -> Result<()> {
    launch_scoped(binary, args, false)
}
pub fn launch_in_new_workspace(binary: &Path, args: &[OsString]) -> Result<()> {
    launch_scoped(binary, args, true)
}
fn launch_scoped(binary: &Path, args: &[OsString], fresh: bool) -> Result<()> {
    let mut command = Command::new(binary);
    if fresh {
        command.env_remove("HL_INITIAL_WORKSPACE_TOKEN");
    }
    let status = command
        .args(args)
        .status()
        .map_err(|e| format!("cannot launch Obsidian: {e}"))?;
    if !status.success() {
        return Err("Obsidian launch failed; no fallback launch/retry".into());
    }
    Ok(())
}
