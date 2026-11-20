use agora_desktop_tools::{
    Result,
    native::Hyprctl,
    storage::LockedStore,
    workspace::{Action, Controller},
};
use std::{os::unix::process::CommandExt, path::PathBuf, process::Command, time::Duration};
fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args == ["--version"] {
        println!(
            "workspace-controller {} (desktop metadata 3)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let action = Action::parse(&args)?;
    let launcher = if action == Action::CreateEmptyAndLaunch {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .filter(|p| p.is_absolute())
            .ok_or("HOME must be absolute")?;
        let path = home.join(".local/bin/session-app-launcher");
        let version = agora_desktop_tools::process::run(
            Command::new(&path).arg("--version"),
            None,
            true,
            Some(Duration::from_secs(5)),
        )?;
        if !version.status.success()
            || !String::from_utf8_lossy(&version.stdout).contains("[expected-workspace-v1]")
        {
            return Err(
                "install the matching expected-workspace launcher before using this action".into(),
            );
        }
        Some(path)
    } else {
        None
    };
    let runtime =
        PathBuf::from(std::env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into()))
            .join("hyprland");
    let store = LockedStore::open(&runtime)?;
    let mut controller = Controller {
        native: Hyprctl,
        store,
    };
    let result = controller.run(action)?;
    // Rofi and launcher context queries must never inherit/hold the workspace lock.
    drop(controller);
    if let Some(value) = result {
        if let Some(path) = launcher {
            let ws = value["workspace_id"]
                .as_i64()
                .ok_or("invalid created workspace")?;
            let owner = value["owner"].as_str().ok_or("invalid created owner")?;
            let error = Command::new(path)
                .args(["--expected-workspace", &ws.to_string(), owner])
                .exec();
            return Err(format!(
                "workspace created but launcher could not start: {error}; no retry"
            ));
        }
        println!("{value}");
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("workspace-controller: {error}");
        std::process::exit(1);
    }
}
