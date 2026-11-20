use agora_desktop_tools::{
    Result,
    native::Hyprctl,
    storage::LockedStore,
    workspace::{Action, Controller},
};
use std::path::PathBuf;
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
    let runtime =
        PathBuf::from(std::env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into()))
            .join("hyprland");
    let store = LockedStore::open(&runtime)?;
    let mut controller = Controller {
        native: Hyprctl,
        store,
    };
    if let Some(value) = controller.run(action)? {
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
