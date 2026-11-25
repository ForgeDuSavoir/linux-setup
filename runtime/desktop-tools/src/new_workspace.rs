//! Explicit Shift launches: prepare, create in the captured owner, confirm, launch once.
use crate::{
    Result,
    core::Sessions,
    files,
    native::{Hyprctl, Native},
    notify, pi, process,
    storage::LockedStore,
    workspace::Controller,
};
use serde_json::Value;
use std::{
    os::unix::fs::{MetadataExt, PermissionsExt},
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Target {
    Browser,
    Pi,
    Files,
    Terminal,
    Apps,
    Youtube,
    Obsidian,
}
impl Target {
    pub fn parse(value: &str) -> Result<Self> {
        match value {
            "browser" => Ok(Self::Browser),
            "pi" => Ok(Self::Pi),
            "files" => Ok(Self::Files),
            "terminal" => Ok(Self::Terminal),
            "apps" => Ok(Self::Apps),
            "youtube" => Ok(Self::Youtube),
            "obsidian" => Ok(Self::Obsidian),
            _ => Err("unknown new-workspace target".into()),
        }
    }
}
#[derive(Clone, Debug, PartialEq)]
pub struct Expected {
    pub workspace: i64,
    pub owner: String,
}
fn runtime() -> Result<PathBuf> {
    std::env::var_os("XDG_RUNTIME_DIR")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .map(|p| p.join("hyprland"))
        .ok_or("XDG_RUNTIME_DIR must be absolute".into())
}
fn status(home: &Path) -> Result<Value> {
    let out = process::run(
        Command::new(home.join(".local/bin/session-desktop")).arg("status"),
        None,
        true,
        Some(Duration::from_secs(2)),
    )?;
    if !out.status.success() {
        return Err("confirmed desktop status unavailable".into());
    }
    let value: Value = serde_json::from_slice(&out.stdout).map_err(|_| "invalid desktop status")?;
    notify::confirmed_context(&value)?;
    Sessions::parse(&value)?;
    Ok(value)
}
impl Expected {
    pub fn capture(home: &Path) -> Result<Self> {
        let before = status(home)?;
        let owner = before["displayed_context"]
            .as_str()
            .ok_or("missing desktop owner")?
            .to_owned();
        let result = {
            let mut controller = Controller {
                native: Hyprctl,
                store: LockedStore::open(&runtime()?)?,
            };
            let state = controller.read_state()?;
            let monitors = controller.native.query("monitors")?;
            let rows = monitors
                .as_array()
                .filter(|r| r.len() == 1)
                .ok_or("new-workspace launch requires one monitor")?;
            let monitor = &rows[0];
            if monitor["specialWorkspace"]["name"]
                .as_str()
                .is_none_or(|s| !s.is_empty())
            {
                return Err("hide the scratchpad before opening a new workspace".into());
            }
            let workspace = monitor["activeWorkspace"]["id"]
                .as_i64()
                .filter(|id| *id > 0 && *id <= crate::state::MAX_ID)
                .ok_or("no ordinary workspace")?;
            if controller.active()? != workspace || state.owner(workspace) != owner {
                return Err("workspace/owner changed".into());
            }
            Self { workspace, owner }
        };
        if status(home)? != before {
            return Err("session changed during capture".into());
        }
        Ok(result)
    }
    pub fn check(&self, home: &Path) -> Result<()> {
        // Verify only the expected identity, not a new complete capture. Release
        // the metadata lock before status() takes its own lock/core snapshot.
        {
            let mut controller = Controller {
                native: Hyprctl,
                store: LockedStore::open(&runtime()?)?,
            };
            let state = controller.read_state()?;
            let monitors = controller.native.query("monitors")?;
            let rows = monitors
                .as_array()
                .filter(|rows| rows.len() == 1)
                .ok_or("expected one monitor; launch cancelled")?;
            if rows[0]["activeWorkspace"]["id"].as_i64() != Some(self.workspace)
                || rows[0]["specialWorkspace"]["name"].as_str() != Some("")
                || controller.active()? != self.workspace
                || state.owner(self.workspace) != self.owner
            {
                return Err("expected workspace/context changed; launch cancelled".into());
            }
        }
        let live = status(home)?;
        if live["displayed_context"].as_str() != Some(self.owner.as_str()) {
            return Err("expected session changed; launch cancelled".into());
        }
        Ok(())
    }
}
fn executable(path: &Path) -> Result<()> {
    let meta =
        std::fs::metadata(path).map_err(|_| format!("missing executable: {}", path.display()))?;
    if !meta.is_file() || meta.permissions().mode() & 0o111 == 0 {
        return Err("launch tool is not executable".into());
    }
    Ok(())
}
fn tool(name: &str) -> Result<PathBuf> {
    for root in std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default()) {
        if root.is_absolute() {
            let p = root.join(name);
            if executable(&p).is_ok() {
                return Ok(p);
            }
        }
    }
    Err(format!("missing launch tool: {name}"))
}
fn identity(path: &Path) -> Result<(u64, u64)> {
    pi::validate_directory(path)?;
    let m = std::fs::metadata(path).map_err(|_| "directory unavailable")?;
    Ok((m.dev(), m.ino()))
}
enum Plan {
    Launcher(PathBuf, Target),
    Vault(PathBuf, String),
    Pi(pi::Plan, notify::Context, (u64, u64)),
    Files(PathBuf, PathBuf, (u64, u64)),
    Terminal(PathBuf),
}
fn prepare(target: Target, home: &Path, expected: &Expected) -> Result<Plan> {
    match target {
        Target::Apps | Target::Browser | Target::Youtube => {
            let path = home.join(".local/bin/session-app-launcher");
            executable(&path)?;
            let output = process::run(
                Command::new(&path).arg("--version"),
                None,
                true,
                Some(Duration::from_secs(5)),
            )?;
            let capability = if target == Target::Youtube {
                "[expected-youtube-v1]"
            } else if target == Target::Browser {
                "[expected-browser-v1]"
            } else {
                "[expected-workspace-v1]"
            };
            if !output.status.success()
                || !String::from_utf8_lossy(&output.stdout).contains(capability)
            {
                return Err("install the matching guarded app launcher first".into());
            }
            Ok(Plan::Launcher(path, target))
        }
        Target::Pi => {
            executable(&home.join(".local/bin/launch-terminal-command"))?;
            tool("pi")?;
            let config = std::env::var_os("XDG_CONFIG_HOME")
                .filter(|s| !s.is_empty())
                .map(PathBuf::from)
                .unwrap_or(home.join(".config"));
            let plan = pi::plan(home, &config, false)?;
            let label = if expected.owner == "neutral" {
                "neutral".into()
            } else {
                format!("session:{}", expected.owner)
            };
            if plan.expected.as_deref() != Some(label.as_str()) {
                return Err("Pi context changed during planning".into());
            }
            let id = identity(&plan.directory)?;
            let origin = pi::capture(home, plan.expected.as_deref());
            Ok(Plan::Pi(plan, origin, id))
        }
        Target::Files => {
            let path = files::destination(home)?;
            let id = identity(&path)?;
            Ok(Plan::Files(path, tool("xdg-open")?, id))
        }
        Target::Terminal => Ok(Plan::Terminal(tool("kitty")?)),
        Target::Obsidian => {
            let path = home.join(".local/bin/session-obsidian");
            let version = process::run(
                Command::new(&path).arg("--version"),
                None,
                true,
                Some(Duration::from_secs(2)),
            )?;
            if !version.status.success()
                || !String::from_utf8_lossy(&version.stdout).contains("[expected-vault-v1]")
            {
                return Err("install guarded Obsidian helper first".into());
            }
            let reply = process::run(
                Command::new(&path).arg("--print-uri"),
                None,
                true,
                Some(Duration::from_secs(5)),
            )?;
            let uri = String::from_utf8(reply.stdout)
                .map_err(|_| "invalid vault URI")?
                .trim()
                .to_owned();
            if !reply.status.success() || !uri.starts_with("obsidian://open?vault=") {
                return Err("cannot prepare contextual vault".into());
            }
            Ok(Plan::Vault(path, uri))
        }
    }
}
pub fn run(target: Target) -> Result<()> {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute() && p.is_dir())
        .ok_or("HOME must be an existing absolute directory")?;
    let before = Expected::capture(&home)?;
    let plan = prepare(target, &home, &before)?;
    before.check(&home)?;
    let workspace = {
        let mut controller = Controller {
            native: Hyprctl,
            store: LockedStore::open(&runtime()?)?,
        };
        let mut state = controller.read_state()?;
        controller.create_for_launch(&mut state, before.workspace, &before.owner)?
    };
    // Never hold the workspace lock while querying the core or running an app/menu.
    let expected = Expected {
        workspace,
        owner: before.owner,
    };
    match plan {
        Plan::Launcher(path, target) => {
            use std::os::unix::process::CommandExt;
            expected.check(&home)?;
            let mut command = Command::new(path);
            command.env_remove("HL_INITIAL_WORKSPACE_TOKEN");
            // Existing plain B/D use a login shell to include ~/.local/bin.
            // Preserve that lookup for desktop Exec/TryExec without a shell here.
            let mut paths: Vec<_> =
                std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default()).collect();
            let local = home.join(".local/bin");
            if !paths.contains(&local) {
                paths.push(local);
            }
            command.env(
                "PATH",
                std::env::join_paths(paths).map_err(|e| e.to_string())?,
            );
            match target {
                Target::Browser => {
                    command.arg("--browser");
                }
                Target::Youtube => {
                    command.arg("--youtube");
                }
                _ => {}
            }
            Err(format!(
                "workspace created; launcher exec failed: {}; no retry",
                command
                    .args([
                        "--expected-workspace",
                        &workspace.to_string(),
                        &expected.owner
                    ])
                    .exec()
            ))
        }
        Plan::Vault(path, uri) => {
            use std::os::unix::process::CommandExt;
            expected.check(&home)?;
            Err(format!(
                "vault launch failed; no retry: {}",
                Command::new(path)
                    .env_remove("HL_INITIAL_WORKSPACE_TOKEN")
                    .args([
                        "--expected-workspace",
                        &workspace.to_string(),
                        &expected.owner,
                        "--expected-uri",
                        &uri
                    ])
                    .exec()
            ))
        }
        Plan::Pi(plan, origin, id) => {
            if identity(&plan.directory)? != id {
                return Err("Pi directory changed; no launch".into());
            }
            expected.check(&home)?;
            pi::launch_in_new_workspace(&home, &plan, &origin)
        }
        Plan::Files(path, tool, id) => {
            if identity(&path)? != id {
                return Err("files directory changed; no launch".into());
            }
            expected.check(&home)?;
            let mut command = Command::new(tool);
            command.env_remove("HL_INITIAL_WORKSPACE_TOKEN");
            let status = command.arg(path).status().map_err(|e| e.to_string())?;
            if status.success() {
                Ok(())
            } else {
                Err("file manager failed; no retry".into())
            }
        }
        Plan::Terminal(tool) => {
            expected.check(&home)?;
            let status = Command::new(tool)
                .env_remove("HL_INITIAL_WORKSPACE_TOKEN")
                .status()
                .map_err(|e| e.to_string())?;
            if status.success() {
                Ok(())
            } else {
                Err("terminal failed; no retry".into())
            }
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pinned_directory_rejects_replacement() {
        let temp = crate::tests::Temp::new();
        let path = temp.0.join("literal ; folder");
        std::fs::create_dir(&path).unwrap();
        let before = identity(&path).unwrap();
        std::fs::rename(&path, temp.0.join("old")).unwrap();
        std::fs::create_dir(&path).unwrap();
        assert_ne!(identity(&path).unwrap(), before);
    }
    #[test]
    fn preflight_requires_executable_regular_file() {
        let temp = crate::tests::Temp::new();
        assert!(executable(&temp.0).is_err());
        let path = temp.0.join("tool");
        std::fs::write(&path, b"").unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
        assert!(executable(&path).is_err());
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o700)).unwrap();
        assert!(executable(&path).is_ok());
    }
    #[test]
    fn closed_targets() {
        for s in [
            "browser", "pi", "files", "terminal", "apps", "youtube", "obsidian",
        ] {
            assert!(Target::parse(s).is_ok());
        }
        for s in ["", "sh", "apps; echo bad", "browser --flag"] {
            assert!(Target::parse(s).is_err());
        }
    }
}
