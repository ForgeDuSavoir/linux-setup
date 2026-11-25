use agora_desktop_tools::{
    core::CliCore,
    desktop::Desktop,
    native::Hyprctl,
    process,
    startup::{self, Failure},
    storage::LockedStore,
    workspace::Controller,
};
use std::{os::unix::process::CommandExt, path::PathBuf, process::Command, time::Duration};
fn initialize() -> std::result::Result<bool, Failure> {
    let instance = std::env::var("HYPRLAND_INSTANCE_SIGNATURE")
        .map_err(|_| Failure::Error("missing/invalid Hyprland instance signature".into()))?;
    startup::validate_signature(&instance)?;
    let home = PathBuf::from(
        std::env::var_os("HOME").ok_or_else(|| Failure::Error("HOME is required".into()))?,
    );
    let binary = std::env::var_os("SESSION_MANAGER_BIN")
        .map(PathBuf::from)
        .unwrap_or(home.join(".local/bin/session-manager"));
    let runtime =
        PathBuf::from(std::env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into()))
            .join("hyprland");
    let mut desktop = Desktop {
        workspace: Controller {
            native: Hyprctl,
            store: LockedStore::open(&runtime)?,
        },
        core: CliCore { binary },
    };
    startup::initialize(&mut desktop, &instance)
}
fn claim_menu() -> Result<bool, String> {
    let instance = std::env::var("HYPRLAND_INSTANCE_SIGNATURE")
        .map_err(|_| "Hyprland instance signature required")?;
    startup::validate_signature(&instance)?;
    let runtime = std::env::var_os("XDG_RUNTIME_DIR")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .ok_or("absolute XDG_RUNTIME_DIR required")?;
    let mut store = LockedStore::open(&runtime.join("hyprland"))?;
    startup::claim_menu(&mut store, &instance)
}
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args == ["--version"] {
        println!(
            "session-startup {} (marker 1; new-compositor only) [startup-menu-v1]",
            env!("CARGO_PKG_VERSION")
        );
        return;
    }
    if args == ["--claim-menu"] {
        match claim_menu() {
            Ok(show) => println!("{}", serde_json::json!({"show":show})),
            Err(error) => {
                eprintln!("session-startup menu claim: {error}");
                std::process::exit(1);
            }
        }
        return; // Never initialization or bar execution from a UI menu claim.
    }
    if !args.is_empty() {
        eprintln!(
            "usage: session-startup [--claim-menu] (normal invocation: Hyprland startup only)"
        );
        std::process::exit(1);
    }
    match initialize() {
        Ok(false) => return,
        Err(Failure::AlreadyAttempted) => {
            eprintln!(
                "session-startup: startup already attempted; inspect state instead of replaying requests"
            );
            std::process::exit(1);
        }
        Err(Failure::Error(error)) => {
            let message = format!(
                "session-startup failed: {error}; use the menu to recover; no automatic retry"
            );
            eprintln!("{message}");
            let _ = process::run(
                Command::new("logger").args(["-t", "session-startup", "--", &message]),
                None,
                true,
                Some(Duration::from_secs(2)),
            );
        }
        Ok(true) => {}
    }
    // The owning desktop/lock has dropped BEFORE exec. Never launch two bars on replay.
    let error = Command::new("quickshell").exec();
    eprintln!("session-startup: cannot exec recovery/session bar: {error}");
    std::process::exit(1);
}
