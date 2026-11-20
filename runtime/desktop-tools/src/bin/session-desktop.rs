use agora_desktop_tools::{
    Result,
    core::CliCore,
    desktop::{Action, Desktop},
    native::Hyprctl,
    storage::LockedStore,
    workspace::Controller,
};
use std::path::PathBuf;
fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args == ["--version"] {
        println!(
            "session-desktop {} (core protocol 3; desktop metadata 2/3)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let action = Action::parse(&args)?;
    let home = PathBuf::from(std::env::var_os("HOME").ok_or("HOME is required")?);
    let binary = std::env::var_os("SESSION_MANAGER_BIN")
        .map(PathBuf::from)
        .unwrap_or(home.join(".local/bin/session-manager"));
    let runtime =
        PathBuf::from(std::env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into()))
            .join("hyprland");
    let store = LockedStore::open(&runtime)?;
    let mut desktop = Desktop {
        workspace: Controller {
            native: Hyprctl,
            store,
        },
        core: CliCore { binary },
    };
    println!("{}", desktop.invoke(action)?);
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("session-desktop: {e}");
        std::process::exit(1);
    }
}
