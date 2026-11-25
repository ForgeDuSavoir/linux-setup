//! Session Pi routing; explicit config, fresh captured origin, literal terminal argv.
use crate::{
    Result,
    core::{self, Sessions, Source},
    notify::Context,
    process,
};
use std::{
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

#[derive(Clone, Debug, PartialEq)]
pub struct Plan {
    pub directory: PathBuf,
    pub expected: Option<String>,
}
pub fn validate_directory(path: &Path) -> Result<()> {
    let lexical: PathBuf = path.components().collect();
    if !lexical.is_absolute() || lexical.is_symlink() || !lexical.is_dir() {
        return Err("working directory is unavailable".into());
    }
    Ok(())
}
pub fn agora_root(config_root: &Path) -> Result<PathBuf> {
    if !config_root.is_absolute() {
        return Err("XDG_CONFIG_HOME must be absolute".into());
    }
    let config = config_root.join("agora-workflow/config.toml");
    let content = std::fs::read_to_string(&config)
        .map_err(|e| format!("configure a valid agora_root in {}: {e}", config.display()))?;
    let value: toml::Value = toml::from_str(&content).map_err(|_| "invalid workflow TOML")?;
    let path = value
        .get("agora_root")
        .and_then(toml::Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or("agora_root must be an absolute directory path")?;
    let path: PathBuf = Path::new(path).components().collect();
    validate_directory(&path)?;
    Ok(path)
}
fn query(manager: &Path, args: &[&str]) -> Result<serde_json::Value> {
    core::query_json(manager, args, Duration::from_secs(35))
}
pub fn plan(home: &Path, config_root: &Path, explicit_agora: bool) -> Result<Plan> {
    if explicit_agora {
        return Ok(Plan {
            directory: agora_root(config_root)?,
            expected: None,
        });
    }
    let manager = home.join(".local/bin/session-manager");
    let sessions = Sessions::parse(&query(&manager, &["session", "list"])?)?;
    let Some(active) = sessions.active_session_id else {
        return Ok(Plan {
            directory: agora_root(config_root)?,
            expected: Some("neutral".into()),
        });
    };
    let session = sessions
        .sessions
        .iter()
        .find(|s| s.id == active)
        .ok_or("active session is missing")?;
    let directory = match &session.source {
        Source::Neutral {} => agora_root(config_root)?,
        Source::Project { project_name } => {
            let path = core::project_path(&query(&manager, &["project", "list"])?, project_name)?;
            let path: PathBuf = path.components().collect();
            validate_directory(&path)?;
            path
        }
    };
    Ok(Plan {
        directory,
        expected: Some(format!("session:{}", active.0)),
    })
}
pub fn accepted_context(output: &str, expected: Option<&str>) -> Context {
    let value = output.trim();
    match Context::parse(value) {
        Ok(context) if expected.is_none_or(|e| e == value) => context,
        _ => Context::Global,
    }
}
pub fn capture(home: &Path, expected: Option<&str>) -> Context {
    let result = process::run(
        Command::new(home.join(".local/bin/agora-notify"))
            .arg("capture")
            .env_remove("AGORA_NOTIFICATION_CONTEXT"),
        None,
        true,
        Some(Duration::from_secs(2)),
    );
    match result {
        Ok(output) if output.status.success() => String::from_utf8(output.stdout)
            .map(|value| accepted_context(&value, expected))
            .unwrap_or(Context::Global),
        _ => Context::Global,
    }
}
pub fn launch(home: &Path, plan: &Plan, context: &Context) -> Result<()> {
    launch_scoped(home, plan, context, false)
}
pub fn launch_in_new_workspace(home: &Path, plan: &Plan, context: &Context) -> Result<()> {
    launch_scoped(home, plan, context, true)
}
fn launch_scoped(home: &Path, plan: &Plan, context: &Context, new_workspace: bool) -> Result<()> {
    let context = context.label();
    let mut command = Command::new(home.join(".local/bin/launch-terminal-command"));
    if new_workspace {
        command.env_remove("HL_INITIAL_WORKSPACE_TOKEN");
    }
    let status = command
        .arg(&plan.directory)
        .args([
            "env",
            &format!("AGORA_NOTIFICATION_CONTEXT={context}"),
            "pi",
            "--continue",
        ])
        .env("AGORA_NOTIFICATION_CONTEXT", context)
        .status()
        .map_err(|e| format!("terminal launch failed: {e}"))?;
    if !status.success() {
        return Err("terminal launch failed; no retry".into());
    }
    Ok(())
}
