use agora_desktop_tools::{
    Result,
    notify::{self, Action, Context},
};
use std::path::PathBuf;
fn inherited() -> Result<Option<String>> {
    std::env::var("AGORA_NOTIFICATION_CONTEXT")
        .map(Some)
        .or_else(|e| match e {
            std::env::VarError::NotPresent => Ok(None),
            _ => Err("invalid inherited context encoding".into()),
        })
}
fn execute(action: Action) -> Result<()> {
    match action {
        Action::Capture => {
            let context = if let Some(value) = inherited()? {
                Context::parse(&value)?
            } else {
                let home = PathBuf::from(
                    std::env::var_os("HOME").ok_or("HOME is required for desktop capture")?,
                );
                notify::capture(&home, None)?
            };
            println!("{}", context.label());
        }
        Action::Send(send) => {
            let inherited = if send.global || send.context.is_some() {
                None
            } else {
                inherited()?
            };
            send.send(inherited.as_deref())?;
        }
        Action::Help => println!(
            "usage: agora-notify capture | send [--context VALUE|--global] [-u low|normal|critical] [-a NAME] [-t INTEGER] [-r UINT32] SUMMARY [BODY]"
        ),
        Action::Version => println!(
            "agora-notify {} (Rust; x-agora-context)",
            env!("CARGO_PKG_VERSION")
        ),
    }
    Ok(())
}
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let action = match notify::parse(&args) {
        Ok(action) => action,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    if let Err(e) = execute(action) {
        eprintln!("agora-notify: {e}");
        std::process::exit(1);
    }
}
